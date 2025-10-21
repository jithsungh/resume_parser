from typing import Any, Dict, List
import statistics
import re

try:
    from docx import Document  # python-docx
except Exception:  # pragma: no cover
    Document = None  # type: ignore


def normalize_text(text: str) -> str:
    if not text:
        return ""
    replacements = {
        "•": "• ",
        "–": "-",
        "—": "-",
        "\u2022": "• ",
        "\u2023": "• ",
        "\u25E6": "• ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"\s+", " ", text)
    ILLEGAL_CHARACTERS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
    text = ILLEGAL_CHARACTERS_RE.sub("", text)
    return text.strip()


def read_docx_paragraphs(docx_path: str) -> List[Dict[str, Any]]:
    """
    Read a DOCX file and convert paragraphs (and list items) into line-like records.
    Returns a list of lines with minimal spatial info emulated for compatibility.
    """
    if Document is None:
        raise RuntimeError("python-docx is not installed. Please install 'python-docx'.")

    doc = Document(docx_path)

    lines: List[Dict[str, Any]] = []
    y_cursor = 0.0
    for pi, para in enumerate(doc.paragraphs):
        raw = para.text or ""
        text = normalize_text(raw)
        if not text:
            y_cursor += 8.0
            continue

        # Identify bullet/numbering and bold runs
        is_bullet = False
        bold_tokens = 0
        total_tokens = 0
        span_sizes: List[float] = []
        fonts: List[str] = []
        colors: List[int] = []

        try:
            pstyle = para.style
            if pstyle and pstyle.name and any(k in pstyle.name.lower() for k in ("list", "bullet", "number")):
                is_bullet = True
        except Exception:
            pass

        for run in para.runs:
            txt = (run.text or "").strip()
            if not txt:
                continue
            total_tokens += len(txt.split())
            try:
                if bool(getattr(run.font, "bold", False)):
                    bold_tokens += len(txt.split())
            except Exception:
                pass
            try:
                if getattr(run.font, "size", None) is not None:
                    span_sizes.append(float(run.font.size.pt))  # type: ignore[attr-defined]
            except Exception:
                pass
            try:
                if getattr(run.font, "name", None):
                    fonts.append(str(run.font.name))
            except Exception:
                pass

        bold_ratio = (bold_tokens / total_tokens) if total_tokens else 0.0
        avg_span_font_size = statistics.mean(span_sizes) if span_sizes else 0.0
        dominant_font = max(set(fonts), key=fonts.count) if fonts else None

        # Emulate a bounding box line height from font size
        height = max(10.0, avg_span_font_size or 11.0)
        top = y_cursor
        bottom = y_cursor + height
        y_cursor = bottom + 4.0  # gap to next line

        line = {
            "line_index": len(lines),
            "text": ("• " + text) if is_bullet and not text.startswith("•") else text,
            "boundaries": {
                "x0": 0.0,
                "x1": 1000.0,
                "top": float(top),
                "bottom": float(bottom),
                "width": 1000.0,
                "height": float(height),
            },
            "properties": {
                "char_count": len(text),
                "word_count": len(text.split()),
                "char_count_no_spaces": len(text.replace(" ", "")),
            },
            "metrics": {
                "height": float(height),
                "space_above": 4.0,
                "space_below": 4.0,
                "char_count": len(text),
                "word_count": len(text.split()),
                "avg_font_size": float(height),
                "avg_span_font_size": float(avg_span_font_size),
                "bold_ratio": float(bold_ratio),
                "dominant_font": dominant_font,
                "dominant_color": None,
                "line_width": 1000.0,
            },
        }
        lines.append(line)

    return lines


def get_single_column_from_docx(docx_path: str) -> List[Dict[str, Any]]:
    """
    For DOCX, treat the document as a single column per page sequence.
    Returns a columns-with-lines list compatible with PDF pipeline downstream.
    
    Raises:
        RuntimeError: If python-docx is not installed
        FileNotFoundError: If file doesn't exist
        Exception: For other parsing errors
    """
    from pathlib import Path
    
    # Validate file exists
    if not Path(docx_path).exists():
        raise FileNotFoundError(f"DOCX file not found: {docx_path}")
    
    # Validate file is readable
    try:
        with open(docx_path, 'rb') as f:
            # Read first few bytes to verify it's a valid file
            header = f.read(4)
            if not header:
                raise ValueError(f"Empty file: {docx_path}")
    except PermissionError:
        raise PermissionError(f"Permission denied reading file: {docx_path}")
    except Exception as e:
        raise RuntimeError(f"Cannot read file {docx_path}: {e}") from e
    
    try:
        lines = read_docx_paragraphs(docx_path)
    except RuntimeError:
        # Re-raise if python-docx not installed
        raise
    except Exception as e:
        # Wrap with context
        raise RuntimeError(f"Failed to parse DOCX paragraphs from {docx_path}: {e}") from e
    
    if not lines:
        # Return empty structure rather than failing - some docs might be legitimately empty
        lines = []
    
    col = {
        "page": 0,
        "column_index": 0,
        "x_start": 0.0,
        "x_end": 1000.0,
        "width": 1000.0,
        "words": [],
        "lines": lines,
    }
    return [col]
