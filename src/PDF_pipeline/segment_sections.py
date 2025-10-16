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
        "methodologies", "frameworks", "strengths", "capabilities", "technical proficiency", "core skills",
        "skill set", "transferable skills", "technical skills & tools", "technical skills and tools",
        "technical skills & expertise", "technical skills and expertise", "professional skills & expertise",
        "professional skills and expertise", "it knowledge", "it skills", "it skills & expertise", "it skills and expertise",
        "it skills & tools", "it skills and tools", "it competencies", "skills summary", "skills & expertise",
        "skills and expertise"
    ],
    "Experience": [
        "experience", "current organisation", "current organization", "previous organzations","previous organisations", "job title", "work experience", "work history", "professional experience",
        "employment history", "career history", "relevant experience", "industry experience",
        "internship experience", "practical experience", "volunteer experience",
        "freelance experience", "project experience", "consulting experience", "military experience",
        "employment", "professional history", "employment details"
    ],
    "Projects": [
        "projects", "project", "relevant projects", "key projects", "selected projects",
        "major projects", "academic projects", "research projects", "open source projects",
        "client projects", "independent projects", "case studies", "portfolio projects",
        "course projects", "personal projects", "project work", "project experience",
        "project details", "project summary", "notable projects", "significant projects",
        "projects delivered", "projects completed", "projects handled"
    ],
    "Education": [
        "education", "educational qualifications", "academic background", "academics",
        "academic history", "training and education", "educational background",
        "college education", "schooling", "coursework", "academic achievements",
        "research and education", "qualifications", "educational details", "educational history",
        "education details", "education history", "educational qualifications", "educational profile",
        "academic qualifications", "academic profile", "education qualifications", "education qualification"
    ],
    "Certifications": [
        "certifications", "certificates", "licenses", "courses", "training", "professional development",
        "workshops", "online courses", "continuing education", "special training",
        "technical certifications", "certificates", "awards and certifications", "awards & certifications",
        "courses and certifications", "courses & certifications", "courses & certificates", "courses and certificates"
    ],
    "Achievements": [
        "achievements", "key achievements", "awards", "honors", "recognitions", "distinctions",
        "milestones", "accomplishments", "notable achievements", "career highlights", "extracurricular activities",
        "extracurricular & achievements", "extracurricular and achievements", "honors & achievements", "honors and achievements",
        "honors & awards", "honors and awards"
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
    "Additional Information": [
        "additional information", "additional details", "other information", "miscellaneous",
        "extra information", "further information", "more information"
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

# Precompute a map of keywords with separators removed (spaces, punctuation) to canonical.
# This helps match stylized headings like "e x p e r i e n c e" or "E-X-P-E-R-I-E-N-C-E".
CANON_NOSEP_MAP: Dict[str, str] = {
    re.sub(r"[^a-z0-9]+", "", kw.lower()): canon
    for canon, kws in SECTIONS.items()
    for kw in kws
}


# Utility
def clean_for_heading(text: str) -> str:
    t = text or ""
    # Normalize common decorative separators
    t = t.replace("•", " ").replace("·", " ").replace("|", " ")
    t = t.replace("—", "-").replace("–", "-")
    # Keep only a conservative set of characters for comparison
    t = re.sub(r'[^A-Za-z0-9\s:.-]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def uppercase_ratio(text: str) -> float:
    alphas = [c for c in text if c.isalpha()]
    if not alphas:
        return 0.0
    ups = [c for c in alphas if c.isupper()]
    return len(ups) / max(1, len(alphas))


def _despaced(text: str) -> str:
    """Remove all non-alphanumeric characters and lowercase."""
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def guess_section_name(text: str) -> Optional[str]:
    """
    Keyword matcher with stylized-heading support:
    - Normalize whitespace and case; allow trailing colon.
    - Exact match against SECTION_MAP.
    - Fallback: match after removing separators (spaces, hyphens, bullets):
      e x p e r i e n c e  -> experience
      E-X-P-E-R-I-E-N-C-E -> experience
    """
    if not text:
        return None

    s = clean_for_heading(text)
    if not s:
        return None

    s = s.strip()
    # Allow a trailing colon
    if s.endswith(':'):
        s0 = s[:-1].strip()
    else:
        s0 = s

    s_norm = re.sub(r"\s+", " ", s0).lower()
    if s_norm in SECTION_MAP:
        return SECTION_MAP[s_norm]

    # Fallback matching after removing separators
    s_nosep = _despaced(s0)
    return CANON_NOSEP_MAP.get(s_nosep)


def is_heading_line(line: Dict[str, Any], col_width: float, prev_line: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[str], float]:
    """
    Heading detection with stylized keyword matching.
    Consider a line a heading only if, after normalization (including de-spacing),
    it matches a known keyword/variant. Token/length constraints are not enforced
    here to allow spaced-letter headings; outlier filtering is handled later.
    """
    text = (line.get('text') or "").strip()
    if not text:
        return (False, None, 0.0)

    s = clean_for_heading(text).strip()
    # Remove optional trailing colon for comparison
    s_comp = s[:-1].strip() if s.endswith(':') else s
    if not s_comp:
        return (False, None, 0.0)

    canon = guess_section_name(s_comp)
    if canon is None:
        return (False, None, 0.0)

    # Match achieved via exact or stylized normalization
    return (True, canon, 1.0)


# ----------------- Enhanced segmentation with candidate analysis -----------------

def _reading_key(col: Dict[str, Any], line: Dict[str, Any]) -> Tuple[int, float, float]:
    page_no = int(col.get('page', 0))
    x_start = float(col.get('x_start', col.get('column_index', 0)))
    top = float(line.get('boundaries', {}).get('top', 0.0))
    return (page_no, x_start, top)


def _median(values: List[float]) -> float:
    if not values:
        return 0.0
    vs = sorted(v for v in values if isinstance(v, (int, float)))
    if not vs:
        return 0.0
    n = len(vs)
    mid = n // 2
    return float(vs[mid] if n % 2 == 1 else (vs[mid - 1] + vs[mid]) / 2.0)


def _safe(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except Exception:
        return default


def _collect_candidates(columns_with_lines: List[Dict[str, Any]]):
    """Return list of (pos_key, cand_dict)."""
    cands = []
    for col in sorted(columns_with_lines, key=lambda c: (c.get('page', 0), c.get('x_start', c.get('column_index', 0)))):
        col_width = float(col.get('width') or (col.get('x_end', 0) - col.get('x_start', 0)) or 0)
        page_no = int(col.get('page', 0))
        col_idx = int(col.get('column_index', 0))
        for li, line in enumerate(sorted(col.get('lines', []), key=lambda l: l.get('boundaries', {}).get('top', 0))):
            ok, canon, _ = is_heading_line(line, col_width, prev_line=None)
            if not ok:
                continue
            text = line.get('text', '') or ''
            m = dict(line.get('metrics', {}))
            b = dict(line.get('boundaries', {}))
            width_ratio = (_safe(m.get('line_width', b.get('width', 0))) / max(1.0, col_width))
            cand = {
                'page': page_no,
                'column_index': col_idx,
                'line_index': int(line.get('line_index', li)),
                'text': text,
                'canon': canon,
                'metrics': m,
                'boundaries': b,
                'width_ratio': width_ratio,
                'uppercase_ratio': uppercase_ratio(text),
                'col_width': col_width,
                'line_ref': line,
            }
            cands.append((_reading_key(col, line), cand))
    return cands


def _filter_candidates(cands: List[Tuple[Tuple[int, float, float], Dict[str, Any]]]) -> List[Tuple[Tuple[int, float, float], Dict[str, Any]]]:
    if not cands:
        return cands
    # Compute medians across candidates
    fonts = [_safe(c[1]['metrics'].get('avg_font_size')) for c in cands]
    spaces = [_safe(c[1]['metrics'].get('space_above')) for c in cands]
    widths = [_safe(c[1]['width_ratio']) for c in cands]
    uppers = [_safe(c[1]['uppercase_ratio']) for c in cands]

    med_font = _median(fonts) or 0.0
    med_space = _median(spaces) or 0.0
    med_width = _median(widths) or 0.0
    med_upper = _median(uppers) or 0.0

    kept = []
    for key, cand in cands:
        f = _safe(cand['metrics'].get('avg_font_size'))
        sa = _safe(cand['metrics'].get('space_above'))
        wr = _safe(cand.get('width_ratio'))
        ur = _safe(cand.get('uppercase_ratio'))
        wc = int(cand['line_ref'].get('properties', {}).get('word_count', 0))

        # Reject if simultaneously too small font, cramped, low uppercase, and looks like a sentence
        small_font = (med_font > 0 and f < 0.7 * med_font)
        cramped = (sa < max(4.0, 0.5 * med_space))
        low_upper = (ur < max(0.6, 0.7 * med_upper))
        long_words = (wc > 6 and wr > 0.9)

        if small_font and cramped and low_upper and long_words:
            # likely a false positive
            continue
        kept.append((key, cand))

    # If everything got filtered (over-aggressive), fall back to original candidates
    return kept if kept else cands


def _is_unknown_heading(line: Dict[str, Any], col_stats: Dict[str, float]) -> bool:
    """Heuristic to catch probable headings that didn't match any known keyword."""
    text = (line.get('text') or '').strip()
    if not text:
        return False
    s = clean_for_heading(text)
    tokens = [t for t in s.split() if t]
    if len(tokens) == 0 or len(tokens) > 7 or len(s) > 48:
        return False

    m = dict(line.get('metrics', {}))
    ur = uppercase_ratio(text)
    fs = _safe(m.get('avg_font_size'))
    sa = _safe(m.get('space_above'))

    col_font_med = col_stats.get('font_median', 0.0)
    col_space_med = col_stats.get('space_median', 0.0)

    # Heading-like if font noticeably larger or uppercase and has some space above or ends with ':'
    if (fs >= 1.15 * max(1.0, col_font_med) or ur >= 0.8 or s.endswith(':')) and (sa >= max(2.0, 1.0 * col_space_med)):
        # Also avoid numeric-only, e.g., dates
        if re.search(r"[A-Za-z]", s):
            # Don't treat as unknown if it actually matches a known section after normalization
            return guess_section_name(s) is None
    return False


def segment_sections_from_columns(columns_with_lines: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Segment columns-with-lines into sections. Two-pass approach:
    1) Collect all heading candidates (with stylized matching) and filter outliers using metrics.
    2) Iterate in reading order creating sections at accepted headings; collect probable unknown headings.
    Returns a full JSON containing sections with full line documents. Also prints a simplified JSON.
    """
    if not columns_with_lines:
        result = {"meta": {"pages": 0, "columns": 0, "sections": 0}, "sections": []}
        print(json.dumps([{"section": "Unknown", "lines": []}], ensure_ascii=False, indent=2))
        return result

    # First pass: candidates
    cands = _collect_candidates(columns_with_lines)
    cands = _filter_candidates(cands)
    accepted_positions: Dict[Tuple[int, int, int], str] = {}
    for _, c in cands:
        key = (c['page'], c['column_index'], c['line_index'])
        accepted_positions[key] = c['canon']

    # Precompute per-column stats
    col_stats_map: Dict[Tuple[int, int], Dict[str, float]] = {}
    for col in columns_with_lines:
        page_no = int(col.get('page', 0))
        col_idx = int(col.get('column_index', 0))
        lines = col.get('lines', [])
        fonts = [_safe(l.get('metrics', {}).get('avg_font_size')) for l in lines]
        spaces = [_safe(l.get('metrics', {}).get('space_above')) for l in lines]
        col_stats_map[(page_no, col_idx)] = {
            'font_median': _median(fonts),
            'space_median': _median(spaces),
            'width': float(col.get('width') or (col.get('x_end', 0) - col.get('x_start', 0)) or 0)
        }

    # Reading order: by page, then by x_start (or column_index), then by line top
    cols_sorted = sorted(
        columns_with_lines,
        key=lambda c: (c.get('page', 0), c.get('x_start', c.get('column_index', 0)))
    )

    sections: List[Dict[str, Any]] = []
    current_section = {
        "section": "Contact Information",
        "lines": []
    }
    unknown_headings: List[Dict[str, Any]] = []

    for col in cols_sorted:
        page_no = int(col.get('page', 0))
        col_idx = int(col.get('column_index', 0))
        col_width = float(col.get('width') or (col.get('x_end', 0) - col.get('x_start', 0)) or 0)
        lines = sorted(col.get('lines', []), key=lambda l: l.get('boundaries', {}).get('top', 0))
        stats = col_stats_map.get((page_no, col_idx), {})

        for li, line in enumerate(lines):
            key = (page_no, col_idx, int(line.get('line_index', li)))
            if key in accepted_positions:
                if current_section["lines"]:
                    sections.append(current_section)
                sec_name = accepted_positions[key] or "Section"
                current_section = {"section": sec_name, "lines": []}
                # Skip adding the heading line itself
                continue

            # Not a recognized heading: record probable unknown headings separately
            if _is_unknown_heading(line, stats):
                unknown_headings.append({
                    "page": page_no,
                    "column_index": col_idx,
                    "line_index": int(line.get('line_index', li)),
                    "text": line.get('text', '') or '',
                    "boundaries": dict(line.get('boundaries', {})),
                    "properties": dict(line.get('properties', {})),
                    "metrics": dict(line.get('metrics', {})),
                })

            # Regular content line
            line_out = {
                "page": page_no,
                "column_index": col_idx,
                "line_index": int(line.get('line_index', li)),
                "text": line.get('text', "") or "",
                "boundaries": dict(line.get('boundaries', {})),
                "properties": dict(line.get('properties', {})),
                "metrics": dict(line.get('metrics', {}))
            }
            current_section["lines"].append(line_out)

    if current_section["lines"]:
        sections.append(current_section)

    # Merge duplicate sections while preserving order of first appearance
    merged: List[Dict[str, Any]] = []
    seen: Dict[str, Dict[str, Any]] = {}
    for sec in sections:
        name = sec["section"]
        canon = guess_section_name(name) or name
        name_key = canon
        if name_key in seen:
            seen[name_key]["lines"].extend(sec["lines"])
        else:
            new_sec = {"section": name_key, "lines": list(sec["lines"])}
            seen[name_key] = new_sec
            merged.append(new_sec)

    # If we found probable unknown headings, add them as a dedicated section at the end
    if unknown_headings:
        merged.append({
            "section": "Unknown Sections",
            "lines": [
                {
                    "page": uh["page"],
                    "column_index": uh["column_index"],
                    "line_index": uh["line_index"],
                    "text": uh["text"],
                    "boundaries": uh.get("boundaries", {}),
                    "properties": uh.get("properties", {}),
                    "metrics": uh.get("metrics", {}),
                }
                for uh in unknown_headings
            ]
        })

    # Build meta
    all_pages = sorted(set(c.get('page', 0) for c in cols_sorted))
    result = {
        "meta": {
            "pages": len(all_pages),
            "page_list": all_pages,
            "columns": len(cols_sorted),
            "sections": len(merged),
            "lines_total": sum(len(sec["lines"]) for sec in merged),
            "unknown_headings_count": len(unknown_headings)
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
        return json.dumps([{ "section": "Unknown", "lines": [] }], ensure_ascii=False, indent=2)
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

    PDF_PATH = "freshteams_resume/ReactJs/Prajkta_Trainee_salesforce_developer_resume.pdf"
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


# if __name__ == "__main__":
#     main()