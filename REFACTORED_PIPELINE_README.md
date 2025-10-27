# 🧠 Refactored Resume Parser - Architecture & Implementation

## 📋 Overview

This is a **complete refactor** of the resume parsing system following a robust, modular, and dynamic pipeline architecture.

## 🏗️ Architecture

The new pipeline consists of 7 well-defined steps:

```
┌─────────────────────────────────────────────────────────┐
│  1. Document Type Detection                             │
│     ├─ PDF or DOCX?                                     │
│     └─ Text-based or Scanned?                           │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  2. Word Extraction with Metadata                       │
│     ├─ Text: font, size, bold, color, bbox              │
│     ├─ Position: page, coordinates                      │
│     └─ Method: PyMuPDF (text) or EasyOCR (scanned)      │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  3. Layout Detection via Histograms                     │
│     ├─ Type 1: Single-column (1 peak)                   │
│     ├─ Type 2: Multi-column (valleys reach 0)           │
│     └─ Type 3: Hybrid/Complex (no deep valleys)         │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  4. Column Segmentation                                 │
│     ├─ Split words into columns                         │
│     ├─ Global column structure detection                │
│     └─ Handle overlaps and assign to nearest            │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  5. Line & Section Grouping                             │
│     ├─ Group words → lines (y-overlap)                  │
│     ├─ Detect section headers (heuristics + semantic)   │
│     └─ Define sections (header → next header)           │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  6. Unknown Section Detection                           │
│     ├─ Identify ambiguous sections                      │
│     ├─ Semantic similarity analysis                     │
│     └─ Suggest corrections                              │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  7. Output Generation                                   │
│     ├─ Structured JSON/Dict output                      │
│     ├─ Debug data (optional)                            │
│     └─ Comprehensive metadata                           │
└─────────────────────────────────────────────────────────┘
```

## 📦 Module Structure

```
src/core/
├── document_detector.py          # Step 1: Document type & scan detection
├── word_extractor.py             # Step 2: Word extraction with rich metadata
├── layout_detector_histogram.py  # Step 3: Histogram-based layout analysis
├── column_segmenter.py           # Step 4: Column splitting & assignment
├── line_section_grouper.py       # Step 5: Line grouping & section detection
├── unknown_section_detector.py   # Step 6: Unknown section identification
└── unified_resume_pipeline.py    # Step 7: Complete pipeline orchestration
```

## 🎯 Key Features

### ✅ Modular & Scalable

- Each step is an independent module
- Easy to test, debug, and extend
- Clear separation of concerns

### ✅ Adaptive to Layouts

- Handles single-column, multi-column, and hybrid layouts
- Dynamic threshold adjustment
- Global column structure detection across pages

### ✅ Rich Metadata

Every word includes:

- Font family, size, color
- Bold/italic attributes
- Bounding box coordinates
- Page number
- Confidence (for OCR)

### ✅ Robust Section Detection

- Heuristic-based (font, size, bold, uppercase)
- Semantic-based (sentence embeddings)
- Handles non-standard section names
- Detects unknown/ambiguous sections

### ✅ OCR Support

- Lazy loading (only when needed)
- EasyOCR integration for scanned documents
- Automatic selection based on document type

### ✅ No Data Loss

- Tracks all words through entire pipeline
- No lines/sections skipped
- Comprehensive error handling

## 🚀 Quick Start

### Installation

```bash
# Core dependencies
pip install PyMuPDF numpy sentence-transformers

# Optional: For OCR support
pip install easyocr

# Optional: For DOCX support
pip install python-docx
```

### Basic Usage

```python
from src.core.unified_resume_pipeline import UnifiedResumeParser

# Create parser
parser = UnifiedResumeParser(
    use_ocr_if_scanned=True,
    use_embeddings=True,
    verbose=True
)

# Parse resume
result = parser.parse("path/to/resume.pdf")

# Access results
print(f"Sections found: {len(result.sections)}")
for section in result.sections:
    print(f"- {section.section_name}: {len(section.content_lines)} lines")

# Save to JSON
with open("output.json", "w") as f:
    f.write(result.to_json(include_debug=True))
```

### Command Line

```bash
# Basic parsing
python -m src.core.unified_resume_pipeline resume.pdf

# Save to JSON
python -m src.core.unified_resume_pipeline resume.pdf --save-json

# Include debug data
python -m src.core.unified_resume_pipeline resume.pdf --save-json --debug

# Quiet mode
python -m src.core.unified_resume_pipeline resume.pdf --no-verbose
```

## 🔧 Configuration

### Parser Options

```python
parser = UnifiedResumeParser(
    # Use OCR for scanned documents
    use_ocr_if_scanned=True,

    # Use semantic embeddings for section matching
    use_embeddings=True,

    # Histogram analysis bin width (in points)
    histogram_bin_width=5,

    # Y-tolerance for line grouping (in points)
    y_tolerance=2.0,

    # Column overlap threshold (0.0 - 1.0)
    column_overlap_threshold=0.5,

    # Save intermediate debug data
    save_debug=False,

    # Print verbose progress
    verbose=False
)
```

## 📊 Output Format

```json
{
  "file_name": "resume.pdf",
  "document_type": {
    "file_type": "pdf",
    "is_scanned": false,
    "recommended_extraction": "text",
    "confidence": 0.95
  },
  "statistics": {
    "total_words": 542,
    "total_pages": 2,
    "total_columns": 4,
    "total_lines": 78,
    "total_sections": 6
  },
  "layouts": [
    {
      "page": 0,
      "type": "multi-column",
      "num_columns": 2,
      "confidence": 0.85
    }
  ],
  "sections": [
    {
      "section_name": "Experience",
      "page": 0,
      "column_id": 0,
      "line_count": 25,
      "content": "...",
      "full_text": "..."
    }
  ],
  "unknown_sections": [],
  "metadata": {
    "processing_time": 2.34,
    "pipeline_version": "2.0.0",
    "success": true
  }
}
```

## 🧪 Testing Individual Modules

Each module can be tested independently:

```bash
# Test document detection
python -m src.core.document_detector resume.pdf

# Test word extraction
python -m src.core.word_extractor resume.pdf

# Test layout detection
python -m src.core.layout_detector_histogram resume.pdf

# Test column segmentation
python -m src.core.column_segmenter resume.pdf

# Test line & section grouping
python -m src.core.line_section_grouper resume.pdf

# Test unknown section detection
python -m src.core.unknown_section_detector resume.pdf
```

## 📈 Performance

- **Single-column PDFs**: ~1-2 seconds
- **Multi-column PDFs**: ~2-4 seconds
- **Scanned PDFs (OCR)**: ~10-30 seconds (GPU can speed up)

## 🔍 Debugging

Enable debug mode to save intermediate results:

```python
parser = UnifiedResumeParser(save_debug=True, verbose=True)
result = parser.parse("resume.pdf")

# Access debug data
print(result.debug_data['word_extraction'])
print(result.debug_data['layouts'])
print(result.debug_data['columns'])
```

## 🎨 Customization

### Adding Custom Section Patterns

Edit `src/core/line_section_grouper.py`:

```python
KNOWN_SECTIONS = [
    # ... existing sections ...
    "custom section name",
    "another custom section"
]
```

### Adjusting Layout Detection

Tune histogram parameters in initialization:

```python
layout_detector = LayoutDetector(
    bin_width=10,           # Larger bins = less sensitive
    min_peak_height=5,      # Higher = fewer peaks detected
    valley_threshold=0.2    # Higher = require deeper valleys
)
```

### Fine-tuning Line Grouping

Adjust y-tolerance based on document characteristics:

```python
line_grouper = LineGrouper(
    y_tolerance=1.0   # Tighter grouping
    # or
    y_tolerance=3.0   # Looser grouping
)
```

## 🐛 Known Limitations

1. **DOCX positioning**: DOCX doesn't have precise positioning info, so coordinates are estimated
2. **Complex tables**: Table detection is not yet implemented
3. **Rotated text**: Currently doesn't handle rotated text
4. **Handwritten text**: OCR may struggle with handwriting

## 🚧 Future Enhancements

- [ ] Table detection and extraction
- [ ] Image/logo detection and extraction
- [ ] Multi-language support (beyond English)
- [ ] GPU acceleration for OCR
- [ ] Parallel processing for batch operations
- [ ] Web API endpoint integration
- [ ] Resume classification (by role/industry)

## 📝 Migration from Old Pipeline

The new pipeline can coexist with the old one. To migrate:

1. Replace imports:

   ```python
   # Old
   from src.smart_parser import smart_parse_resume

   # New
   from src.core.unified_resume_pipeline import UnifiedResumeParser
   parser = UnifiedResumeParser()
   result = parser.parse(file_path)
   ```

2. Update result access:

   ```python
   # Old
   sections = result['sections']

   # New
   sections = result.sections
   ```

## 📞 Support

For questions or issues with the refactored pipeline:

- Check module docstrings for detailed documentation
- Run individual modules with `--help`
- Enable `verbose=True` for debugging output

---

**Version**: 2.0.0  
**Last Updated**: 2025-10-27
