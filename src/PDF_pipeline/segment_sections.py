import re
import json
from typing import List, Dict, Any, Tuple, Optional
import os
from pathlib import Path

# Import section splitter for multi-section header detection
try:
    from src.core.section_splitter import get_section_splitter
    _SECTION_SPLITTER_AVAILABLE = True
except ImportError:
    _SECTION_SPLITTER_AVAILABLE = False
    print("[WARNING] Section splitter not available, multi-section headers may not be detected")

# Import section learner for auto-learning
try:
    from src.core.section_learner import SectionLearner
    _SECTION_LEARNER_AVAILABLE = True
    _section_learner_instance = None
except ImportError:
    _SECTION_LEARNER_AVAILABLE = False
    print("[WARNING] Section learner not available, auto-learning disabled")

def _get_section_learner():
    """Get singleton section learner instance"""
    global _section_learner_instance
    if _section_learner_instance is None and _SECTION_LEARNER_AVAILABLE:
        try:
            config_path = Path(__file__).parent.parent.parent / "config" / "sections_database.json"
            _section_learner_instance = SectionLearner(str(config_path))
            _section_learner_instance.verbose = _SEG_DEBUG
        except Exception as e:
            if _SEG_DEBUG:
                print(f"[segment] Could not initialize section learner: {e}")
    return _section_learner_instance

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
        "highlights", "overview", "professional synopsis" 
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
        "skills and expertise", "technical skill set"  
    ],
    "Experience": [
        "experience", "current organisation", "current organization", "previous organzations","previous organisations", "job title", "work experience", "work history", "professional experience",
        "employment history", "career history", "relevant experience", "industry experience",
        "internship experience", "practical experience", "volunteer experience",
        "freelance experience", "project experience", "consulting experience", "military experience",
        "employment", "professional history", "employment details",
        "professional experiance", "experience summary", "company details", "internship",
        "exprofessional experience", "employment profile", "experiance & projects", "experien",
        "experiance and work location"
    ],
    "Projects": [
        "projects", "project", "relevant projects", "key projects", "selected projects",
        "major projects", "academic projects", "research projects", "open source projects",
        "client projects", "independent projects", "case studies", "portfolio projects",
        "course projects", "personal projects", "project work", "project experience",
        "project details", "project summary", "notable projects", "significant projects",
        "projects delivered", "projects completed", "projects handled",
        "details of the projects worked on", "open source"
    ],
    "Education": [
        "education", "educational qualifications", "academic background", "academics",
        "academic history", "training and education", "educational background",
        "college education", "schooling", "coursework", "academic achievements",
        "research and education", "qualifications", "educational details", "educational history",
        "education details", "education history", "educational qualifications", "educational profile",
        "academic qualifications", "academic profile", "education qualifications", "education qualification",
        "academic details", "academic achievements",
        "education & certifications", "education and certifications", "education certifications"
    ],
    "Certifications": [
        "certifications", "certificates", "licenses", "courses", "training", "professional development",
        "workshops", "online courses", "continuing education", "special training",
        "technical certifications", "certificates", "awards and certifications", "awards & certifications",
        "courses and certifications", "courses & certifications", "courses & certificates", "courses and certificates",
        "certificate"
    ],
    "Achievements": [
        "achievements", "key achievements", "awards", "honors", "recognitions", "distinctions",
        "milestones", "accomplishments", "notable achievements", "career highlights", "extracurricular activities",
        "extracurricular & achievements", "extracurricular and achievements", "honors & achievements", "honors and achievements",
        "honors & awards", "honors and awards",
        "extracuricular activities"
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
        "languages", "language proficiency", "spoken languages", "language skills",
        "languages known", "languages known and other information"
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

# ---------------- Self-learning: load learned variants and extend SECTIONS ----------------
_LEARNED_FILE_CANDIDATES = [
    Path(__file__).resolve().parent / "sections_learned.jsonl",
    Path(__file__).resolve().parent / "sections_learned.json",
    Path.cwd() / "sections_learned.jsonl",
    Path.cwd() / "sections_learned.json",
]


def _load_learned_variants() -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for p in _LEARNED_FILE_CANDIDATES:
        try:
            if not p.exists():
                continue
            if p.suffix.lower() == ".jsonl":
                with p.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                        except Exception:
                            continue
                        canon = (obj.get("canonical") or obj.get("section") or "").strip()
                        header = (obj.get("header") or obj.get("text") or "").strip()
                        if canon and header:
                            out.setdefault(canon, []).append(header)
            else:
                with p.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    for canon, variants in data.items():
                        if isinstance(variants, list):
                            out.setdefault(canon, []).extend([str(v) for v in variants])
                elif isinstance(data, list):
                    for obj in data:
                        if not isinstance(obj, dict):
                            continue
                        canon = (obj.get("canonical") or obj.get("section") or "").strip()
                        header = (obj.get("header") or obj.get("text") or "").strip()
                        if canon and header:
                            out.setdefault(canon, []).append(header)
        except Exception:
            continue
    return out


# Apply learned variants into SECTIONS before building maps
try:
    _learned = _load_learned_variants()
    for _canon, _vars in _learned.items():
        if not _vars:
            continue
        if _canon not in SECTIONS:
            # if an unknown canonical appears, treat as Additional Information bucket
            SECTIONS.setdefault("Additional Information", []).extend(_vars)
        else:
            SECTIONS[_canon].extend(_vars)
except Exception:
    pass

# ---------------- Build maps from (possibly extended) SECTIONS ----------------
SECTION_MAP: Dict[str, str] = {
    kw.lower(): canon for canon, kws in SECTIONS.items() for kw in kws
}

CANON_NOSEP_MAP: Dict[str, str] = {
    re.sub(r"[^a-z0-9]+", "", kw.lower()): canon
    for canon, kws in SECTIONS.items()
    for kw in kws
}

# Debug/feature flags via env
def _env_flag(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).lower() in ("1", "true", "yes", "on")

_SEG_DEBUG = _env_flag("SEG_DEBUG", False)


def _embeddings_allowed() -> bool:
    # Opt-in to embeddings to avoid slow model downloads by default
    return _env_flag("SEG_ENABLE_EMBEDDINGS", False)

# Utility
def clean_for_heading(text: str) -> str:
    t = text or ""
    
    # Handle letter-spaced text (e.g., "P R O F I L E" -> "PROFILE")
    # Check if text has single letters separated by spaces
    words = t.split()
    if len(words) > 1 and all(len(w) == 1 and w.isalpha() for w in words):
        t = ''.join(words)  # Join single letters
    
    # Normalize common decorative separators
    t = t.replace("•", " ").replace("·", " ").replace("|", " ")
    t = t.replace("&", " and ")  # keep meaning of '&' before stripping
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


def _split_multi_section_header(text: str) -> list[str]:
    """
    Split potential multi-section headers like 'EXPERIENCE SKILLS' into separate sections.
    Returns list of potential section names found in the text.
    """
    if not text:
        return []
    
    # Clean and normalize
    cleaned = clean_for_heading(text).strip()
    if not cleaned:
        return []
    
    # Split by common separators
    words = re.split(r'[\s\|/&]+', cleaned)
    
    # Filter out very short words (likely not section names)
    potential_sections = [w.strip() for w in words if len(w.strip()) > 2]
    
    # Try to match each word as a section
    matched_sections = []
    for word in potential_sections:
        # Try exact match first
        word_lower = word.lower()
        if word_lower in SECTION_MAP:
            matched_sections.append(SECTION_MAP[word_lower])
            continue
        
        # Try despaced match
        word_nosep = _despaced(word)
        if word_nosep in CANON_NOSEP_MAP:
            matched_sections.append(CANON_NOSEP_MAP[word_nosep])
            continue
    
    return matched_sections


def guess_section_name(text: str) -> Optional[str]:
    """
    Keyword matcher with stylized-heading support:
    - Normalize whitespace and case; allow trailing colon.
    - Exact match against SECTION_MAP.
    - Fallback: match after removing separators (spaces, hyphens, bullets):
      e x p e r i e n c e  -> experience
      E-X-P-E-R-I-E-N-C-E -> experience
    - Handle multi-section headers like "EXPERIENCE SKILLS" (return first match)
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
    if s_nosep in CANON_NOSEP_MAP:
        return CANON_NOSEP_MAP[s_nosep]
    
    # Try splitting multi-section headers
    multi_sections = _split_multi_section_header(s0)
    if multi_sections:
        return multi_sections[0]  # Return first matched section
    
    return None


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
    if _SEG_DEBUG:
        print(f"[segment] candidates collected: {len(cands)}")
    return cands


def _metric_font_size(m: Dict[str, Any]) -> float:
    """Prefer span-derived font size from PyMuPDF; fallback to geometric avg_font_size."""
    fs_span = m.get('avg_span_font_size')
    try:
        fs_span = float(fs_span)
    except Exception:
        fs_span = None
    if isinstance(fs_span, float) and fs_span > 0:
        return fs_span
    return _safe(m.get('avg_font_size'))


def _filter_candidates(cands: List[Tuple[Tuple[int, float, float], Dict[str, Any]]]) -> List[Tuple[Tuple[int, float, float], Dict[str, Any]]]:
    if not cands:
        return cands
    # Compute medians across candidates (font: prefer span font size)
    fonts = [_metric_font_size(c[1].get('metrics', {})) for c in cands]
    spaces = [_safe(c[1]['metrics'].get('space_above')) for c in cands]
    widths = [_safe(c[1]['width_ratio']) for c in cands]
    uppers = [_safe(c[1]['uppercase_ratio']) for c in cands]
    bolds = [_safe(c[1]['metrics'].get('bold_ratio')) for c in cands]

    med_font = _median(fonts) or 0.0
    med_space = _median(spaces) or 0.0
    med_width = _median(widths) or 0.0
    med_upper = _median(uppers) or 0.0
    med_bold = _median(bolds) or 0.0

    kept = []
    for key, cand in cands:
        m = cand.get('metrics', {})
        f = _metric_font_size(m)
        sa = _safe(m.get('space_above'))
        wr = _safe(cand.get('width_ratio'))
        ur = _safe(cand.get('uppercase_ratio'))
        br = _safe(m.get('bold_ratio'))
        wc = int(cand['line_ref'].get('properties', {}).get('word_count', 0))

        # Reject only if multiple signals indicate non-heading
        small_font = (med_font > 0 and f < 0.7 * med_font)
        cramped = (sa < max(4.0, 0.5 * med_space))
        low_upper = (ur < max(0.6, 0.7 * med_upper))
        low_bold = (br < max(0.15, 0.5 * med_bold))  # allow headings that aren't bold
        long_words = (wc > 6 and wr > 0.9)

        # If either bold or uppercase or normal font size, keep even if other signals are weak
        looks_like_heading = (br >= 0.3) or (ur >= 0.7) or (not small_font)
        if not looks_like_heading and small_font and cramped and low_upper and low_bold and long_words:
            continue
        kept.append((key, cand))

    if _SEG_DEBUG:
        print(f"[segment] candidates kept after filter: {len(kept)} (from {len(cands)})")
    return kept if kept else cands


def _is_unknown_heading(line: Dict[str, Any], col_stats: Dict[str, float]) -> bool:
    """Heuristic to catch probable headings that didn't match any known keyword.
    Uses PyMuPDF metrics when available (bold_ratio, avg_span_font_size).
    """
    text = (line.get('text') or '').strip()
    if not text:
        return False
    s = clean_for_heading(text)
    tokens = [t for t in s.split() if t]
    if len(tokens) == 0 or len(tokens) > 7 or len(s) > 48:
        return False

    m = dict(line.get('metrics', {}))
    ur = uppercase_ratio(text)
    fs = _metric_font_size(m)
    br = _safe(m.get('bold_ratio'))
    sa = _safe(m.get('space_above'))

    col_font_med = col_stats.get('font_median', 0.0)
    col_space_med = col_stats.get('space_median', 0.0)

    # Heading-like if larger font OR bold OR uppercase, and some space above, or trailing colon
    font_or_style = (fs >= 1.15 * max(1.0, col_font_med)) or (br >= 0.35) or (ur >= 0.8)
    spaced = (sa >= max(2.0, 1.0 * col_space_med))
    if (font_or_style and spaced) or s.endswith(':'):
        if re.search(r"[A-Za-z]", s):
            return guess_section_name(s) is None
    return False


# ---------------- Column Re-splitting for Multi-Section Headers ----------------

def _resplit_columns_for_multi_sections(columns_with_lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Detect multi-section headers and re-split columns accordingly.
    
    When a line contains multiple section headers (e.g., "EXPERIENCE    SKILLS"),
    this function splits the page/column into separate columns so each section
    can be processed independently.
    
    Args:
        columns_with_lines: Original columns from get_lines.get_column_wise_lines()
        
    Returns:
        Re-split columns (may have more columns than input if multi-sections found)
    """
    if not _SECTION_SPLITTER_AVAILABLE:
        return columns_with_lines
    
    from src.PDF_pipeline.split_columns import split_columns_by_multi_section_header
    
    # Group columns by page for processing
    pages_map = {}
    for col in columns_with_lines:
        page_no = col.get('page', 0)
        if page_no not in pages_map:
            pages_map[page_no] = []
        pages_map[page_no].append(col)
    
    result_columns = []
    splitter = get_section_splitter()
    
    for page_no, page_cols in sorted(pages_map.items()):
        # Check each column for multi-section headers
        multi_section_found = False
        multi_section_line = None
        
        for col in page_cols:
            lines = col.get('lines', [])
            
            for line in lines:
                text = line.get('text', '').strip()
                
                if not text or len(text) < 10:
                    continue
                
                # Check if this line has multi-section header
                try:
                    multi_sections = splitter.detect_multi_section_header(text)
                    
                    if len(multi_sections) >= 2:
                        if _SEG_DEBUG:
                            section_names = [s[0] for s in multi_sections]
                            print(f"[resplit] Multi-section header found on page {page_no}: '{text}' -> {section_names}")
                        
                        multi_section_found = True
                        multi_section_line = {
                            'text': text,
                            'boundaries': line.get('boundaries', {}),
                            'multi_sections': [s[0] for s in multi_sections]
                        }
                        break
                except Exception as e:
                    if _SEG_DEBUG:
                        print(f"[resplit] Error checking multi-section: {e}")
            
            if multi_section_found:
                break
        
        if multi_section_found and multi_section_line:
            # Need to re-split this page
            if _SEG_DEBUG:
                print(f"[resplit] Re-splitting page {page_no} based on multi-section header")
            
            # Collect all words from this page
            all_words = []
            page_width = 595  # Default PDF width
            
            for col in page_cols:
                words = col.get('words', [])
                all_words.extend(words)
                # Get page width from first column
                if 'width' in col:
                    page_width = col.get('x_end', 595)
            
            if not all_words:
                # No words, keep original columns
                result_columns.extend(page_cols)
                continue
            
            # Re-split columns based on multi-section positions
            try:
                new_columns = split_columns_by_multi_section_header(
                    words=all_words,
                    page_width=page_width,
                    multi_section_line=multi_section_line,
                    min_words_per_column=5
                )
                
                if new_columns and len(new_columns) >= 2:
                    if _SEG_DEBUG:
                        print(f"[resplit] Split page {page_no} into {len(new_columns)} columns")
                    
                    # Now we need to rebuild lines for each new column
                    from src.PDF_pipeline.get_lines import get_column_wise_lines_from_words
                    
                    # Process each new column
                    for new_col in new_columns:
                        new_col['page'] = page_no
                        
                        # Generate lines from words
                        col_words = new_col.get('words', [])
                        
                        # Group words into lines (simple approach: by Y-coordinate)
                        lines_dict = {}
                        for word in col_words:
                            y = int(word.get('top', 0))
                            if y not in lines_dict:
                                lines_dict[y] = []
                            lines_dict[y].append(word)
                        
                        # Build line objects
                        lines = []
                        for line_idx, (y, words_in_line) in enumerate(sorted(lines_dict.items())):
                            words_in_line.sort(key=lambda w: w.get('x0', 0))
                            
                            line_text = ' '.join(w.get('text', '') for w in words_in_line)
                            
                            # Calculate boundaries
                            x0 = min(w.get('x0', 0) for w in words_in_line)
                            x1 = max(w.get('x1', 0) for w in words_in_line)
                            top = min(w.get('top', 0) for w in words_in_line)
                            bottom = max(w.get('bottom', 0) for w in words_in_line)
                            
                            lines.append({
                                'line_index': line_idx,
                                'text': line_text,
                                'boundaries': {
                                    'x0': x0, 'x1': x1,
                                    'top': top, 'bottom': bottom,
                                    'width': x1 - x0,
                                    'height': bottom - top
                                },
                                'properties': {
                                    'char_count': len(line_text),
                                    'word_count': len(words_in_line),
                                    'char_count_no_spaces': len(line_text.replace(' ', ''))
                                },
                                'metrics': {
                                    'height': bottom - top,
                                    'space_above': 0,  # Computed later
                                    'space_below': 0,  # Computed later
                                    'char_count': len(line_text),
                                    'word_count': len(words_in_line),
                                    'avg_font_size': 12,  # Default
                                    'line_width': x1 - x0
                                }
                            })
                        
                        # Compute space_above and space_below
                        for i, line in enumerate(lines):
                            if i > 0:
                                prev_bottom = lines[i-1]['boundaries']['bottom']
                                curr_top = line['boundaries']['top']
                                line['metrics']['space_above'] = max(0, curr_top - prev_bottom)
                            
                            if i < len(lines) - 1:
                                curr_bottom = line['boundaries']['bottom']
                                next_top = lines[i+1]['boundaries']['top']
                                line['metrics']['space_below'] = max(0, next_top - curr_bottom)
                        
                        new_col['lines'] = lines
                        
                        # Add section hint if available
                        if 'section_hint' in new_col:
                            if _SEG_DEBUG:
                                print(f"[resplit] Column {new_col['column_index']} has section hint: {new_col['section_hint']}")
                    
                    result_columns.extend(new_columns)
                else:
                    # Re-split failed, keep original
                    if _SEG_DEBUG:
                        print(f"[resplit] Re-split failed, keeping original columns for page {page_no}")
                    result_columns.extend(page_cols)
            
            except Exception as e:
                if _SEG_DEBUG:
                    print(f"[resplit] Error during column re-splitting: {e}")
                # Keep original columns on error
                result_columns.extend(page_cols)
        else:
            # No multi-section header, keep original columns
            result_columns.extend(page_cols)
    
    return result_columns


def segment_sections_from_columns(columns_with_lines: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Segment columns-with-lines into sections. Two-pass approach:
    1) Pre-process: Detect multi-section headers and re-split columns if needed
    2) Collect all heading candidates (with stylized matching) and filter outliers using metrics.
    3) Iterate in reading order creating sections at accepted headings; collect probable unknown headings.
    Returns a full JSON containing sections with full line documents. Also prints a simplified JSON.
    """
    if not columns_with_lines:
        result = {"meta": {"pages": 0, "columns": 0, "sections": 0}, "sections": []}
        print(json.dumps([{"section": "Unknown", "lines": []}], ensure_ascii=False, indent=2))
        return result

    # PRE-PROCESS: Re-split columns if multi-section headers detected
    columns_with_lines = _resplit_columns_for_multi_sections(columns_with_lines)

    # First pass: candidates
    cands = _collect_candidates(columns_with_lines)
    cands = _filter_candidates(cands)
    if _SEG_DEBUG:
        print(f"[segment] accepted positions building from {len(cands)} candidates")
    accepted_positions: Dict[Tuple[Tuple[int, int, int], str]] = {}
    for _, c in cands:
        key = (c['page'], c['column_index'], c['line_index'])
        accepted_positions[key] = c['canon']

    # Precompute per-column stats
    col_stats_map: Dict[Tuple[int, int], Dict[str, float]] = {}
    for col in columns_with_lines:
        page_no = int(col.get('page', 0))
        col_idx = int(col.get('column_index', 0))
        lines = col.get('lines', [])
        fonts = [_metric_font_size(l.get('metrics', {})) for l in lines]
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
                continue            # Heuristic unknown heading -> try multi-section detection first, then embedding classification
            if _is_unknown_heading(line, stats):
                raw_text = line.get('text', '') or ''
                  # First, check if this is a multi-section header (e.g., "EXPERIENCE SKILLS")
                multi_sections_detected = False
                if _SECTION_SPLITTER_AVAILABLE:
                    try:
                        splitter = get_section_splitter()
                        multi_sections = splitter.detect_multi_section_header(raw_text)
                        
                        if len(multi_sections) >= 2:
                            # Found multiple sections in one line!
                            if _SEG_DEBUG:
                                section_names = [s[0] for s in multi_sections]
                                print(f"[segment] multi-section header detected: '{raw_text}' -> {section_names}")
                            
                            # AUTO-LEARN: Add detected sections to learner database
                            if _SECTION_LEARNER_AVAILABLE:
                                try:
                                    learner = _get_section_learner()
                                    if learner:
                                        for section_name in [s[0] for s in multi_sections]:
                                            # Try to learn this as a variant
                                            learned = learner.add_variant(section_name, raw_text.strip(), auto_learn=True)
                                            if learned and _SEG_DEBUG:
                                                print(f"[segment] Auto-learned: '{raw_text}' -> {section_name}")
                                except Exception as e:
                                    if _SEG_DEBUG:
                                        print(f"[segment] Auto-learning failed: {e}")
                            
                            # Record in unknown headings with special marker
                            unknown_headings.append({
                                "page": page_no,
                                "column_index": col_idx,
                                "line_index": int(line.get('line_index', li)),
                                "text": f"[MULTI-SECTION: {', '.join([s[0] for s in multi_sections])}] {raw_text}",
                                "boundaries": dict(line.get('boundaries', {})),
                                "properties": dict(line.get('properties', {})),
                                "metrics": dict(line.get('metrics', {})),
                                "multi_sections": [s[0] for s in multi_sections]
                            })
                            multi_sections_detected = True
                            continue
                    except Exception as e:
                        if _SEG_DEBUG:
                            print(f"[segment] multi-section detection failed: {e}")
                
                # If not a multi-section header, try embedding classification
                if not multi_sections_detected:
                    predicted, score = (None, 0.0)
                    if _embeddings_allowed():
                        if _SEG_DEBUG:
                            print(f"[segment] classifying unknown heading via embeddings: '{raw_text}'")
                        predicted, score = classify_header_embedding(clean_for_heading(raw_text))
                    else:
                        if _SEG_DEBUG:
                            print(f"[segment] embeddings disabled; recording unknown heading: '{raw_text}'")

                    if predicted:
                        # persist learned variant for future exact match
                        try:
                            attrs = {
                                "score": score,
                                "uppercase_ratio": uppercase_ratio(raw_text),
                                "metrics": dict(line.get('metrics', {})),
                            }
                            _persist_learned_variant(predicted, raw_text.strip(), attrs)
                        except Exception:
                            pass
                        # start a new section and skip adding heading line itself
                        if current_section["lines"]:
                            sections.append(current_section)
                        current_section = {"section": predicted, "lines": []}
                        continue
                    else:
                        # record as unknown, skip adding as content
                        unknown_headings.append({
                            "page": page_no,
                            "column_index": col_idx,
                            "line_index": int(line.get('line_index', li)),
                            "text": raw_text,
                            "boundaries": dict(line.get('boundaries', {})),
                            "properties": dict(line.get('properties', {})),
                            "metrics": dict(line.get('metrics', {})),
                        })
                        continue

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

    if _SEG_DEBUG:
        print(f"[segment] sections merged: {len(merged)}, unknown headings: {len(unknown_headings)}")

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
    # printable = [
    #     {
    #         "section": sec["section"],
    #         "lines": [ln.get("text", "") for ln in sec["lines"]]
    #     }
    #     for sec in merged
    # ]
    # print(json.dumps(printable, ensure_ascii=False, indent=2))

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


# ---------------- Embedding-based classifier (tiny model, optional) ----------------
_EMBEDDER = None
_ST_UTIL = None
_SECTION_EMB = None  # type: ignore
_LEARNED_CACHE: set = set()


def _get_embedder():
    global _EMBEDDER, _ST_UTIL
    if _EMBEDDER is not None:
        return _EMBEDDER
    try:
        from sentence_transformers import SentenceTransformer, util  # type: ignore
        _EMBEDDER = SentenceTransformer("all-MiniLM-L6-v2")
        _ST_UTIL = util
    except Exception:
        _EMBEDDER = None
        _ST_UTIL = None
    return _EMBEDDER


def _build_section_embeddings():
    global _SECTION_EMB
    if _SECTION_EMB is not None:
        return _SECTION_EMB
    embedder = _get_embedder()
    _SECTION_EMB = {}
    if embedder is None:
        return _SECTION_EMB
    texts = []
    keys = []
    for canon, variants in SECTIONS.items():
        # Use canonical + variants as training text
        corpus = " ".join([canon] + list(dict.fromkeys([v for v in variants if v]))).lower()
        texts.append(corpus)
        keys.append(canon)
    mat = embedder.encode(texts, normalize_embeddings=True)
    for i, canon in enumerate(keys):
        _SECTION_EMB[canon] = mat[i]
    return _SECTION_EMB


def classify_header_embedding(header_text: str, threshold: float = 0.68) -> Tuple[Optional[str], float]:
    # Respect env flag to avoid slow model downloads by default
    if not _embeddings_allowed():
        return None, 0.0
    header = (header_text or "").strip()
    if not header:
        return None, 0.0
    embedder = _get_embedder()
    if embedder is None or _ST_UTIL is None:
        return None, 0.0
    section_emb = _build_section_embeddings()
    if not section_emb:
        return None, 0.0
    vec = embedder.encode([header.lower()], normalize_embeddings=True)
    best = None
    best_score = -1.0
    for canon, emb in section_emb.items():
        score = float(_ST_UTIL.cos_sim(vec, emb)[0][0])  # type: ignore
        if score > best_score:
            best_score = score
            best = canon
    if best is not None and best_score >= threshold:
        return best, float(best_score)
    return None, float(best_score)


def _persist_learned_variant(canon: str, header_text: str, attrs: Dict[str, Any]) -> None:
    key = f"{canon}|{header_text.strip().lower()}"
    if key in _LEARNED_CACHE:
        return
    _LEARNED_CACHE.add(key)
    payload = {
        "canonical": canon,
        "header": header_text,
        "attributes": attrs,
    }
    for p in _LEARNED_FILE_CANDIDATES:
        try:
            # Prefer jsonl
            if p.suffix.lower() == ".jsonl" or p.name.endswith(".jsonl"):
                with p.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(payload, ensure_ascii=False) + "\n")
                return
        except Exception:
            continue
    # Fallback: write to first candidate as jsonl
    p = _LEARNED_FILE_CANDIDATES[0]
    try:
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


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
