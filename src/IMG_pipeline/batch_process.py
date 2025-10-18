import os
import re
import json
import io
from contextlib import redirect_stdout
from typing import List, Dict, Any

from openpyxl import Workbook

from src.IMG_pipeline.pipeline import run_pipeline_ocr
from src.PDF_pipeline.segment_sections import SECTIONS

ILLEGAL_CHARACTERS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


def sanitize_cell(value: str) -> str:
    if value is None:
        return ""
    s = str(value)
    s = ILLEGAL_CHARACTERS_RE.sub("", s)
    return s.strip()


def find_pdfs(directory: str, max_files: int = 100, recursive: bool = True) -> List[str]:
    pdfs: List[str] = []
    if recursive:
        for root, _, files in os.walk(directory):
            for f in files:
                if f.lower().endswith(".pdf"):
                    pdfs.append(os.path.join(root, f))
    else:
        for f in os.listdir(directory):
            if f.lower().endswith(".pdf"):
                pdfs.append(os.path.join(directory, f))
    pdfs.sort()
    return pdfs[:max_files]


def result_section_text(result: Dict[str, Any], canonical: str) -> str:
    sections = result.get("sections", []) or []
    for sec in sections:
        if (sec.get("section") or "").strip().lower() == canonical.strip().lower():
            lines = [ln.get("text", "") for ln in sec.get("lines", [])]
            return "\n".join(filter(None, lines))
    return ""


def process_directory_to_excel(
    input_dir: str,
    output_xlsx: str = "batch_sections_ocr.xlsx",
    max_files: int = 100,
    recursive: bool = True,
    dpi: int = 300,
) -> str:
    pdf_paths = find_pdfs(input_dir, max_files=max_files, recursive=recursive)
    if not pdf_paths:
        print("No PDF files found.")
        return output_xlsx

    canonical_sections = list(SECTIONS.keys())
    EXTRA_UNKNOWN = "Unknown Sections"
    export_sections = canonical_sections + [EXTRA_UNKNOWN]

    wb = Workbook()
    ws = wb.active
    ws.title = "Sections (OCR)"

    headers = ["pdf_path", "contact_info"] + export_sections
    ws.append(headers)

    for i, pdf_path in enumerate(pdf_paths, start=1):
        print(f"[{i}/{len(pdf_paths)}] OCR Processing: {pdf_path}")
        try:
            with redirect_stdout(io.StringIO()):
                result, _ = run_pipeline_ocr(
                    pdf_path,
                    dpi=dpi,
                    min_words_per_column=10,
                    dynamic_min_words=True,
                    y_tolerance=0.5,
                    verbose=False,
                )

            contact = result.get("contact", {}) or {}
            contact_str = json.dumps(contact, ensure_ascii=False)

            row = [sanitize_cell(pdf_path), sanitize_cell(contact_str)]
            for canon in export_sections:
                content = result_section_text(result, canon)
                row.append(sanitize_cell(content))

            ws.append(row)
        except Exception as e:
            err_row = [sanitize_cell(pdf_path), sanitize_cell(f'{{"error": "{str(e)}"}}')]
            err_row.extend([""] * len(export_sections))
            ws.append(err_row)
            print(f"Error processing {pdf_path}: {e}")

    os.makedirs(os.path.dirname(output_xlsx) or ".", exist_ok=True)
    wb.save(output_xlsx)
    print(f"Wrote: {output_xlsx}")
    return output_xlsx


def main():
    INPUT_DIR = "freshteams_resume/"
    OUTPUT_XLSX = "outputs/batch_sections_ocr.xlsx"
    MAX_FILES = 300
    RECURSIVE = True

    process_directory_to_excel(
        INPUT_DIR,
        output_xlsx=OUTPUT_XLSX,
        max_files=MAX_FILES,
        recursive=RECURSIVE,
        dpi=300,
    )


if __name__ == "__main__":
    main()
