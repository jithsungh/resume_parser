from typing import Dict, Any, Tuple
import json
import re

from src.DOCX_pipeline.get_lines_from_docx import get_single_column_from_docx
from src.PDF_pipeline.segment_sections import (
    segment_sections_from_columns,
    simple_json,
    pretty_print_segmented_sections,
)

# Reuse the same contact regexes from PDF pipeline for consistency
EMAIL_RE = re.compile(r'[\w\.-]+@[\w\.-]+\.\w{2,}', re.IGNORECASE)
PHONE_RE = re.compile(r'(?:\+|00)?\d{1,3}[\s\-\.]?(?:\(?\d{2,5}\)?[\s\-\.]?)?\d{3,5}[\s\-\.]?\d{3,5}', re.IGNORECASE)
LINKEDIN_RE = re.compile(r'(?:https?://)?(?:www\.)?linkedin\.com/[^\s,;]+', re.IGNORECASE)
GITHUB_RE = re.compile(r'(?:https?://)?(?:www\.)?github\.com/[^\s,;]+', re.IGNORECASE)
LOCATION_CANDIDATE_RE = re.compile(r"\b([A-Z][A-Za-z .\-]+,\s*[A-Z][A-Za-z .\-]+(?:,\s*[A-Z][A-Za-z .\-]+)?)\b(?:\s*\d{5}(?:-\d{4})?|\s*\d{6})?", re.IGNORECASE)
NAME_LINE_RE = re.compile(r"^[A-Z][a-zA-Z'\-]+(?: [A-Z][a-zA-Z'\-]+){0,3}$")

# Optional spaCy
try:
    import spacy  # type: ignore
    _NLP = None
except Exception:  # pragma: no cover
    spacy = None  # type: ignore
    _NLP = None  # type: ignore


def _get_spacy_model():
    global _NLP
    if _NLP is not None:
        return _NLP
    if spacy is None:
        return None
    try:
        for name in ("en_core_web_sm", "en_core_web_md", "en_core_web_lg"):
            try:
                _NLP = spacy.load(name)  # type: ignore
                return _NLP
            except Exception:
                continue
        _NLP = spacy.blank("en")  # type: ignore
        return _NLP
    except Exception:
        return None


def _infer_name_from_email(email: str):
    if not email:
        return None
    try:
        local = email.split("@", 1)[0]
        local = re.sub(r"\d+", " ", local)
        parts = re.split(r"[._\-+ ]+", local)
        parts = [p for p in parts if p and p.lower() not in ("mail", "email", "gmail", "yahoo", "outlook", "hotmail")]
        if not parts:
            return None
        cand = " ".join(parts[:3]).strip()
        cand = " ".join(w.capitalize() for w in cand.split())
        if 2 <= len(cand) <= 50:
            return cand
    except Exception:
        pass
    return None


def _spacy_name_location(text: str):
    nlp = _get_spacy_model()
    if nlp is None:
        return None, None
    try:
        doc = nlp(text)
        name = None
        location = None
        for ent in doc.ents:
            if ent.label_ == "PERSON" and not name:
                t = ent.text.strip()
                if t and 2 <= len(t) <= 60 and "@" not in t and "http" not in t:
                    name = t
            if ent.label_ in ("GPE", "LOC") and not location:
                lt = ent.text.strip()
                if lt and 2 <= len(lt) <= 80:
                    location = lt
            if name and location:
                break
        return name, location
    except Exception:
        return None, None


def _collect_all_lines(columns_with_lines):
    lines = []
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
    lines.sort(key=lambda l: (l["page"], l.get("_top", 0)))
    return lines


def _extract_first_match(regex: re.Pattern, text: str):
    m = regex.search(text or "")
    return m.group(0) if m else None


def _normalize_phone(ph: str) -> str:
    if not ph:
        return ph
    s = ph.strip()
    s = re.sub(r'[^\d\+]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def extract_contact_info_from_lines(columns_with_lines):
    info: Dict[str, Any] = {}
    all_lines = _collect_all_lines(columns_with_lines)
    if not all_lines:
        return info

    first_page = min(l["page"] for l in all_lines)
    first_page_lines = [l for l in all_lines if l["page"] == first_page]
    first_page_lines.sort(key=lambda l: l.get("_top", 0))
    head_window = first_page_lines[:40]

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
            if ph and len(re.sub(r'\D', '', ph)) >= 8:
                info["phone"] = _normalize_phone(ph)
        if "location" not in info:
            loc = _extract_first_match(LOCATION_CANDIDATE_RE, txt)
            if loc and not any(k in txt.lower() for k in ("summary", "experience", "education", "skills", "projects")):
                info["location"] = loc.strip()

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

    # infer name from email (non-blocking)
    if "name" not in info and "email" in info:
        nm = _infer_name_from_email(info.get("email", ""))
        if nm:
            info["name"] = nm

    # spaCy NER on the head area to confirm/extract name and location
    head_text = "\n".join((ln.get("text") or "") for ln in head_window)
    sp_name, sp_loc = _spacy_name_location(head_text)
    if sp_name and "name" not in info:
        info["name"] = sp_name
    if sp_loc and "location" not in info:
        info["location"] = sp_loc

    return info


# -------------------- Pipeline --------------------

def run_pipeline(docx_path: str, *, verbose: bool = True) -> Tuple[Dict[str, Any], str]:
    """
    Run the DOCX resume parsing pipeline:
      DOCX -> lines (single column) -> section segmentation -> contact info -> simple_json.
    Returns (full_result_json, simplified_json_str). Prints simplified JSON fully.
    Output format matches src/PDF_pipeline/pipeline.run_pipeline output.
    
    Raises:
        RuntimeError: If python-docx is not installed
        FileNotFoundError: If DOCX file doesn't exist
        Exception: For other parsing errors
    """
    if verbose:
        print(f"DOCX: {docx_path}")
    
    # Validate file exists
    from pathlib import Path
    if not Path(docx_path).exists():
        raise FileNotFoundError(f"DOCX file not found: {docx_path}")
    
    # Validate file extension
    suffix = Path(docx_path).suffix.lower()
    if suffix not in ['.docx', '.doc']:
        raise ValueError(f"Invalid file type: {suffix}. Expected .docx or .doc")

    try:
        columns_with_lines = get_single_column_from_docx(docx_path)
    except RuntimeError as e:
        # Re-raise if python-docx is not installed
        raise
    except Exception as e:
        # Wrap other errors with context
        raise RuntimeError(f"Failed to extract lines from DOCX: {e}") from e
    
    if not columns_with_lines:
        raise ValueError("No content extracted from DOCX file")
    
    if verbose:
        line_count = sum(len(c.get("lines", [])) for c in columns_with_lines)
        print(f"Total lines: {line_count}")
        print("Starting section segmentation...")

    result = segment_sections_from_columns(columns_with_lines)
    
    if verbose:
        sec_cnt = len(result.get("sections", []) or [])
        lines_total = result.get("meta", {}).get("lines_total", 0)
        print(f"Segmentation done. Sections: {sec_cnt}, total lines in sections: {lines_total}")
        print("Extracting contact info...")
    
    contact = extract_contact_info_from_lines(columns_with_lines)
    result["contact"] = contact

    sim = simple_json(result)
    if verbose:
        print(sim)
    return result, sim


def main():
    DOCX_PATH = "freshteams_resume/Automation Testing/Manikanta_Testing_Resume.docx"
    VERBOSE = True

    result, sim = run_pipeline(DOCX_PATH, verbose=VERBOSE)

    if VERBOSE:
        print("\nPretty print (section-wise with page/column):")
        print(simple_json(result))

        print("\nDetected contact info:")
        print(json.dumps(result.get("contact", {}), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
