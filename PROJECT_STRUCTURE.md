# Project Structure - Complete Overview

This document explains the organization and purpose of every directory and key file in the resume parser project.

## 📁 Directory Tree

```
resume_parser/
│
├── 📄 README.md                   # Main project documentation
├── 📄 requirements.txt            # Python dependencies
├── 📄 .gitignore                  # Git ignore rules
├── 📄 install_and_test.sh        # Quick setup script
│
├── 📁 config/                     # Configuration files
│   └── sections_database.json   # Learned section patterns (self-learning DB)
│
├── 📁 scripts/                    # 🎯 Command-line utilities (START HERE)
│   ├── README.md                 # Scripts documentation
│   ├── batch_folder_process.py  # ⭐ Batch process folders → Excel
│   ├── test_pipeline.py         # Test & verify pipeline
│   ├── view_results.py          # Web viewer for results
│   └── index.html               # Web viewer frontend
│
├── 📁 src/                        # 🔧 Core source code
│   ├── __init__.py
│   │
│   ├── 📁 core/                  # ⭐ Main pipeline (USE THIS)
│   │   ├── README.md
│   │   ├── unified_pipeline.py  # ⭐⭐ MAIN ENTRY POINT
│   │   ├── batch_processor.py   # Batch processing logic
│   │   ├── section_learner.py   # Self-learning system
│   │   └── parser.py            # 🔧 Legacy (deprecated)
│   │
│   ├── 📁 app/                   # Intelligence layer
│   │   ├── README.md
│   │   ├── file_detector.py     # Detect file types
│   │   ├── layout_analyzer.py   # Analyze document layout
│   │   ├── strategy_selector.py # Choose parsing strategy
│   │   └── quality_validator.py # Validate extraction quality
│   │
│   ├── 📁 PDF_pipeline/          # Digital PDF extraction
│   │   ├── README.md
│   │   ├── pipeline.py          # Main PDF parser
│   │   ├── get_words.py         # Extract words with coords
│   │   ├── get_words_pymupdf.py # Alternative extractor
│   │   ├── get_lines.py         # Group words into lines
│   │   ├── histogram_column_detector.py  # Detect columns
│   │   ├── region_detector.py   # Detect layout regions
│   │   ├── split_columns.py     # Split multi-column layouts
│   │   └── segment_sections.py  # Identify sections
│   │
│   ├── 📁 DOCX_pipeline/         # Word document extraction
│   │   ├── README.md
│   │   └── pipeline.py          # DOCX parser
│   │
│   ├── 📁 IMG_pipeline/          # OCR for scanned docs
│   │   ├── README.md
│   │   └── pipeline.py          # EasyOCR-based parser
│   │
│   └── 📁 ROBUST_pipeline/       # Advanced layout-aware parsing
│       ├── README.md            # Detailed documentation
│       ├── pipeline.py          # Main robust pipeline
│       ├── pipeline_ocr.py      # OCR variant
│       ├── adaptive_thresholds.py  # Dynamic tuning
│       ├── batch_process.py     # Batch processing
│       └── test_robust.py       # Testing script
│
├── 📁 outputs/                    # Generated Excel/JSON files
│   └── batch_sections_*.xlsx    # Batch processing results
│
├── 📁 freshteams_resume/         # Sample/test resumes
│   ├── Automation Testing/
│   ├── Backend Java Developer/
│   ├── DevOps/
│   ├── Golang Developer/
│   ├── ReactJs/
│   └── Resumes/
│
└── 📁 train_original.json        # Training data (if needed)
    validation_original.json      # Validation data
```

---

## 🎯 What Each Directory Is For

### `/` (Root)

**Purpose**: Project configuration and entry points

**Key Files**:

- `README.md` - Start here! Complete project documentation
- `requirements.txt` - Install dependencies: `pip install -r requirements.txt`
- `.gitignore` - What Git should ignore
- `install_and_test.sh` - Quick setup and test

---

### `/config/`

**Purpose**: Configuration and learned patterns

**Files**:

- `sections_database.json` - Self-learning database of section patterns
  - Contains learned section header variations
  - Updated automatically when learning is enabled
  - Can be manually edited to add custom sections

**When to modify**:

- Add organization-specific section names
- Customize section mappings
- Reset learning (delete and regenerate)

---

### `/scripts/` ⭐ **START HERE FOR CLI**

**Purpose**: Command-line tools for daily use

**Who uses it**: End users, recruiters, HR, automation scripts

**What's inside**:

- `batch_folder_process.py` - **Most used!** Process folders → Excel
- `test_pipeline.py` - Verify everything works
- `view_results.py` - Web interface to review results
- `index.html` - Web viewer frontend

**Typical workflow**:

```bash
# 1. Test
python scripts/test_pipeline.py

# 2. Batch process
python scripts/batch_folder_process.py --folder "resumes/" --output "results.xlsx"

# 3. View
python scripts/view_results.py
```

See [scripts/README.md](scripts/README.md) for detailed docs.

---

### `/src/core/` ⭐ **MAIN PIPELINE**

**Purpose**: Core orchestration and intelligence

**Who uses it**: Developers integrating resume parsing into applications

**Key Components**:

#### `unified_pipeline.py` ⭐⭐ **THE MAIN ENTRY POINT**

- **Use this for everything!**
- Orchestrates all parsing strategies
- Automatic file type detection
- Automatic strategy selection
- Quality validation
- Learning integration

#### `batch_processor.py`

- Parallel processing of multiple files
- Progress tracking
- Error handling
- Excel export

#### `section_learner.py`

- Self-improving section detection
- Learns from parsed resumes
- Updates database automatically

#### `parser.py` 🔧

- **Legacy code** - Use `unified_pipeline.py` instead
- Kept for backward compatibility

**Example**:

```python
from src.core.unified_pipeline import UnifiedPipeline

pipeline = UnifiedPipeline()
result = pipeline.parse("resume.pdf")
```

See [src/core/README.md](src/core/README.md) for detailed docs.

---

### `/src/app/`

**Purpose**: Intelligence layer - decision making

**Who uses it**: Automatically by unified_pipeline (you don't call directly)

**Components**:

- `file_detector.py` - Detects file type, validates, checks if scanned
- `layout_analyzer.py` - Analyzes columns, complexity, regions
- `strategy_selector.py` - Chooses best parsing strategy
- `quality_validator.py` - Validates results, triggers fallback

**How it works**:

```
unified_pipeline → file_detector → layout_analyzer → strategy_selector
    → [parse] → quality_validator → [fallback if needed]
```

See [src/app/README.md](src/app/README.md) for detailed docs.

---

### `/src/PDF_pipeline/`

**Purpose**: Extract text from digital (non-scanned) PDFs

**When used**: For PDFs with selectable text (most modern PDFs)

**Strategies**:

- **Simple**: Single-column layouts (fast)
- **Histogram**: Multi-column detection
- **Region**: Complex multi-region layouts

**Key Files**:

- `pipeline.py` - Main orchestrator
- `get_words.py` - Extract words with coordinates
- `get_lines.py` - Group words into lines
- `histogram_column_detector.py` - Detect columns automatically
- `region_detector.py` - Detect different layout regions
- `segment_sections.py` - Identify resume sections

**Performance**: 0.5-3 seconds per page

See [src/PDF_pipeline/README.md](src/PDF_pipeline/README.md) for detailed docs.

---

### `/src/DOCX_pipeline/`

**Purpose**: Extract from Word documents

**When used**: For .docx and .doc files

**Advantages**:

- Faster than PDF (no layout analysis)
- More accurate (uses document styles)
- Preserves formatting explicitly

**Performance**: 0.1-1 second per file

See [src/DOCX_pipeline/README.md](src/DOCX_pipeline/README.md) for detailed docs.

---

### `/src/IMG_pipeline/`

**Purpose**: OCR for scanned documents

**When used**:

- Scanned PDFs (no selectable text)
- Image files (.jpg, .png)
- Poor quality PDFs

**Technology**: EasyOCR (deep learning OCR)

**Performance**: 1-8 seconds per page (slower but necessary for scans)

**GPU acceleration**: 3-5x faster with GPU

See [src/IMG_pipeline/README.md](src/IMG_pipeline/README.md) for detailed docs.

---

### `/src/ROBUST_pipeline/`

**Purpose**: Advanced layout-aware parsing for complex documents

**When used**:

- Very complex multi-region layouts
- Hybrid layouts (1-col header + 2-col body)
- Creative/unusual resume designs
- When other pipelines fail

**Features**:

- Recursive layout analysis
- Adaptive thresholds
- Context-aware heading detection
- Handles nested structures

**Performance**: 2-5 seconds per page

**Use case**: Last resort for difficult documents

See [src/ROBUST_pipeline/README.md](src/ROBUST_pipeline/README.md) for detailed docs.

---

### `/outputs/`

**Purpose**: Storage for generated files

**What's stored**:

- Excel files from batch processing
- JSON exports
- Temporary processing results

**Ignored by Git**: Files here are not committed (see .gitignore)

---

### `/freshteams_resume/`

**Purpose**: Sample resumes for testing

**Structure**:

- Organized by role (Automation Testing, DevOps, etc.)
- Real-world examples with various formats
- Used by test_pipeline.py

**Note**: Ignored by Git (contains real resumes)

---

## 🔄 How Everything Works Together

### Single File Parsing Flow:

```
1. User calls: pipeline.parse("resume.pdf")
                     ↓
2. unified_pipeline.py (orchestrator)
                     ↓
3. file_detector.py (check file type, validate)
                     ↓
4. layout_analyzer.py (analyze structure)
                     ↓
5. strategy_selector.py (choose best strategy)
                     ↓
6. Execute strategy:
   ├─ PDF_pipeline (if digital PDF)
   ├─ DOCX_pipeline (if Word doc)
   ├─ IMG_pipeline (if scanned)
   └─ ROBUST_pipeline (if complex)
                     ↓
7. quality_validator.py (check quality)
                     ↓
8. If poor quality → Try fallback strategy (step 6)
                     ↓
9. section_learner.py (learn patterns - optional)
                     ↓
10. Return structured result
```

### Batch Processing Flow:

```
1. User runs: batch_folder_process.py
                     ↓
2. Find all PDFs/DOCX in folder
                     ↓
3. Create ThreadPoolExecutor with N workers
                     ↓
4. For each file (in parallel):
   - Call unified_pipeline.parse()
   - Track progress
   - Handle errors
                     ↓
5. Collect all results
                     ↓
6. Export to Excel (openpyxl)
   - One row per resume
   - One column per section
                     ↓
7. Save outputs/results.xlsx
```

---

## 🎨 Usage Patterns

### Pattern 1: Quick Single File (Developers)

```python
from src.core.unified_pipeline import UnifiedPipeline
pipeline = UnifiedPipeline()
result = pipeline.parse("resume.pdf")
```

### Pattern 2: Batch Processing (CLI - Most Common)

```bash
python scripts/batch_folder_process.py \
    --folder "resumes/" \
    --output "results.xlsx" \
    --workers 4
```

### Pattern 3: Batch Processing (Programmatic)

```python
from src.core.batch_processor import BatchProcessor
processor = BatchProcessor(max_workers=4)
results = processor.process_folder("resumes/")
processor.export_to_excel(results, "output.xlsx")
```

### Pattern 4: Custom Integration

```python
from src.core.unified_pipeline import UnifiedPipeline

pipeline = UnifiedPipeline(
    config_path="custom_config.json",
    enable_learning=True,
    verbose=False
)

for resume_file in my_files:
    result = pipeline.parse(resume_file)
    my_database.store(result)
```

---

## 🛠️ For Developers: Where to Make Changes

### Add new section type:

→ Edit `config/sections_database.json`

### Change parsing strategy logic:

→ Edit `src/app/strategy_selector.py`

### Improve section detection:

→ Edit `src/PDF_pipeline/segment_sections.py`

### Add new extraction method:

→ Create new pipeline in `src/NEW_pipeline/`

### Change quality thresholds:

→ Edit `src/app/quality_validator.py`

### Modify Excel export format:

→ Edit `scripts/batch_folder_process.py` → `save_to_excel()`

### Add preprocessing:

→ Edit specific pipeline's preprocessing step

---

## 📊 Performance Characteristics

| Component                | Speed              | When to Use                |
| ------------------------ | ------------------ | -------------------------- |
| PDF_pipeline (simple)    | ⚡⚡⚡ Fast (0.5s) | Single-column digital PDFs |
| PDF_pipeline (histogram) | ⚡⚡ Medium (1-2s) | Multi-column digital PDFs  |
| DOCX_pipeline            | ⚡⚡⚡ Fast (0.3s) | Word documents             |
| IMG_pipeline (CPU)       | 🐌 Slow (5-8s)     | Scanned docs (no choice)   |
| IMG_pipeline (GPU)       | ⚡ Fast (1-3s)     | Scanned docs with GPU      |
| ROBUST_pipeline          | ⚡⚡ Medium (2-5s) | Complex layouts            |

**Batch processing (4 workers)**: 2-5 files/second mixed formats

---

## 🎓 Learning Curve

### Level 1 - User (5 minutes)

- Run `batch_folder_process.py`
- View results in Excel
- ✅ That's it!

### Level 2 - Power User (30 minutes)

- Understand different strategies
- Customize batch processing options
- Use web viewer
- Interpret results

### Level 3 - Developer (2-4 hours)

- Understand pipeline architecture
- Customize section detection
- Integrate into applications
- Add new features

### Level 4 - Expert (1-2 days)

- Modify core extraction logic
- Add new pipelines
- Optimize performance
- Train custom models

---

## 📚 Documentation Map

- **README.md** (root) - Main overview and quick start
- **scripts/README.md** - CLI tools documentation
- **src/core/README.md** - Core pipeline architecture
- **src/app/README.md** - Intelligence layer
- **src/PDF_pipeline/README.md** - PDF extraction details
- **src/DOCX_pipeline/README.md** - DOCX extraction details
- **src/IMG_pipeline/README.md** - OCR extraction details
- **src/ROBUST_pipeline/README.md** - Advanced parsing details
- **PROJECT_STRUCTURE.md** (this file) - Complete overview

---

## 🚀 Quick Reference

**Just want to parse resumes?**

```bash
python scripts/batch_folder_process.py --folder "resumes/" --output "results.xlsx"
```

**Want to integrate into Python app?**

```python
from src.core.unified_pipeline import UnifiedPipeline
pipeline = UnifiedPipeline()
result = pipeline.parse("resume.pdf")
```

**Having issues?**

```bash
python scripts/test_pipeline.py  # Run diagnostics
```

**Want to understand internals?**

- Read src/core/README.md first
- Then read specific pipeline READMEs as needed
