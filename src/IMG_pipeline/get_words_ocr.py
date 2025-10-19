import os
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF for rasterization
import easyocr
from PIL import Image
import numpy as np

PageT = Dict[str, Any]
WordT = Dict[str, Any]

# Global EasyOCR reader instance (initialized lazily)
_EASYOCR_READER = None


def _get_easyocr_reader(languages: List[str] = ['en'], gpu: bool = False):
    """Get or initialize the EasyOCR reader (singleton pattern for efficiency)."""
    global _EASYOCR_READER
    if _EASYOCR_READER is None:
        _EASYOCR_READER = easyocr.Reader(languages, gpu=gpu)
    return _EASYOCR_READER


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
    languages: List[str] = ['en'],
    gpu: bool = False,
    paragraph: bool = False,
) -> List[WordT]:
    """Run EasyOCR on an image and return word-level boxes in pipeline format."""
    reader = _get_easyocr_reader(languages=languages, gpu=gpu)
    
    # Convert PIL Image to numpy array
    img_array = np.array(img)
    
    # Run EasyOCR - returns list of (bbox, text, confidence)
    # bbox is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    results = reader.readtext(img_array, paragraph=paragraph)
    
    words: List[WordT] = []
    for detection in results:
        bbox, text, conf = detection
        text = text.strip()
        if not text:
            continue
        
        # Extract bounding box coordinates
        # bbox is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        x_coords = [point[0] for point in bbox]
        y_coords = [point[1] for point in bbox]
        
        x0 = min(x_coords)
        x1 = max(x_coords)
        y0 = min(y_coords)
        y1 = max(y_coords)
        
        height = y1 - y0
        
        words.append({
            "text": text,
            "x0": float(x0),
            "x1": float(x1),
            "top": float(y0),
            "bottom": float(y1),
            "page": int(page_no),
            "page_width": float(page_width),
            "page_height": float(page_height),
            # No font metadata from OCR; set placeholders
            "font": "",
            "font_size": float(height),
            "font_color": 0,
            "is_bold": False,
            "_conf": float(conf),
        })
    return words


def get_words_from_pdf_ocr(
    pdf_path: str,
    dpi: int = 300,
    *,
    languages: List[str] = ['en'],
    gpu: bool = False,
    paragraph: bool = False,
) -> List[PageT]:
    """
    Rasterize each page to an image, OCR to words using EasyOCR, and return pages in the same structure
    expected by the existing split_columns/get_lines/segment_sections pipeline.
    
    Args:
        pdf_path: Path to the PDF file
        dpi: Resolution for rendering PDF pages (default: 300)
        languages: List of language codes for EasyOCR (default: ['en'])
        gpu: Whether to use GPU acceleration (default: False)
        paragraph: If True, returns paragraph-level text; if False, returns word-level (default: False)
    """
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

        words = _ocr_words_from_image(
            img, page_index, pw, ph, 
            languages=languages, 
            gpu=gpu, 
            paragraph=paragraph
        )
        pages.append({
            "page_no": int(page_index),
            "width": pw,
            "height": ph,
            "words": words,
        })
    return pages
