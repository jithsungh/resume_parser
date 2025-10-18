import os
import re
import json
import io
from contextlib import redirect_stdout
from typing import List, Dict, Any

from openpyxl import Workbook

from src.DOCX_pipeline.pipeline import run_pipeline
from src.PDF_pipeline.segment_sections import SECTIONS

# OpenPyXL-safe character filter
ILLEGAL_CHARACTERS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


def sanitize_cell(value: str) -> str:
    if value is None:
        return ""
    s = str(value)
    s = ILLEGAL_CHARACTERS_RE.sub("", s)
    return s.strip()


def find_docx(directory: str, max_files: int = 1000, recursive: bool = True) -> List[str]:
    """Collect .docx files under directory.
    Skips temporary files like '~$*.docx'.
    """
    docs: List[str] = []
    if recursive:
        for root, _, files in os.walk(directory):
            for f in files:
                fl = f.lower()
                if fl.endswith(".docx") and not fl.startswith("~$"):
                    docs.append(os.path.join(root, f))
    else:
        for f in os.listdir(directory):
            fl = f.lower()
            if fl.endswith(".docx") and not fl.startswith("~$"):
                docs.append(os.path.join(directory, f))
    docs.sort()
    return docs[:max_files]


def result_section_text(result: Dict[str, Any], canonical: str) -> str:
    sections = result.get("sections", []) or []
    for sec in sections:
        if (sec.get("section") or "").strip().lower() == canonical.strip().lower():
            lines = [ln.get("text", "") for ln in sec.get("lines", [])]
            return "\n".join(filter(None, lines))
    return ""


def process_directory_to_excel(
    input_dir: str,
    output_xlsx: str = "outputs/batch_sections_7.xlsx",
    max_files: int = 1000,
    recursive: bool = True,
) -> str:
    doc_paths = find_docx(input_dir, max_files=max_files, recursive=recursive)
    if not doc_paths:
        print("No DOCX files found.")
        return output_xlsx

    # Canonical section columns from SECTIONS dict keys (stable order)
    canonical_sections = list(SECTIONS.keys())
    EXTRA_UNKNOWN = "Unknown Sections"
    export_sections = canonical_sections + [EXTRA_UNKNOWN]

    # Prepare workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Sections"

    # Header matches PDF batch for viewer compatibility
    headers = ["pdf_path", "contact_info"] + export_sections
    ws.append(headers)

    for i, doc_path in enumerate(doc_paths, start=1):
        print(f"[{i}/{len(doc_paths)}] Processing: {doc_path}")
        try:
            # Suppress pipeline prints (it prints simplified JSON)
            with redirect_stdout(io.StringIO()):
                result, _ = run_pipeline(
                    doc_path,
                    verbose=False,
                )

            contact = result.get("contact", {}) or {}
            contact_str = json.dumps(contact, ensure_ascii=False)

            row = [sanitize_cell(doc_path), sanitize_cell(contact_str)]
            for canon in export_sections:
                content = result_section_text(result, canon)
                row.append(sanitize_cell(content))

            ws.append(row)
        except Exception as e:
            err_row = [sanitize_cell(doc_path), sanitize_cell(f'{{"error": "{str(e)}"}}')]
            err_row.extend([""] * len(export_sections))
            ws.append(err_row)
            print(f"Error processing {doc_path}: {e}")

    os.makedirs(os.path.dirname(output_xlsx) or ".", exist_ok=True)
    wb.save(output_xlsx)
    print(f"Wrote: {output_xlsx}")
    return output_xlsx


def main():
    # Static inputs: edit these paths/settings as needed
    INPUT_DIR = "freshteams_resume/"               # directory containing DOCX files
    OUTPUT_XLSX = "outputs/batch_sections_8.xlsx"  # aligns with viewer defaults
    MAX_FILES = 2000                                # max DOCX files to process
    RECURSIVE = True

    process_directory_to_excel(
        INPUT_DIR,
        output_xlsx=OUTPUT_XLSX,
        max_files=MAX_FILES,
        recursive=RECURSIVE,
    )


if __name__ == "__main__":
    main()
