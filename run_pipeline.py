import argparse
import json
import os
from typing import Tuple, Dict, Any

from src.PDF_pipeline.pipeline import run_pipeline as run_pdf_pipeline
from src.IMG_pipeline.pipeline import run_pipeline_ocr
from src.DOCX_pipeline.pipeline import run_pipeline as run_docx_pipeline


def run_any(path: str, prefer_ocr: bool = False, **kwargs) -> Tuple[Dict[str, Any], str, str]:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        res, sim = run_docx_pipeline(path, verbose=kwargs.get("verbose", True))
        return res, sim, "docx"

    if ext != ".pdf":
        raise ValueError(f"Unsupported file type: {ext}")

    def _empty(r: Dict[str, Any]) -> bool:
        meta = r.get("meta", {})
        return (meta.get("lines_total", 0) or 0) == 0 and len(r.get("sections", []) or []) == 0

    if prefer_ocr:
        res, sim = run_pipeline_ocr(path,
                                    dpi=kwargs.get("dpi", 300),
                                    min_words_per_column=kwargs.get("min_words_per_column", 10),
                                    dynamic_min_words=kwargs.get("dynamic_min_words", True),
                                    y_tolerance=kwargs.get("y_tolerance", 1.0),
                                    verbose=kwargs.get("verbose", True))
        if _empty(res):
            res, sim = run_pdf_pipeline(path,
                                        min_words_per_column=kwargs.get("min_words_per_column", 10),
                                        dynamic_min_words=kwargs.get("dynamic_min_words", True),
                                        y_tolerance=kwargs.get("y_tolerance", 1.0),
                                        verbose=kwargs.get("verbose", True))
            return res, sim, "pdf"
        return res, sim, "ocr"
    else:
        res, sim = run_pdf_pipeline(path,
                                    min_words_per_column=kwargs.get("min_words_per_column", 10),
                                    dynamic_min_words=kwargs.get("dynamic_min_words", True),
                                    y_tolerance=kwargs.get("y_tolerance", 1.0),
                                    verbose=kwargs.get("verbose", True))
        if _empty(res):
            res, sim = run_pipeline_ocr(path,
                                        dpi=kwargs.get("dpi", 300),
                                        min_words_per_column=kwargs.get("min_words_per_column", 10),
                                        dynamic_min_words=kwargs.get("dynamic_min_words", True),
                                        y_tolerance=kwargs.get("y_tolerance", 1.0),
                                        verbose=kwargs.get("verbose", True))
            return res, sim, "ocr"
        return res, sim, "pdf"


def main():
    p = argparse.ArgumentParser(description="Run resume parsing pipeline (auto PDF/DOCX with OCR fallback)")
    p.add_argument("path", help="Path to .pdf or .docx file")
    p.add_argument("--prefer-ocr", action="store_true", help="Try OCR before PDF text extraction")
    p.add_argument("--dpi", type=int, default=300)
    p.add_argument("--y-tol", type=float, default=1.0)
    p.add_argument("--min-words", type=int, default=10)
    p.add_argument("--no-dynamic-min", action="store_true")
    p.add_argument("--quiet", action="store_true")
    p.add_argument("--save-simple", help="Path to save simplified JSON output")
    args = p.parse_args()

    res, sim, used = run_any(
        args.path,
        prefer_ocr=args.prefer_ocr,
        dpi=args.dpi,
        min_words_per_column=args.min_words,
        dynamic_min_words=not args.no_dynamic_min,
        y_tolerance=args.y_tol,
        verbose=not args.quiet,
    )

    if not args.quiet:
        print(f"\nPipeline used: {used}")
        print("\nSimplified JSON:\n", sim)

    if args.save_simple:
        with open(args.save_simple, "w", encoding="utf-8") as f:
            f.write(sim)
        print(f"Saved simple JSON -> {args.save_simple}")


if __name__ == "__main__":
    main()
