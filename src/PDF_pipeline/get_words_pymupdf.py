import fitz  # PyMuPDF
from typing import List, Dict, Any


def _is_bold_font(font_name: str) -> bool:
    f = (font_name or "").lower()
    return any(k in f for k in ["bold", "semibold", "black", "heavy", "medium", "demi"]) or f.endswith("bd")


def get_words_from_pdf(pdf_path: str, *_, **__) -> List[Dict[str, Any]]:
    """
    Extract words from all pages using PyMuPDF and enrich with span font attributes.
    Returns a list of pages: { page_no, width, height, words: [ {text,x0,x1,top,bottom,page,page_width,page_height,font,font_size,font_color,is_bold} ] }
    The signature accepts extra args for compatibility with the prior extractor.
    """
    doc = fitz.open(pdf_path)
    pages: List[Dict[str, Any]] = []

    for page_index in range(len(doc)):
        page = doc[page_index]
        pw = float(page.rect.width)
        ph = float(page.rect.height)

        # Build spans index by (block_no, line_no)
        spans_by_line = {}
        text_dict = page.get_text("dict")
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
                    })
                spans_by_line[key] = spans

        # Get words with their block/line indices
        words_out = []
        try:
            words = page.get_text("words")  # [x0, y0, x1, y1, word, block_no, line_no, word_no]
        except Exception:
            words = []

        for item in words:
            if len(item) < 8:
                # PyMuPDF occasionally returns shorter tuples; skip
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
                # Quick vertical inclusion check with tolerance
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
                is_bold = _is_bold_font(font)

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
