#!/usr/bin/env python3
"""
Web-based Resume Parser Results Viewer
=======================================

View parsed resume results in a browser with side-by-side comparison.

Usage:
    python scripts/view_results.py
    # Then open browser to http://localhost:5000
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import json
from pathlib import Path
from typing import List, Dict, Any

from flask import Flask, jsonify, send_file, abort, Response, request
from openpyxl import load_workbook

from src.PDF_pipeline.segment_sections import SECTIONS

# Config
# Default Excel file name as requested. Fallback to outputs/batch_sections.xlsx if missing.
DEFAULT_XLSX = "batch_selection_8.xlsx"
FALLBACK_XLSX = "outputs/batch_sections_8.xlsx"
ALSO_TRY_XLSX = "batch_sections_8.xlsx"  # batch writer default name

# Resolve project root (this file is in project root)
ROOT_DIR = Path(__file__).resolve().parent
INDEX_HTML = ROOT_DIR / "index.html"

def _windows_to_wsl_path(s: str) -> Path:
    """
    Convert Windows absolute path like C:\\Users\\... to WSL /mnt/c/Users/...
    If not a drive path, return as Path(s).
    """
    if not s:
        return Path("")
    # Drive letter pattern: X:\ or X:/
    if len(s) >= 3 and s[1] == ":" and (s[2] == "\\" or s[2] == "/") and s[0].isalpha():
        drive = s[0].lower()
        rest = s[2:].replace("\\", "/").lstrip("/")
        return Path(f"/mnt/{drive}/{rest}")
    return Path(s)

def _sanitize_path_str(raw: str) -> str:
    # Remove common prefixes like file://
    if not raw:
        return raw
    if raw.startswith("file://"):
        return raw.replace("file://", "", 1)
    return raw

def _search_workspace_for(name: str) -> Path | None:
    """Search the workspace for a file by exact filename, then by stem (preferring .pdf)."""
    try:
        # Exact filename match
        matches = list(ROOT_DIR.rglob(name))
        if matches:
            # Prefer PDFs then shorter paths
            matches.sort(key=lambda p: (p.suffix.lower() != ".pdf", len(str(p))))
            return matches[0]
        # By stem
        stem = Path(name).stem
        if not stem:
            return None
        stem_matches = [p for p in ROOT_DIR.rglob(f"{stem}.*")]
        if stem_matches:
            stem_matches.sort(key=lambda p: (p.suffix.lower() != ".pdf", len(str(p))))
            return stem_matches[0]
    except Exception:
        pass
    return None

def _load_rows_from_excel(xlsx_path: Path) -> List[Dict[str, Any]]:
    if not xlsx_path.exists():
        raise FileNotFoundError(f"Excel file not found: {xlsx_path}")

    wb = load_workbook(str(xlsx_path), read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    header = [str(h or "").strip() for h in rows[0]]
    data_rows = rows[1:]

    # Identify canonical section columns from header, falling back to SECTIONS keys
    canonical_list = list(SECTIONS.keys())
    cols = {name: idx for idx, name in enumerate(header)}

    required_cols = ["pdf_path", "contact_info"]
    for r in required_cols:
        if r not in cols:
            raise ValueError(f"Missing required column '{r}' in Excel header: {header}")

    # Any remaining columns treat as section columns; prefer known canonical order if present
    section_cols_in_sheet = [h for h in header if h not in required_cols]
    # Keep order by canonical_list
    ordered_sections = [s for s in canonical_list if s in section_cols_in_sheet]
    # Add any extra unknown columns at the end
    ordered_sections += [h for h in section_cols_in_sheet if h not in ordered_sections]

    items: List[Dict[str, Any]] = []
    for i, r in enumerate(data_rows):
        if r is None:
            continue
        pdf_path = (r[cols["pdf_path"]] or "").strip() if len(r) > cols["pdf_path"] else ""
        if not pdf_path:
            continue
        contact_raw = (r[cols["contact_info"]] or "") if len(r) > cols["contact_info"] else ""
        contact: Dict[str, Any] = {}
        if isinstance(contact_raw, str) and contact_raw.strip():
            try:
                contact = json.loads(contact_raw)
                if not isinstance(contact, dict):
                    contact = {"raw": contact_raw}
            except Exception:
                contact = {"raw": str(contact_raw)}
        elif isinstance(contact_raw, dict):
            contact = contact_raw

        sections: Dict[str, Any] = {}
        for sec in ordered_sections:
            idx = cols.get(sec)
            if idx is None or idx >= len(r):
                continue
            val = r[idx] or ""
            # Section lines were joined with '\n' in batch writer; split to list for UI
            if isinstance(val, str):
                lines = [ln.strip() for ln in val.split("\n") if str(ln).strip()]
            elif isinstance(val, (list, tuple)):
                lines = [str(v).strip() for v in val if str(v).strip()]
            else:
                lines = [str(val).strip()] if str(val).strip() else []
            if lines:
                sections[sec] = lines

        items.append({
            "index": i,
            "pdf_path": pdf_path,
            "contact": contact,
            "sections": sections,
        })
    return items

def _resolve_excel_path() -> Path:
    # Allow override via env
    env_val = os.getenv("BATCH_XLSX")
    if env_val:
        p = Path(env_val)
        if not p.is_absolute():
            p = ROOT_DIR / p
        if p.exists():
            return p

    candidates = [
        ROOT_DIR / DEFAULT_XLSX,
        ROOT_DIR / ALSO_TRY_XLSX,
        ROOT_DIR / FALLBACK_XLSX,
        ROOT_DIR / "outputs" / DEFAULT_XLSX,
    ]
    for p in candidates:
        if p.exists():
            return p

    # last resort: look in root for any xlsx containing 'batch' in name
    for cand in ROOT_DIR.glob("*.xlsx"):
        if "batch" in cand.name.lower():
            return cand
    raise FileNotFoundError(f"Could not find {DEFAULT_XLSX} or {ALSO_TRY_XLSX} or {FALLBACK_XLSX} in {ROOT_DIR}")

def _build_allowed_pdf_map(items: List[Dict[str, Any]]) -> Dict[int, Path]:
    """
    Map index -> absolute Path. Only serve files that appear in the Excel.
    Also translate Windows-style absolute paths to WSL if needed. Fall back to workspace search.
    """
    idx_to_path: Dict[int, Path] = {}
    for i, item in enumerate(items):
        raw = str(item.get("pdf_path", "") or "").strip()
        if not raw:
            continue
        raw = _sanitize_path_str(raw)
        p = Path(raw)

        # Prefer absolute resolution or relative to project
        if not p.is_absolute():
            p = (ROOT_DIR / raw).resolve()

        # If missing, try Windows->WSL translation
        if not p.exists():
            p2 = _windows_to_wsl_path(raw)
            if p2.exists():
                p = p2

        # If still missing, search workspace by filename/stem, prefer PDF
        if not p.exists():
            fallback = _search_workspace_for(Path(raw).name)
            if fallback and fallback.exists():
                p = fallback

        idx_to_path[i] = p

        # Optional: log missing for debugging
        if not p.exists():
            try:
                print(f"[warn] Missing file for row {i}: '{raw}' -> resolved '{p}'", flush=True)
            except Exception:
                pass
    return idx_to_path

def create_app() -> Flask:
    app = Flask(__name__)

    # Load data once at startup
    xlsx = _resolve_excel_path()
    items = _load_rows_from_excel(xlsx)
    path_map = _build_allowed_pdf_map(items)

    @app.get("/")
    def index() -> Response:
        if not INDEX_HTML.exists():
            return Response("index.html not found at project root.", status=404)
        return send_file(str(INDEX_HTML), mimetype="text/html; charset=utf-8")

    @app.get("/api/rows")
    def api_rows():
        # Filtering controlled via query params. Defaults to no filtering (all).
        # New param: experience={all|empty|nonempty}. Back-compat: experience_empty={0|1}
        q_mode = request.args.get("experience")
        q_legacy = request.args.get("experience_empty")

        def has_empty_experience(item: Dict[str, Any]) -> bool:
            secs = item.get("sections", {}) or {}
            # find the experience key case-insensitively
            exp_key = None
            for k in secs.keys():
                if str(k).strip().lower() == "experience":
                    exp_key = k
                    break
            exp_lines = secs.get(exp_key) if exp_key is not None else None
            # treat missing or empty list/string as empty
            if exp_lines is None:
                return True
            if isinstance(exp_lines, str):
                return len(exp_lines.strip()) == 0
            if isinstance(exp_lines, list):
                return len([ln for ln in exp_lines if str(ln).strip()]) == 0
            return False

        # Determine filter mode
        mode = "all"
        if q_mode:
            v = q_mode.strip().lower()
            if v in ("empty", "none"):
                mode = "empty"
            elif v in ("nonempty", "notnull", "not-null"):
                mode = "nonempty"
            else:
                mode = "all"
        elif q_legacy is not None:
            # legacy boolean flag
            mode = "empty" if q_legacy.strip().lower() in ("1", "true", "yes") else "all"

        payload = []
        for i, item in enumerate(items):
            empty = has_empty_experience(item)
            if mode == "empty" and not empty:
                continue
            if mode == "nonempty" and empty:
                continue
            payload.append({
                "i": i,
                "pdf_path": item["pdf_path"],
                "filename": Path(item["pdf_path"]).name,
                "contact": item.get("contact", {}),
                "sections": item.get("sections", {}),
            })
        return jsonify(payload)

    @app.get("/pdf/<int:i>")
    def serve_pdf_by_index(i: int):
        if i < 0 or i >= len(items):
            abort(404)
        p = path_map.get(i)
        if not p or not p.exists():
            abort(404)
        # Determine mimetype
        ext = p.suffix.lower()
        if ext == ".pdf":
            mimetype = "application/pdf"
        elif ext in (".png", ".jpg", ".jpeg"):
            mimetype = f"image/{'jpeg' if ext in ('.jpg', '.jpeg') else 'png'}"
        else:
            # default binary; iframe may not render but still allows download
            mimetype = "application/octet-stream"
        return send_file(str(p), mimetype=mimetype, conditional=True)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)

