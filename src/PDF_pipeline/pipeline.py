import re
import json
from typing import Dict, Any, Tuple, List, Optional

from src.PDF_pipeline.get_words import get_words_from_pdf
from src.PDF_pipeline.split_columns import split_columns
from src.PDF_pipeline.get_lines import get_column_wise_lines
from src.PDF_pipeline.segment_sections import (
    segment_sections_from_columns,
    simple_json,
    pretty_print_segmented_sections,
)

# ------------ Contact info extraction (regex-based) ------------

EMAIL_RE = re.compile(r'[\w\.-]+@[\w\.-]+\.\w{2,}', re.IGNORECASE)
# Broad international phone pattern; avoids too-short matches
PHONE_RE = re.compile(
    r'(?:\+|00)?\d{1,3}[\s\-\.]?(?:\(?\d{2,5}\)?[\s\-\.]?)?\d{3,5}[\s\-\.]?\d{3,5}',
    re.IGNORECASE,
)
LINKEDIN_RE = re.compile(r'(?:https?://)?(?:www\.)?linkedin\.com/[^\s,;]+', re.IGNORECASE)
GITHUB_RE = re.compile(r'(?:https?://)?(?:www\.)?github\.com/[^\s,;]+', re.IGNORECASE)

# Location: "City, State" or "City, Country" or with PIN/ZIP at end
LOCATION_CANDIDATE_RE = re.compile(
    r'\b([A-Z][A-Za-z .\-]+,\s*[A-Z][A-Za-z .\-]+(?:,\s*[A-Z][A-Za-z .\-]+)?)\b(?:\s*\d{5}(?:-\d{4})?|\s*\d{6})?',
    re.IGNORECASE,
)

# Name heuristic (regex-and-heuristic): 1-4 Title-Case tokens, no digits, no email/url
NAME_LINE_RE = re.compile(r"^[A-Z][a-zA-Z'\-]+(?: [A-Z][a-zA-Z'\-]+){0,3}$")


def _collect_all_lines(columns_with_lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    lines: List[Dict[str, Any]] = []
    for col in columns_with_lines or []:
        for ln in col.get("lines", []) or []:
            page = ln.get("page", col.get("page", 0))
            top = (ln.get("boundaries", {}) or {}).get("top", 0)
            lines.append({
                "page": page,
                "column_index": col.get("column_index", 0),
                "text": ln.get("text", "") or "",
                "boundaries": dict(ln.get("boundaries", {})),
                "properties": dict(ln.get("properties", {})),
                "metrics": dict(ln.get("metrics", {})),
                "line_index": ln.get("line_index", 0),
                "_top": top,
            })
    # Reading order: first by page then by top
    lines.sort(key=lambda l: (l["page"], l.get("_top", 0)))
    return lines


def _extract_first_match(regex: re.Pattern, text: str) -> Optional[str]:
    m = regex.search(text or "")
    return m.group(0) if m else None


def _normalize_phone(ph: str) -> str:
    if not ph:
        return ph
    s = ph.strip()
    # Collapse multiple spaces/dots/hyphens
    s = re.sub(r'[^\d\+]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def extract_contact_info_from_lines(columns_with_lines: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Regex-based extraction of contact fields from lines.
    Priority: early lines on first page, then fallback to whole text.
    """
    info: Dict[str, Any] = {}
    all_lines = _collect_all_lines(columns_with_lines)
    if not all_lines:
        return info

    # Focus on top of first page
    first_page = min(l["page"] for l in all_lines)
    first_page_lines = [l for l in all_lines if l["page"] == first_page]
    first_page_lines.sort(key=lambda l: l.get("_top", 0))
    head_window = first_page_lines[:40]  # top 40 lines

    # Scan head window for contact fields
    for ln in head_window:
        txt = ln.get("text", "") or ""
        if "email" not in info:
            em = _extract_first_match(EMAIL_RE, txt)
            if em:
                info["email"] = em
        if "linkedin" not in info:
            li = _extract_first_match(LINKEDIN_RE, txt)
            if li:
                info["linkedin"] = li
        if "github" not in info:
            gh = _extract_first_match(GITHUB_RE, txt)
            if gh:
                info["github"] = gh
        if "phone" not in info:
            ph = _extract_first_match(PHONE_RE, txt)
            # Avoid matching a short number or year-like values
            if ph and len(re.sub(r'\D', '', ph)) >= 8:
                info["phone"] = _normalize_phone(ph)
        if "location" not in info:
            loc = _extract_first_match(LOCATION_CANDIDATE_RE, txt)
            if loc and not any(k in txt.lower() for k in ("summary", "experience", "education", "skills", "projects")):
                info["location"] = loc.strip()

    # Name heuristic from very top lines (exclude lines containing obvious contact artifacts)
    if "name" not in info:
        for ln in first_page_lines[:15]:
            t = (ln.get("text") or "").strip()
            if not t or any(x in t.lower() for x in ("@", "linkedin.com", "github.com", "www.", "http")):
                continue
            if any(ch.isdigit() for ch in t):
                continue
            if NAME_LINE_RE.match(t) and 1 <= len(t.split()) <= 4:
                info["name"] = t
                break

    # Fallback: scan entire text for any missing fields
    all_text = " ".join(l.get("text", "") or "" for l in all_lines)
    if "email" not in info:
        em = _extract_first_match(EMAIL_RE, all_text)
        if em:
            info["email"] = em
    if "linkedin" not in info:
        li = _extract_first_match(LINKEDIN_RE, all_text)
        if li:
            info["linkedin"] = li
    if "github" not in info:
        gh = _extract_first_match(GITHUB_RE, all_text)
        if gh:
            info["github"] = gh
    if "phone" not in info:
        ph = _extract_first_match(PHONE_RE, all_text)
        if ph and len(re.sub(r'\D', '', ph)) >= 8:
            info["phone"] = _normalize_phone(ph)
    if "location" not in info:
        loc = _extract_first_match(LOCATION_CANDIDATE_RE, all_text)
        if loc:
            info["location"] = loc.strip()

    return info


# -------------------- Pipeline --------------------

def run_pipeline(
    pdf_path: str,
    *,
    min_words_per_column: int = 10,
    dynamic_min_words: bool = True,
    y_tolerance: float = 1.0,
    verbose: bool = True,
) -> Tuple[Dict[str, Any], str]:
    """
    Run the resume parsing pipeline:
      PDF -> words -> columns -> column-wise lines -> section segmentation -> contact info -> simple_json.
    Returns (full_result_json, simplified_json_str). Prints simplified JSON fully.
    """
    if verbose:
        print(f"PDF: {pdf_path}")

    # 1) Words
    pages = get_words_from_pdf(pdf_path)
    if not pages:
        print("No pages extracted.")
        empty = {"meta": {"pages": 0, "columns": 0, "sections": 0, "lines_total": 0}, "sections": [], "contact": {}}
        sim = simple_json(empty)
        print(sim)
        return empty, sim

    if verbose:
        total_words = sum(len(p.get("words", [])) for p in pages)
        print(f"Pages: {len(pages)} | Total words: {total_words}")

    # 2) Columns
    columns = split_columns(
        pages,
        min_words_per_column=min_words_per_column,
        dynamic_min_words=dynamic_min_words,
    )
    if verbose:
        print(f"Columns: {len(columns)}")

    # 3) Lines with tight vertical overlap and metrics
    columns_with_lines = get_column_wise_lines(columns, y_tolerance=y_tolerance)
    if verbose:
        line_count = sum(len(c.get("lines", [])) for c in columns_with_lines)
        print(f"Total lines: {line_count}")

    # 4) Sections (prints simplified JSON internally as well)
    result = segment_sections_from_columns(columns_with_lines)

    # 5) Contact info (regex-based)
    contact = extract_contact_info_from_lines(columns_with_lines)
    result["contact"] = contact

    # 6) Simplified JSON (print fully for the caller too)
    sim = simple_json(result)
    print(sim)

    return result, sim


def main():
    # Static inputs (edit as needed)
    PDF_PATH = "freshteams_resume/ReactJs/UI_Developer.pdf"
    MIN_WORDS = 10
    DYNAMIC_MIN_WORDS = True
    Y_TOL = 0.5
    VERBOSE = True

    result, sim = run_pipeline(
        PDF_PATH,
        min_words_per_column=MIN_WORDS,
        dynamic_min_words=DYNAMIC_MIN_WORDS,
        y_tolerance=Y_TOL,
        verbose=VERBOSE,
    )

    if VERBOSE:
        print("\nPretty print (section-wise with page/column):")
        print(simple_json(result))

        print("\nDetected contact info:")
        print(json.dumps(result.get("contact", {}), ensure_ascii=False, indent=2))

    # Optional: save
    # with open("segmented_full.json", "w", encoding="utf-8") as f:
    #     json.dump(result, f, ensure_ascii=False, indent=2)
    # with open("segmented_simple.json", "w", encoding="utf-8") as f:
    #     f.write(sim)


if __name__ == "__main__":
    main()