import os
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF for rasterization
import pytesseract
from PIL import Image
import numpy as np

PageT = Dict[str, Any]
WordT = Dict[str, Any]


# Allow overriding tesseract path via env var on Windows
_TESS_CMD = os.getenv("TESSERACT_CMD")
if _TESS_CMD:
    pytesseract.pytesseract.tesseract_cmd = _TESS_CMD


def _open_pdf(pdf_path: str):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(pdf_path)
    return fitz.open(pdf_path)


def _pil_from_pix(pix: fitz.Pixmap) -> Image.Image:
    """Robustly convert a PyMuPDF Pixmap to a PIL.Image.
    - Convert non-RGB colorspaces (and alpha) to RGB first
    - Support grayscale directly
    """
    try:
        # If grayscale without alpha
        if pix.colorspace and pix.colorspace.n == 1 and not pix.alpha:
            return Image.frombytes("L", (pix.width, pix.height), pix.samples).convert("RGB")

        # Otherwise force RGB (drops alpha / converts CMYK)
        if not pix.colorspace or pix.colorspace.n != 3 or pix.alpha:
            pix = fitz.Pixmap(fitz.csRGB, pix)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    except Exception:
        # Fallback via numpy if needed
        n = 4 if pix.alpha else (pix.colorspace.n if pix.colorspace else 3)
        arr = np.frombuffer(pix.samples, dtype=np.uint8)
        if arr.size == pix.width * pix.height * n:
            if n == 1:
                img = Image.fromarray(arr.reshape(pix.height, pix.width), mode="L").convert("RGB")
            else:
                img = Image.fromarray(arr.reshape(pix.height, pix.width, n)[..., :3], mode="RGB")
            return img
        # Last resort: convert to RGB and try again
        pix = fitz.Pixmap(fitz.csRGB, pix)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def _ocr_words_from_image(
    img: Image.Image,
    page_no: int,
    page_width: float,
    page_height: float,
    *,
    lang: str = "eng",
    config: str = "--oem 3 --psm 6",
) -> List[WordT]:
    """Run Tesseract OCR on an image and return word-level boxes in pipeline format."""
    data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT, config=config)
    words: List[WordT] = []
    n = len(data.get("text", []))
    for i in range(n):
        txt = (data["text"][i] or "").strip()
        conf = data.get("conf", [""])[i]
        try:
            conf_f = float(conf)
        except Exception:
            conf_f = -1.0
        if not txt:
            continue
        x = int(data.get("left", [0])[i])
        y = int(data.get("top", [0])[i])
        w = int(data.get("width", [0])[i])
        h = int(data.get("height", [0])[i])
        words.append({
            "text": txt,
            "x0": float(x),
            "x1": float(x + w),
            "top": float(y),
            "bottom": float(y + h),
            "page": int(page_no),
            "page_width": float(page_width),
            "page_height": float(page_height),
            # No font metadata from OCR; set placeholders
            "font": "",
            "font_size": float(h),
            "font_color": 0,
            "is_bold": False,
            "_conf": conf_f,
        })
    return words


def get_words_from_pdf_ocr(
    pdf_path: str,
    dpi: int = 300,
    *,
    lang: str = "eng",
    config: str = "--oem 3 --psm 6",
    tesseract_cmd: Optional[str] = None,
) -> List[PageT]:
    """
    Rasterize each page to an image, OCR to words, and return pages in the same structure
    expected by the existing split_columns/get_lines/segment_sections pipeline.
    """
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    doc = _open_pdf(pdf_path)
    pages: List[PageT] = []
    for page_index in range(len(doc)):
        page = doc[page_index]
        # Scale: 72 dpi base in PDF. To get target DPI, use zoom = dpi/72
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        pw = float(pix.width)
        ph = float(pix.height)
        img = _pil_from_pix(pix)

        words = _ocr_words_from_image(img, page_index, pw, ph, lang=lang, config=config)
        pages.append({
            "page_no": int(page_index),
            "width": pw,
            "height": ph,
            "words": words,
        })
    return pages
