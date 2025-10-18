import json
from typing import Dict, Any, Tuple

from src.IMG_pipeline.get_words_ocr import get_words_from_pdf_ocr
from src.PDF_pipeline.split_columns import split_columns
from src.PDF_pipeline.get_lines import get_column_wise_lines
from src.PDF_pipeline.segment_sections import (
    segment_sections_from_columns,
    simple_json,
)
from src.PDF_pipeline.pipeline import extract_contact_info_from_lines


def run_pipeline_ocr(
    pdf_path: str,
    *,
    dpi: int = 300,
    min_words_per_column: int = 10,
    dynamic_min_words: bool = True,
    y_tolerance: float = 1.0,
    verbose: bool = True,
    tesseract_cmd: str | None = None,
) -> Tuple[Dict[str, Any], str]:
    """
    Image-based pipeline using OCR for image or scanned PDFs.
    Steps: PDF -> raster images -> OCR words -> columns -> lines -> sections -> contact -> simple_json
    """
    if verbose:
        print(f"PDF (OCR): {pdf_path}")

    pages = get_words_from_pdf_ocr(pdf_path, dpi=dpi, tesseract_cmd=tesseract_cmd)
    if not pages:
        if verbose:
            print("No pages extracted (OCR).")
        empty = {"meta": {"pages": 0, "columns": 0, "sections": 0, "lines_total": 0}, "sections": [], "contact": {}}
        sim = simple_json(empty)
        print(sim)
        return empty, sim

    if verbose:
        total_words = sum(len(p.get("words", [])) for p in pages)
        print(f"Pages: {len(pages)} | OCR words: {total_words}")

    columns = split_columns(
        pages,
        min_words_per_column=min_words_per_column,
        dynamic_min_words=dynamic_min_words,
    )
    if verbose:
        print(f"Columns: {len(columns)}")

    columns_with_lines = get_column_wise_lines(columns, y_tolerance=y_tolerance)
    if verbose:
        line_count = sum(len(c.get("lines", [])) for c in columns_with_lines)
        print(f"Total lines: {line_count}")

    result = segment_sections_from_columns(columns_with_lines)

    contact = extract_contact_info_from_lines(columns_with_lines)
    result["contact"] = contact

    sim = simple_json(result)
    print(sim)

    return result, sim


# --- Debugging / quick test ---
if __name__ == "__main__":
    print("HI")
    import argparse
    print("Hello world")
    parser = argparse.ArgumentParser(description="Run OCR resume parsing pipeline on a single PDF")
    parser.add_argument("--pdf", help="Path to PDF")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--y_tol", type=float, default=1.0)
    parser.add_argument("--min_words", type=int, default=10)
    parser.add_argument("--no_dynamic_min", action="store_true", help="Disable dynamic min-words per column")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--save_simple", help="Optional path to write simplified JSON")
    parser.add_argument("--tesseract_cmd", help="Path to tesseract executable (if not on PATH)")
    args = parser.parse_args()

    print(f"Running OCR pipeline on: {args.pdf}")

    res, sim = run_pipeline_ocr(
        args.pdf,
        dpi=args.dpi,
        min_words_per_column=args.min_words,
        dynamic_min_words=not args.no_dynamic_min,
        y_tolerance=args.y_tol,
        verbose=not args.quiet,
        tesseract_cmd=args.tesseract_cmd,
    )

    if args.save_simple:
        with open(args.save_simple, "w", encoding="utf-8") as f:
            f.write(sim)
        print(f"Saved simple JSON -> {args.save_simple}")
