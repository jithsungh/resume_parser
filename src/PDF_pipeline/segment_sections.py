import re
import json
from typing import List, Dict, Any, Tuple, Optional

# Input to this module:
# - columns_with_lines: output of get_lines.get_column_wise_lines(...)
#   Each column dict contains:
#     {
#       'page': int,
#       'column_index': int,
#       'x_start': int/float, 'x_end': int/float, 'width': int/float,
#       'words': [...],
#       'lines': [
#           {
#               'line_index': int,
#               'text': str,
#               'boundaries': { x0, x1, top, bottom, width, height },
#               'properties': { char_count, word_count, char_count_no_spaces },
#               'metrics': { height, space_above, space_below, char_count, word_count, avg_font_size, line_width }
#           }, ...
#       ]
#     }

# Expanded section vocabulary (canonical -> variants)
SECTIONS: Dict[str, List[str]] = {
    "Contact Information": [
        "contact", "contact information", "contact details", "personal details",
        "basic information", "contact info", "bio"
    ],
    "Summary": [
        "summary", "professional summary", "career summary", "profile", "about me",
        "executive summary", "personal profile", "introduction", "career objective",
        "objective", "professional profile", "career overview", "personal statement",
        "highlights", "overview"
    ],
    "Skills": [
        "skills", "key skills", "technical skills", "non technical skills", "nontechnical skills",
        "technical expertise", "core competencies", "competencies", "areas of expertise",
        "professional skills", "hard skills", "soft skills", "language skills", "computer skills",
        "programming languages", "tools", "tools and technologies", "technologies", "tech stack",
        "methodologies", "frameworks", "strengths", "capabilities", "technical proficiency"
    ],
    "Experience": [
        "experience", "work experience", "work history", "professional experience",
        "employment history", "career history", "relevant experience", "industry experience",
        "internship experience", "practical experience", "volunteer experience",
        "freelance experience", "project experience", "consulting experience", "military experience",
        "employment", "professional history"
    ],
    "Projects": [
        "projects", "project", "relevant projects", "key projects", "selected projects",
        "major projects", "academic projects", "research projects", "open source projects",
        "client projects", "independent projects", "case studies", "portfolio projects",
        "course projects", "personal projects", "project work", "project experience",
        "project details", "project summary", "notable projects", "significant projects"
    ],
    "Education": [
        "education", "educational qualifications", "academic background", "academics",
        "academic history", "training and education", "educational background",
        "college education", "schooling", "coursework", "academic achievements",
        "research and education", "qualifications"
    ],
    "Certifications": [
        "certifications", "licenses", "courses", "training", "professional development",
        "workshops", "online courses", "continuing education", "special training",
        "technical certifications", "certificates", "awards and certifications", "awards & certifications"
    ],
    "Achievements": [
        "achievements", "key achievements", "awards", "honors", "recognitions", "distinctions",
        "milestones", "accomplishments", "notable achievements", "career highlights"
    ],
    "Publications": [
        "publications", "research papers", "journal articles", "conference papers",
        "books", "book chapters", "academic publications", "white papers", "preprints"
    ],
    "Research": [
        "research", "research experience", "research work", "research summary",
        "thesis", "dissertation", "research interests"
    ],
    "Languages": [
        "languages", "language proficiency", "spoken languages", "language skills"
    ],
    "Volunteer": [
        "volunteer", "volunteering", "community involvement", "social work",
        "philanthropy", "community service", "volunteer activities"
    ],
    "Hobbies": [
        "hobbies", "interests", "personal interests", "extracurricular activities",
        "outside interests", "personal pursuits", "leisure activities"
    ],
    "References": [
        "references", "referees"
    ],
    "Declarations": [
        "declaration", "declarations", "disclaimer", "self declaration"
    ]
}

# Map each keyword (lower) to canonical section
SECTION_MAP: Dict[str, str] = {
    kw.lower(): canon for canon, kws in SECTIONS.items() for kw in kws
}

# Precompile regex for quick matching (word-boundary, optional trailing colon)
SECTION_PATTERNS: List[Tuple[re.Pattern, str]] = []
for canon, kws in SECTIONS.items():
    for kw in kws:
        # e.g., r'^\s*(?:relevant\s+projects|projects)\s*:?\s*$' (anchored, whole line, optional colon)
        pat = re.compile(r'^\s*' + re.escape(kw) + r'\s*:?\s*$', flags=re.IGNORECASE)
        SECTION_PATTERNS.append((pat, canon))

# Utility
def clean_for_heading(text: str) -> str:
    t = text or ""
    t = re.sub(r'[^A-Za-z0-9\s:.-]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def uppercase_ratio(text: str) -> float:
    alphas = [c for c in text if c.isalpha()]
    if not alphas:
        return 0.0
    ups = [c for c in alphas if c.isupper()]
    return len(ups) / max(1, len(alphas))

def guess_section_name(text: str) -> Optional[str]:
    if not text:
        return None
    s = clean_for_heading(text).lower()
    # Exact pattern (line == keyword or keyword + colon)
    for pat, canon in SECTION_PATTERNS:
        if pat.match(s):
            return canon
    # Soft match: startswith or contains keyword at boundaries (short lines only)
    tokens = s.split()
    if len(tokens) <= 6:
        joined = ' '.join(tokens)
        for kw, canon in SECTION_MAP.items():
            if kw == joined:
                return canon
            if joined.startswith(kw + " ") or joined.endswith(" " + kw):
                return canon
    return None

def is_heading_line(line: Dict[str, Any], col_width: float, prev_line: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[str], float]:
    """
    Decide if a line is a section heading using metrics to avoid false positives.
    Requires BOTH: strong metrics score and lexical signal (canonical keyword or trailing colon).
    Returns (is_heading, section_name, score).
    """
    text = (line.get('text') or "").strip()
    if not text:
        return (False, None, 0.0)

    props = line.get('properties', {}) or {}
    mets = line.get('metrics', {}) or {}
    bounds = line.get('boundaries', {}) or {}

    wc = props.get('word_count') or 0
    cc = props.get('char_count') or len(text)
    fs = mets.get('avg_font_size') or (bounds.get('height') or 0)
    sa = mets.get('space_above') or 0
    lw = mets.get('line_width') or (bounds.get('width') or 0)

    s_text = clean_for_heading(text)
    ends_colon = s_text.endswith(':')
    ends_punct = s_text.endswith('.') or s_text.endswith(';') or s_text.endswith(',')
    up_ratio = uppercase_ratio(s_text)

    canon = guess_section_name(s_text)

    # Scoring (scale-invariant, minimal absolute thresholds)
    score = 0.0
    if canon:
        score += 3.0                       # strong lexical match
    if ends_colon:
        score += 1.0                       # headings often end with colon
    if up_ratio >= 0.6 or s_text.istitle():
        score += 1.0                       # heading-like casing
    if wc <= 6 and cc <= 48:
        score += 1.0                       # short line
    if fs and sa >= 0.6 * fs:
        score += 1.0                       # spacing above suggests a block break

    # Negative evidences
    if ends_punct:
        score -= 2.0                       # sentence, not heading
    if col_width and lw > 0.85 * col_width and wc > 6:
        score -= 2.0                       # paragraph-like
    # Avoid false positive: single wrapped word like "Experience" at end of paragraph
    if wc == 1 and not ends_colon and fs and sa < 0.4 * fs:
        score -= 3.0

    # If previous line exists and there's no real gap, demote unless explicit colon/exact match
    if prev_line is not None and not ends_colon and not canon:
        prev_m = prev_line.get('metrics', {}) or {}
        gap = mets.get('space_above') or 0
        pfs = prev_m.get('avg_font_size') or fs or 0
        if pfs and gap < 0.3 * pfs:
            score -= 1.5

    # Final decision: require BOTH metrics (score) and lexical/colon signal
    is_heading = (score >= 3.0) and (canon is not None or ends_colon)
    return (is_heading, canon, score)


def segment_sections_from_columns(columns_with_lines: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Segment columns-with-lines into sections. Processes columns per page in reading order.
    Returns a full JSON containing sections with full line documents. Also prints a simplified JSON.
    """
    if not columns_with_lines:
        result = {"meta": {"pages": 0, "columns": 0, "sections": 0}, "sections": []}
        print(json.dumps([{"section": "Unknown", "lines": []}], ensure_ascii=False, indent=2))
        return result

    # Reading order: by page, then by x_start (or column_index), then by line top
    cols_sorted = sorted(
        columns_with_lines,
        key=lambda c: (c.get('page', 0), c.get('x_start', c.get('column_index', 0)))
    )

    sections: List[Dict[str, Any]] = []
    # Default bucket until first heading
    current_section = {
        "section": "Contact Information",
        "lines": []  # full line docs
    }

    prev_line_ctx: Optional[Tuple[int, int, Dict[str, Any]]] = None  # (page, col_idx, line)

    for col in cols_sorted:
        col_width = float(col.get('width') or (col.get('x_end', 0) - col.get('x_start', 0)) or 0)
        page_no = int(col.get('page', 0))
        col_idx = int(col.get('column_index', 0))
        lines = sorted(col.get('lines', []), key=lambda l: l.get('boundaries', {}).get('top', 0))

        for li, line in enumerate(lines):
            # Attach page/column to line for downstream consumers
            line_out = {
                "page": page_no,
                "column_index": col_idx,
                "line_index": int(line.get('line_index', li)),
                "text": line.get('text', "") or "",
                "boundaries": dict(line.get('boundaries', {})),
                "properties": dict(line.get('properties', {})),
                "metrics": dict(line.get('metrics', {}))
            }

            # Determine previous line in same page+column (for tighter FP control)
            prev_line = None
            if prev_line_ctx and prev_line_ctx[0] == page_no and prev_line_ctx[1] == col_idx:
                prev_line = prev_line_ctx[2]

            is_head, canon_name, _score = is_heading_line(line, col_width, prev_line=prev_line)

            if is_head:
                # Save current section if it has content
                if current_section["lines"]:
                    sections.append(current_section)
                # Start new section with canonical name if known
                sec_name = canon_name or clean_for_heading(line_out["text"]).rstrip(':').strip().title() or "Section"
                current_section = {"section": sec_name, "lines": []}
                # Do not include the heading line itself as content
            else:
                current_section["lines"].append(line_out)

            # Update previous line context for same page/column
            prev_line_ctx = (page_no, col_idx, line)

    # Flush last section
    if current_section["lines"]:
        sections.append(current_section)

    # Merge duplicate sections while preserving order of first appearance
    merged: List[Dict[str, Any]] = []
    seen: Dict[str, Dict[str, Any]] = {}
    for sec in sections:
        name = sec["section"]
        # Normalize name to canonical where possible
        canon = guess_section_name(name) or name
        name_key = canon
        if name_key in seen:
            seen[name_key]["lines"].extend(sec["lines"])
        else:
            new_sec = {"section": name_key, "lines": list(sec["lines"])}
            seen[name_key] = new_sec
            merged.append(new_sec)

    # Build meta
    all_pages = sorted(set(c.get('page', 0) for c in cols_sorted))
    result = {
        "meta": {
            "pages": len(all_pages),
            "page_list": all_pages,
            "columns": len(cols_sorted),
            "sections": len(merged),
            "lines_total": sum(len(sec["lines"]) for sec in merged),
        },
        "sections": merged
    }

    # Print simplified JSON as requested (full print, not a glimpse)
    printable = [
        {
            "section": sec["section"],
            "lines": [ln.get("text", "") for ln in sec["lines"]]
        }
        for sec in merged
    ]
    print(json.dumps(printable, ensure_ascii=False, indent=2))

    return result


def simple_json(data: Dict[str, Any]) -> str:
    """
    Convert full JSON to simplified JSON with just section names and line texts.
    """
    if not data or 'sections' not in data:
        return json.dumps([{"section": "Unknown", "lines": []}], ensure_ascii=False, indent=2)
    printable = [
        {
            "section": sec.get("section", "Unknown"),
            "lines": [ln.get("text", "") for ln in sec.get("lines", [])]
        }
        for sec in data.get("sections", [])
    ]
    return json.dumps(printable, ensure_ascii=False, indent=2)


def pretty_print_segmented_sections(data: Dict[str, Any]) -> None:
    """
    Pretty print the segmented sections from the full JSON result.
    """
    sections = data.get("sections", [])
    for sec in sections:
        print(f"\n=== Section: {sec.get('section', 'Unknown')} ===")
        for line in sec.get("lines", []):
            page = line.get("page", 0)
            col_idx = line.get("column_index", 0)
            text = line.get("text", "")
            print(f"[Page {page}, Col {col_idx}] {text}")


# --------- Demo (static inputs) ----------
# This demo assumes you already produced column-wise lines using get_lines.get_column_wise_lines.
# If you want to test end-to-end here, uncomment the imports and generate columns below.

def main():
    # Optional end-to-end demo (static).
    from src.PDF_pipeline.get_words import get_words_from_pdf
    from src.PDF_pipeline.split_columns import split_columns
    from src.PDF_pipeline.get_lines import get_column_wise_lines

    PDF_PATH = "freshteams_resume/ReactJs/UI_Developer.pdf"
    MIN_WORDS = 10
    DYNAMIC_MIN_WORDS = True
    Y_TOL = 1.0

    print("Extracting words...")
    pages = get_words_from_pdf(PDF_PATH)
    print(f"Pages: {len(pages)}")

    print("Splitting into columns...")
    columns = split_columns(pages, min_words_per_column=MIN_WORDS, dynamic_min_words=DYNAMIC_MIN_WORDS)
    print(f"Columns: {len(columns)}")

    print("Building lines (column-wise)...")
    columns_with_lines = get_column_wise_lines(columns, y_tolerance=Y_TOL)

    print("Segmenting sections...")
    data = segment_sections_from_columns(columns_with_lines)

    print("\nPretty print:")
    pretty_print_segmented_sections(data)

    print("\nSimplified JSON:")
    print(simple_json(data))


if __name__ == "__main__":
    main()