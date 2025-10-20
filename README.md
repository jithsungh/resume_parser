# Resume Parser - Intelligent Multi-Strategy Pipeline

A production-ready, intelligent resume parsing system that handles PDF, DOCX, and scanned documents with automatic strategy selection and self-learning capabilities.

## 🚀 Features

- **Multi-Format Support**: PDF, DOCX, DOC, and scanned documents
- **Intelligent Strategy Selection**: Automatically chooses the best parsing approach
- **Self-Learning**: Improves section detection from parsed resumes
- **Batch Processing**: Process entire folders in parallel with progress tracking
- **Quality Validation**: Automatic quality scoring and validation
- **Excel Export**: Export parsed sections to Excel with clean formatting
- **Web Viewer**: View and validate parsing results in browser

## 📋 Requirements

```bash
pip install -r requirements.txt
```

### Key Dependencies

- **PDF Processing**: `pdfplumber`, `pymupdf`
- **OCR**: `easyocr` (for scanned documents)
- **DOCX Processing**: `python-docx`
- **ML Models**: `sentence-transformers`, `spacy`
- **Export**: `openpyxl` (Excel), `pandas`

## 🎯 Quick Start

### 1. Parse a Single Resume

```python
from src.core.unified_pipeline import UnifiedPipeline

pipeline = UnifiedPipeline()
result = pipeline.parse("resume.pdf", verbose=True)

print(f"Success: {result['success']}")
print(f"Strategy: {result['metadata']['strategy']}")
print(f"Sections found: {len(result['result']['sections'])}")
```

### 2. Batch Process a Folder

```bash
python batch_folder_process.py --folder "resumes/" --output "results.xlsx"
```

### 3. Test the Pipeline

```bash
python test_pipeline.py
```

### 4. View Results in Browser

```bash
python view_results.py
# Open browser to http://localhost:5000
```

## 📁 Project Structure

```
resume_parser/
├── README.md                      # This file
├── requirements.txt               # Python dependencies
├── config/
│   └── sections_database.json    # Section learning database
│
├── scripts/                       # Utility scripts
│   ├── batch_folder_process.py   # Batch process resumes → Excel
│   ├── test_pipeline.py          # Test & verify pipeline
│   └── view_results.py           # Web viewer for results
│
├── src/                           # Core source code
│   ├── core/                      # Main pipeline components
│   │   ├── unified_pipeline.py   # Main entry point (USE THIS!)
│   │   ├── parser.py             # Legacy parser (deprecated)
│   │   ├── batch_processor.py   # Batch processing logic
│   │   └── section_learner.py   # Self-learning system
│   │
│   ├── app/                       # Application layer
│   │   ├── file_detector.py     # File type detection
│   │   ├── layout_analyzer.py   # Layout analysis
│   │   ├── strategy_selector.py # Strategy selection logic
│   │   └── quality_validator.py # Quality scoring
│   │
│   ├── PDF_pipeline/             # PDF extraction strategies
│   │   ├── pipeline.py           # Standard PDF parsing
│   │   ├── get_words.py          # Text extraction
│   │   ├── get_lines.py          # Line detection
│   │   ├── segment_sections.py  # Section segmentation
│   │   ├── region_detector.py   # Multi-region layout
│   │   └── histogram_column_detector.py  # Column detection
│   │
│   ├── DOCX_pipeline/            # DOCX extraction
│   │   └── pipeline.py           # DOCX parsing
│   │
│   ├── IMG_pipeline/             # OCR for scanned docs
│   │   └── pipeline.py           # EasyOCR-based parsing
│   │
│   └── ROBUST_pipeline/          # Advanced layout-aware parsing
│       ├── README.md             # Detailed documentation
│       ├── pipeline.py           # Main robust pipeline
│       ├── pipeline_ocr.py       # OCR variant
│       └── adaptive_thresholds.py # Dynamic threshold tuning
│
├── outputs/                       # Generated Excel files
├── freshteams_resume/            # Sample resumes (for testing)
└── index.html                    # Web viewer frontend

```

## 🔧 Architecture

### Pipeline Flow

```
1. File Input (PDF/DOCX/Image)
          ↓
2. File Detection & Validation
          ↓
3. Layout Analysis
   - Scanned vs. digital
   - Column structure
   - Complexity score
          ↓
4. Strategy Selection
   - PDF_NATIVE: Fast text extraction
   - PDF_HISTOGRAM: Column-aware parsing
   - PDF_REGION: Complex multi-region layouts
   - OCR: Scanned documents
   - DOCX_NATIVE: Word documents
          ↓
5. Extraction & Parsing
          ↓
6. Quality Validation
   - Section coverage
   - Text quality
   - Completeness
          ↓
7. Section Learning (Optional)
   - Learn new patterns
   - Update database
          ↓
8. Output (JSON/Excel)
```

### Key Components

#### **UnifiedPipeline** (Main Entry Point)

- Orchestrates all parsing strategies
- Handles automatic fallback
- Manages learning and caching

#### **Strategy Selector**

- Analyzes document characteristics
- Chooses optimal parsing strategy
- Handles edge cases

#### **Section Learner**

- Self-improving system
- Learns section patterns from parsed resumes
- Adapts to new resume formats

#### **Quality Validator**

- Validates extraction quality
- Triggers fallback if needed
- Provides quality scores

## 📊 Supported Resume Sections

- Contact Information
- Summary / Objective
- Skills (Technical, Soft, Languages)
- Experience / Work History
- Projects
- Education
- Certifications
- Achievements / Awards
- Publications
- Research
- Volunteer Work
- Hobbies / Interests
- References
- Declarations

## 🎨 Usage Examples

### Example 1: Single Resume with Custom Config

```python
from src.core.unified_pipeline import UnifiedPipeline

pipeline = UnifiedPipeline(
    config_path="config/sections_database.json",
    enable_learning=True,
    verbose=True
)

result = pipeline.parse("resume.pdf")

# Access parsed data
sections = result['result']['sections']
for section in sections:
    print(f"\n{section['section']}:")
    for line in section['lines']:
        print(f"  {line}")
```

### Example 2: Batch Processing with Custom Options

```bash
# Process folder with 8 parallel workers
python batch_folder_process.py \
    --folder "resumes/" \
    --output "batch_results.xlsx" \
    --workers 8

# Process without recursive search
python batch_folder_process.py \
    --folder "resumes/" \
    --output "results.xlsx" \
    --no-recursive

# Quiet mode (no progress)
python batch_folder_process.py \
    --folder "resumes/" \
    --output "results.xlsx" \
    --quiet
```

### Example 3: Programmatic Batch Processing

```python
from src.core.batch_processor import BatchProcessor

processor = BatchProcessor(
    output_dir="outputs/",
    max_workers=4,
    enable_learning=True
)

results = processor.process_folder(
    folder_path="resumes/",
    recursive=True
)

# Export to Excel
processor.export_to_excel(
    results=results,
    output_path="batch_output.xlsx"
)
```

## 🧪 Testing

```bash
# Run full test suite
python test_pipeline.py

# Test specific file
python -c "
from src.core.unified_pipeline import UnifiedPipeline
pipeline = UnifiedPipeline()
result = pipeline.parse('test_resume.pdf', verbose=True)
print(result)
"
```

## 🐛 Troubleshooting

### Issue: Poor OCR Quality

**Solution**: Increase DPI for better text extraction

```python
result = pipeline.parse("resume.pdf", force_ocr=True, ocr_dpi=400)
```

### Issue: Missed Sections

**Solution**: Enable learning mode to improve detection

```python
pipeline = UnifiedPipeline(enable_learning=True)
```

### Issue: Slow Processing

**Solution**: Reduce parallel workers or disable OCR fallback

```bash
python batch_folder_process.py --folder "resumes/" --workers 2
```

## 📈 Performance

- **Digital PDFs**: ~0.5-2 seconds per page
- **DOCX Files**: ~0.3-1 second per file
- **Scanned PDFs**: ~3-8 seconds per page (OCR)
- **Batch Processing**: ~2-5 files/second (with 4 workers)

## 🤝 Contributing

1. Follow existing code structure
2. Add tests for new features
3. Update documentation
4. Use type hints
5. Keep functions modular and single-purpose

## 📝 License

Proprietary - Internal Use Only

## 🔄 Changelog

### v3.0 (Current)

- Unified pipeline architecture
- Self-learning section detection
- Advanced quality validation
- Web-based result viewer

### v2.0

- Multi-strategy support
- Batch processing
- Excel export

### v1.0

- Initial PDF parsing
- Basic section detection
