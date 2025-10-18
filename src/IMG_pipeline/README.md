Image OCR Pipeline

Overview

- Converts each PDF page to an image (configurable DPI).
- Uses Tesseract OCR to extract word boxes.
- Reuses the PDF pipeline’s column detection, line grouping, and section segmentation.
- Outputs the same JSON structure as the PDF pipeline.

Usage

- Single file debug:
  python -m src.IMG_pipeline.pipeline freshteams_resume/SomeScan.pdf --dpi 300 --y_tol 0.5 --save_simple out.json

- Batch export to Excel:
  python -m src.IMG_pipeline.batch_process

Notes

- Install Tesseract OCR and ensure it’s on PATH (or set TESSERACT_CMD env var to the executable).
- You can adjust OCR language via get_words_ocr(lang="eng").
