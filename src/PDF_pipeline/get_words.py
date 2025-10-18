from typing import Any, Dict, List, Tuple
import os

try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover - optional dependency
    fitz = None  # type: ignore

# Keep pdfplumber as fallback
try:
    import pdfplumber
except Exception:  # pragma: no cover
    pdfplumber = None  # type: ignore


PageT = Dict[str, Any]
WordT = Dict[str, Any]


def _is_bold_font(font_name: str) -> bool:
    f = (font_name or "").lower()
    return any(k in f for k in ["bold", "semibold", "black", "heavy", "medium", "demi"]) or f.endswith("bd")


def _span_is_bold(span: Dict[str, Any]) -> bool:
    flags = int(span.get("flags", 0) or 0)
    # PyMuPDF: bold bit is 2
    return bool(flags & 2) or _is_bold_font(span.get("font", ""))


def _is_probably_pdf(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            sig = f.read(5)
        return sig.startswith(b"%PDF-")
    except Exception:
        return False


def _get_words_from_pdf_pymupdf(pdf_path: str) -> List[PageT]:
    doc = fitz.open(pdf_path)
    try:
        if getattr(doc, "needs_pass", False) and doc.needs_pass:  # type: ignore[attr-defined]
            # Try empty password
            try:
                doc.authenticate("")  # type: ignore[attr-defined]
            except Exception:
                pass
    except Exception:
        pass

    pages: List[PageT] = []

    for page_index in range(len(doc)):
        page = doc[page_index]
        pw = float(page.rect.width)
        ph = float(page.rect.height)

        # Build spans index by (block_no, line_no)
        spans_by_line: Dict[Tuple[int, int], List[dict]] = {}
        try:
            text_dict = page.get_text("dict")
        except Exception:
            text_dict = {"blocks": []}
        for b_idx, block in enumerate(text_dict.get("blocks", [])):
            if block.get("type", 0) != 0:
                continue  # text blocks only
            for l_idx, line in enumerate(block.get("lines", [])):
                key = (b_idx, l_idx)
                spans = []
                for span in line.get("spans", []):
                    spans.append({
                        "bbox": span.get("bbox", (0, 0, 0, 0)),
                        "font": span.get("font", ""),
                        "size": float(span.get("size", 0.0) or 0.0),
                        "color": int(span.get("color", 0) or 0),
                        "text": span.get("text", ""),
                        "flags": int(span.get("flags", 0) or 0),
                    })
                spans_by_line[key] = spans

        # Get words with their block/line indices
        words_out: List[WordT] = []
        try:
            words = page.get_text("words")  # [x0, y0, x1, y1, word, block_no, line_no, word_no]
        except Exception:
            words = []

        for item in words:
            if len(item) < 8:
                continue
            x0, y0, x1, y1, txt, bno, lno, _wno = item[:8]
            font = ""
            size = 0.0
            color = 0
            is_bold = False

            spans = spans_by_line.get((int(bno), int(lno)), [])
            # Find the span whose bbox best overlaps horizontally
            best = None
            best_overlap = -1.0
            for sp in spans:
                sx0, sy0, sx1, sy1 = sp["bbox"]
                v_ok = (y0 >= sy0 - 1.5) and (y1 <= sy1 + 1.5)
                if not v_ok:
                    continue
                overlap = max(0.0, min(float(x1), float(sx1)) - max(float(x0), float(sx0)))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best = sp
            if best is not None:
                font = best.get("font", "")
                size = float(best.get("size", 0.0) or 0.0)
                color = int(best.get("color", 0) or 0)
                is_bold = _span_is_bold(best)

            words_out.append({
                "text": str(txt or ""),
                "x0": float(x0),
                "x1": float(x1),
                "top": float(y0),
                "bottom": float(y1),
                "page": int(page_index),
                "page_width": float(pw),
                "page_height": float(ph),
                "font": font,
                "font_size": float(size),
                "font_color": int(color),
                "is_bold": bool(is_bold),
            })

        pages.append({
            "page_no": int(page_index),
            "width": float(pw),
            "height": float(ph),
            "words": words_out,
        })

    return pages


def _get_words_from_pdf_pdfplumber(pdf_path: str, x_tolerance=2, y_tolerance=2.5, keep_blank_chars=False) -> List[PageT]:
    pages: List[PageT] = []
    if pdfplumber is None:
        return pages
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Try unlock with empty password if encrypted
            try:
                if getattr(pdf, "is_encrypted", False) and pdf.is_encrypted:
                    pdf.decrypt("")  # type: ignore[attr-defined]
            except Exception:
                pass
            for page_num, page in enumerate(pdf.pages):
                words = page.extract_words(
                    x_tolerance=x_tolerance,
                    y_tolerance=y_tolerance,
                    keep_blank_chars=keep_blank_chars
                )
                for word in words:
                    word['page'] = page_num
                    word['page_width'] = float(page.width)
                    word['page_height'] = float(page.height)
                pages.append({
                    "page_no": page_num,
                    "width": float(page.width),
                    "height": float(page.height),
                    "words": words
                })
    except Exception as e:  # pragma: no cover
        print(f"Error extracting from {pdf_path}: {e}")
        return []
    return pages


def get_words_from_pdf(pdf_path, x_tolerance=2, y_tolerance=2.5, keep_blank_chars=False):
    """Extract words from all pages with coordinates. Prefer PyMuPDF; fallback to pdfplumber.
    Falls back if PyMuPDF raises OR returns zero pages.
    """
    # Basic checks and helpful debug
    if not os.path.isabs(pdf_path):
        abs_path = os.path.abspath(pdf_path)
    else:
        abs_path = pdf_path
    if not os.path.exists(abs_path):
        print(f"File not found: {abs_path}")
        return []
    if not _is_probably_pdf(abs_path):
        print(f"Not a PDF file (missing %PDF signature): {abs_path}")
        # still try, but warn
    if fitz is not None:
        try:
            pages = _get_words_from_pdf_pymupdf(abs_path)
            if pages:
                return pages
            print("PyMuPDF returned 0 pages, trying pdfplumber...")
        except Exception as e:  # pragma: no cover
            print(f"PyMuPDF extraction failed, falling back to pdfplumber: {e}")
    return _get_words_from_pdf_pdfplumber(abs_path, x_tolerance, y_tolerance, keep_blank_chars)


def get_all_words_flat(pdf_path, x_tolerance=2, y_tolerance=2.5, keep_blank_chars=False):
    pages = get_words_from_pdf(pdf_path, x_tolerance, y_tolerance, keep_blank_chars)
    all_words: List[WordT] = []
    for page in pages:
        all_words.extend(page['words'])
    return all_words


def get_words_from_single_page(pdf_path, page_number=0):
    pages = get_words_from_pdf(pdf_path)
    for page in pages:
        if page.get('page_no') == page_number:
            return page['words']
    raise ValueError(f"Page {page_number} does not exist. PDF has {len(pages)} pages.")


def main():
    pdf_path = "freshteams_resume/ReactJs/UI_Developer.pdf"
    print("Extracting words from all pages...")
    pages = get_words_from_pdf(pdf_path)
    print(f"Total pages extracted: {len(pages)}")
    for page in pages:
        for word in page['words'][:3]:
            print(f"Page {page['page_no'] + 1}: '{word['text']}' at ({word['x0']:.1f}, {word['top']:.1f})")

# if __name__ == "__main__":
#     main()