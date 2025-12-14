# 🚀 Smart Resume Parser - Advanced AI-Powered Resume Analysis System

<div align="center">

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)
![Status](https://img.shields.io/badge/status-production-success.svg)

**Transform resumes into structured data with industry-leading 90-95% accuracy**

[Quick Start](#-quick-start) • [Features](#-core-features) • [API](#-api-endpoints) • [Documentation](#-documentation) • [Deploy](#-deployment)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Core Features](#-core-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [API Endpoints](#-api-endpoints)
- [Supported Formats](#-supported-formats)
- [Parsing Pipelines](#-parsing-pipelines)
- [Extracted Information](#-extracted-information)
- [Advanced Features](#-advanced-features)
- [Installation](#-installation)
- [Usage Examples](#-usage-examples)
- [Configuration](#-configuration)
- [Deployment](#-deployment)
- [Development Tools](#-development-tools)
- [Project Structure](#-project-structure)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

---

## 🎯 Overview

**Smart Resume Parser** is an advanced, production-ready resume parsing system that automatically extracts structured information from resumes in multiple formats. Built with state-of-the-art NLP models and intelligent layout detection, it achieves **90-95% section accuracy** across diverse resume formats and layouts.

### Why This Parser?

✨ **Intelligent & Adaptive**

- Automatic pipeline selection (PDF/OCR/DOCX)
- Multi-column layout support (2-3 columns)
- Handles complex and hybrid layouts
- Letter-spaced heading detection (e.g., "P R O F I L E" → "PROFILE")

🎯 **High Accuracy**

- 90-95% section accuracy (vs 70-80% traditional parsers)
- Fine-tuned NER models for experience extraction
- Semantic section classification
- Robust contact information extraction

⚡ **Production Ready**

- RESTful API with FastAPI
- Batch processing support
- Docker containerization
- Comprehensive error handling
- Background job processing

---

## ✨ Core Features

### 🤖 Smart Layout Detection

The parser automatically analyzes PDF structure and selects the optimal processing pipeline:

- **Layout Analysis**: Detects columns, text density, and complexity
- **Scan Detection**: Identifies scanned vs native PDFs
- **Pipeline Routing**: Automatically chooses PDF, OCR, or DOCX pipeline
- **Confidence Scoring**: Provides confidence metrics for decisions

### 📊 Advanced Layout Processing

**Three-Type Layout Classification:**

| Layout Type | Description              | Detection Method          |
| ----------- | ------------------------ | ------------------------- |
| **Type 1**  | Single-column, standard  | Single histogram peak     |
| **Type 2**  | Multi-column, clear gaps | Deep valleys (reach 0)    |
| **Type 3**  | Hybrid/Complex, mixed    | Shallow valleys, overlaps |

**Column Detection Methods:**

- **Histogram-based**: Vertical projection analysis for column boundaries
- **Y-overlap analysis**: Detects reading order in multi-column layouts
- **Adaptive thresholds**: Dynamic adjustment based on document characteristics

### 🧠 NER-Based Information Extraction

Powered by fine-tuned Transformer models:

- **Named Entity Recognition**: Extract companies, roles, dates, skills
- **Experience Timeline**: Calculate total years and role progression
- **Skills Extraction**: Technology and skill identification per role
- **Contact Extraction**: Name, email, phone, location

### 📝 Section Segmentation

Intelligent section detection with multiple fallback strategies:

1. **Keyword Matching**: 100+ section heading patterns
2. **Letter-Spacing Detection**: Handles stylized headings
3. **Semantic Classification**: Embedding-based section identification
4. **Multi-Section Headers**: Detects combined headers (e.g., "SKILLS & CERTIFICATIONS")

### 🔄 Multiple Processing Pipelines

**PDF Pipeline** (Native PDFs)

- PyMuPDF-based text extraction
- Rich metadata (fonts, colors, positions)
- Fast processing (~1-3 seconds)
- Multi-column support with histogram analysis

**OCR Pipeline** (Scanned PDFs/Images)

- EasyOCR for text recognition
- GPU acceleration support
- Multi-language support (20+ languages)
- High DPI rendering (300 DPI default)

**DOCX Pipeline** (Microsoft Word)

- python-docx document parsing
- Paragraph and style extraction
- Table content handling
- Maintains document structure

**ROBUST Pipeline** (Fallback)

- Adaptive threshold adjustment
- Enhanced error recovery
- Handles corrupted or unusual formats

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     API Layer (FastAPI)                      │
│  ┌──────────────┬──────────────┬────────────────────────┐  │
│  │ Smart Parse  │ Batch Parse  │ NER Extract │ Segment │  │
│  └──────────────┴──────────────┴────────────────────────┘  │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               Smart Parser (Layout Detector)                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ • Analyze PDF structure                              │  │
│  │ • Detect columns & complexity                        │  │
│  │ • Recommend optimal pipeline                         │  │
│  └──────────────────────────────────────────────────────┘  │
└────────┬───────────────────┬──────────────────┬─────────────┘
         │                   │                  │
    ┌────▼────┐       ┌──────▼──────┐    ┌────▼─────┐
    │   PDF   │       │     OCR     │    │   DOCX   │
    │ Pipeline│       │  Pipeline   │    │ Pipeline │
    └────┬────┘       └──────┬──────┘    └────┬─────┘
         │                   │                 │
         └───────────────┬───────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Processing Pipeline                         │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 1. Document Detection → Type & Scan Status           │  │
│  │ 2. Word Extraction → Text + Rich Metadata            │  │
│  │ 3. Layout Detection → Column Analysis (Histogram)    │  │
│  │ 4. Column Segmentation → Split & Assign Words        │  │
│  │ 5. Line Grouping → Y-overlap Analysis                │  │
│  │ 6. Section Detection → Headers & Content             │  │
│  │ 7. NER Extraction → Experience, Skills, Dates        │  │
│  │ 8. Contact Extraction → Name, Email, Phone           │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Structured Output                          │
│  • Sections with lines and content                          │
│  • Contact information (name, email, mobile, location)       │
│  • Work experience with timeline and skills                  │
│  • Metadata (pipeline used, processing time, confidence)     │
└─────────────────────────────────────────────────────────────┘
```

### Pipeline Decision Flow

```
PDF File
   │
   ▼
┌──────────────────┐
│ Layout Detector  │
│   Analysis       │
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
Scanned?   Native?
    │         │
    ▼         ▼
┌───────┐  ┌──────┐
│  OCR  │  │ PDF  │
│Pipeline│ │Pipeline│
└───────┘  └──────┘
    │         │
    └────┬────┘
         │
         ▼
   ┌──────────┐
   │ Sections │
   │ + NER    │
   └──────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip package manager
- (Optional) Docker for containerized deployment

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd resume_parser

# Install dependencies
pip install -r requirements.txt

# Download spaCy model (optional, for enhanced name extraction)
python -m spacy download en_core_web_sm
```

### Start the API Server

**Option 1: Direct Python**

```bash
python -m src.api
```

**Option 2: Uvicorn (Development)**

```bash
uvicorn src.api.main:app --reload --port 8000
```

**Option 3: Docker**

```bash
docker-compose up
```

The API will be available at:

- **API Base**: `http://localhost:8000/api/v1`
- **Interactive Docs**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/api/v1/health`

---

## 🔌 API Endpoints

### Core Endpoints

#### 🌟 Smart Parse (RECOMMENDED)

**Parse single resume with automatic pipeline selection**

```bash
POST /api/v1/parse/smart
```

```bash
# Example
curl -X POST "http://localhost:8000/api/v1/parse/smart" \
  -F "file=@resume.pdf"
```

**Query Parameters:**

- `force_pipeline` (optional): Force `pdf` or `ocr` pipeline

**Response:**

```json
{
  "success": true,
  "filename": "resume.pdf",
  "sections": [
    {
      "section_name": "Experience",
      "lines": ["Software Engineer at Google", "2020 - Present", ...]
    },
    {
      "section_name": "Education",
      "lines": ["B.S. Computer Science", "Stanford University", ...]
    }
  ],
  "metadata": {
    "pipeline_used": "pdf",
    "processing_time": 1.23,
    "num_columns": 2,
    "layout_complexity": "moderate",
    "confidence": 0.85
  }
}
```

#### 📦 Batch Smart Parse

**Parse multiple resumes in parallel**

```bash
POST /api/v1/batch/smart-parse
```

```bash
# Example
curl -X POST "http://localhost:8000/api/v1/batch/smart-parse" \
  -F "files=@resume1.pdf" \
  -F "files=@resume2.pdf" \
  -F "files=@resume3.pdf"
```

**Response:**

```json
{
  "job_id": "uuid-here",
  "status": "processing",
  "total_files": 3,
  "message": "Batch job started"
}
```

#### 📊 Check Batch Status

```bash
GET /api/v1/batch/status/{job_id}
```

**Response:**

```json
{
  "job_id": "uuid-here",
  "status": "completed",
  "total": 3,
  "completed": 3,
  "failed": 0,
  "results": [...]
}
```

### Additional Endpoints

#### Parse Single Resume (Legacy, uses smart parser internally)

```bash
POST /api/v1/parse/single
```

Accepts PDF, DOCX, or TXT files. Returns complete parsing result with contact info and experience.

#### NER-Only Extraction

```bash
POST /api/v1/ner/extract
```

Extract only named entities (companies, roles, dates, skills) from text.

#### Section Segmentation Only

```bash
POST /api/v1/sections/segment
```

Segment resume into sections without full NER processing.

#### Contact Extraction

```bash
POST /api/v1/contact/extract
```

Quick extraction of contact information only.

#### Health Check

```bash
GET /api/v1/health
```

Returns service status, model availability, and version information.

---

## 📁 Supported Formats

| Format             | Extension       | Pipeline | Features                             |
| ------------------ | --------------- | -------- | ------------------------------------ |
| **Native PDF**     | `.pdf`          | PDF      | Fast, rich metadata, multi-column    |
| **Scanned PDF**    | `.pdf`          | OCR      | EasyOCR, GPU support, multi-language |
| **Microsoft Word** | `.docx`, `.doc` | DOCX     | Paragraph styles, tables             |
| **Plain Text**     | `.txt`          | Text     | Basic extraction                     |

### Language Support (OCR)

20+ languages including:

- English (`en`)
- Spanish (`es`)
- French (`fr`)
- German (`de`)
- Chinese (`ch_sim`, `ch_tra`)
- Japanese (`ja`)
- Korean (`ko`)
- And many more...

---

## 🔄 Parsing Pipelines

### 1. PDF Pipeline (Native PDFs)

**Best for:** Native PDFs with selectable text

**Features:**

- PyMuPDF-based extraction
- Font metadata (family, size, bold, italic, color)
- Bounding box coordinates
- Multi-column detection via histogram analysis
- Fast processing (1-3 seconds)

**Process:**

1. Extract words with rich metadata
2. Analyze layout with vertical histograms
3. Detect columns and boundaries
4. Group words into lines
5. Identify section headers
6. Segment content into sections
7. Extract contact information
8. Run NER on experience sections

### 2. OCR Pipeline (Scanned PDFs/Images)

**Best for:** Scanned documents, images, low-quality PDFs

**Features:**

- EasyOCR text recognition
- GPU acceleration support
- Multi-language recognition
- High-resolution rendering (300 DPI)
- Confidence scoring per word

**Process:**

1. Render PDF pages to images (300 DPI)
2. Run EasyOCR on each page
3. Extract word bounding boxes and text
4. Follow same pipeline as PDF
5. Additional quality validation

**Configuration:**

```python
# Example with custom settings
result = smart_parse_resume(
    "resume.pdf",
    force_pipeline="ocr",
    ocr_dpi=300,
    ocr_languages=['en', 'es'],
    verbose=True
)
```

### 3. DOCX Pipeline (Microsoft Word)

**Best for:** .docx and .doc files

**Features:**

- python-docx parsing
- Paragraph and run analysis
- Style and formatting extraction
- Table content handling
- Header/footer processing

**Process:**

1. Parse document structure
2. Extract paragraphs with styles
3. Identify headers via formatting
4. Group content into sections
5. Extract tables and lists
6. Run contact and NER extraction

### 4. ROBUST Pipeline (Fallback)

**Best for:** Edge cases, corrupted files, unusual formats

**Features:**

- Adaptive threshold adjustment
- Enhanced error recovery
- Fallback strategies
- Detailed debugging information

---

## 📤 Extracted Information

### Contact Information

```json
{
  "name": "John Doe",
  "email": "john.doe@email.com",
  "mobile": "+1 (555) 123-4567",
  "location": "San Francisco, CA",
  "linkedin": "linkedin.com/in/johndoe",
  "github": "github.com/johndoe"
}
```

**Extraction Methods:**

- **Name**: spaCy NER, email inference, filename heuristics
- **Email**: Regex pattern matching
- **Phone**: International format support
- **Location**: NER (GPE entities), pattern matching
- **Social**: URL pattern extraction

### Work Experience

```json
{
  "total_experience_years": 5.5,
  "primary_role": "Software Engineer",
  "experiences": [
    {
      "company_name": "Google LLC",
      "role": "Senior Software Engineer",
      "from": "2020-06",
      "to": "Present",
      "duration_months": 42,
      "skills": [
        "Python",
        "Machine Learning",
        "TensorFlow",
        "Kubernetes",
        "Docker",
        "AWS"
      ]
    },
    {
      "company_name": "Microsoft",
      "role": "Software Engineer",
      "from": "2018-01",
      "to": "2020-05",
      "duration_months": 28,
      "skills": ["C#", ".NET", "Azure", "SQL Server"]
    }
  ]
}
```

**NER Entities:**

- `COMPANY`: Company names
- `ROLE`: Job titles and positions
- `DATE`: Start and end dates
- `SKILL`: Technologies and skills

### Resume Sections

Automatically detected sections:

- Experience / Work History / Employment
- Education / Academic Background
- Skills / Technical Skills / Core Competencies
- Certifications / Licenses
- Projects / Portfolio
- Awards / Honors / Achievements
- Publications / Research
- Languages / Language Proficiency
- Volunteer / Community Service
- References

---

## 🎨 Advanced Features

### Layout Analysis

**Histogram-Based Column Detection**

The parser uses vertical projection histograms to detect column boundaries:

```python
def detect_columns_with_histogram(words, page_width):
    # Create histogram of word density across page width
    histogram = compute_vertical_histogram(words, page_width)

    # Smooth to reduce noise
    smoothed = smooth_histogram(histogram)

    # Detect valleys (gaps between columns)
    valleys = detect_valleys(smoothed)

    # Classify layout type
    layout_type = classify_layout_type(valleys, histogram)

    return column_boundaries, layout_type
```

**Layout Types:**

- **Type 1**: Single column (1 peak, simple reading order)
- **Type 2**: Multi-column with clear gaps (valleys reach 0)
- **Type 3**: Hybrid layout (overlapping sections, complex structure)

### Section Header Detection

**Multi-Strategy Approach:**

1. **Keyword Matching**

   - 100+ predefined section patterns
   - Case-insensitive with variations
   - Plural and singular forms

2. **Letter-Spacing Handler**

   ```python
   # Detects: "P R O F I L E" → "PROFILE"
   # Detects: "S K I L L S" → "SKILLS"
   ```

3. **Font Heuristics**

   - Bold text detection
   - Font size analysis
   - All-caps patterns
   - Color differences

4. **Semantic Classification**
   - Sentence transformer embeddings
   - Similarity scoring with known sections
   - Threshold-based classification (0.68)

### Unknown Section Detection

For ambiguous headers not matching known patterns:

```json
{
  "unknown_sections": [
    {
      "header": "Core Competencies",
      "suggested_section": "Skills",
      "confidence": 0.72,
      "alternative_suggestions": [
        { "section": "Experience", "score": 0.45 },
        { "section": "Projects", "score": 0.38 }
      ]
    }
  ]
}
```

### Batch Processing

**Features:**

- Parallel file processing
- Background job execution
- Progress tracking
- Result aggregation
- Error handling per file

**Configuration:**

```python
# In docker-compose.yml or environment
MAX_BATCH_SIZE=100
WORKER_THREADS=4
```

---

## 💻 Installation

### System Requirements

- **OS**: Windows, Linux, macOS
- **Python**: 3.8+
- **Memory**: 4GB+ RAM (8GB+ recommended)
- **Storage**: 2GB+ for models

### Dependencies Installation

```bash
# Core dependencies
pip install -r requirements.txt

# spaCy model (optional, for enhanced NER)
python -m spacy download en_core_web_sm

# For GPU support (OCR)
pip install easyocr[gpu]
```

### Linux System Dependencies

**For OCR support on headless servers:**

```bash
# RHEL/CentOS
sudo yum install mesa-libGL

# Ubuntu/Debian
sudo apt-get install libgl1

# Or use install script
chmod +x install_system_deps.sh
./install_system_deps.sh
```

### Verify Installation

```bash
python verify_installation.py
```

This checks:

- Python version
- Required packages
- Optional dependencies
- Model availability
- System compatibility

---

## 📖 Usage Examples

### Python API

```python
from src.smart_parser import smart_parse_resume

# Parse with auto-detection
result, simplified_json, metadata = smart_parse_resume(
    "resume.pdf",
    verbose=True
)

print(f"Pipeline used: {metadata['pipeline_used']}")
print(f"Columns detected: {metadata['layout_analysis']['num_columns']}")
print(f"Processing time: {metadata['processing_time']:.2f}s")

# Access sections
for section in result['sections']:
    print(f"\n{section['section_name']}:")
    for line in section['lines']:
        print(f"  {line}")
```

### Force Specific Pipeline

```python
# Force OCR for testing
result, json_str, metadata = smart_parse_resume(
    "resume.pdf",
    force_pipeline="ocr",
    ocr_dpi=300,
    ocr_languages=['en', 'es']
)
```

### Complete Resume Parser (with NER)

```python
from src.core.complete_resume_parser import CompleteResumeParser

# Initialize parser
parser = CompleteResumeParser(model_path='./ml_model')

# Parse resume
result = parser.parse_resume(
    resume_text="full resume text here",
    filename="john_doe_resume.pdf"
)

print(f"Name: {result['name']}")
print(f"Email: {result['email']}")
print(f"Total Experience: {result['total_experience_years']} years")
print(f"Primary Role: {result['primary_role']}")

for exp in result['experiences']:
    print(f"\n{exp['role']} at {exp['company_name']}")
    print(f"Duration: {exp['from']} to {exp['to']}")
    print(f"Skills: {', '.join(exp['skills'])}")
```

### Batch Processing

```python
from src.smart_parser import batch_smart_parse

# Process multiple files
results = batch_smart_parse(
    pdf_paths=[
        "resume1.pdf",
        "resume2.pdf",
        "resume3.pdf"
    ],
    output_dir="./outputs",
    verbose=True
)

for result in results:
    print(f"{result['filename']}: {result['status']}")
```

### Using the API Client

```python
import requests

# Upload and parse
with open("resume.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/parse/smart",
        files={"file": f}
    )

result = response.json()
print(f"Success: {result['success']}")
print(f"Sections found: {len(result['sections'])}")
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# Model Configuration
MODEL_PATH=./ml_model

# API Server
HOST=0.0.0.0
PORT=8000
RELOAD=False

# Processing
MAX_BATCH_SIZE=100
WORKER_THREADS=4

# Logging
LOG_LEVEL=INFO

# OCR Settings (optional)
OCR_DPI=300
OCR_LANGUAGES=en,es
OCR_GPU=false
```

### Pipeline Parameters

**PDF Pipeline:**

```python
from src.PDF_pipeline.pipeline import run_pipeline

result, json_str = run_pipeline(
    pdf_path="resume.pdf",
    min_words_per_column=10,
    y_tolerance=1.0,
    use_histogram_detection=True,
    verbose=True
)
```

**OCR Pipeline:**

```python
from src.IMG_pipeline.pipeline import run_pipeline_ocr

result, json_str = run_pipeline_ocr(
    pdf_path="scanned_resume.pdf",
    dpi=300,
    languages=['en'],
    gpu=False,
    min_words_per_column=10,
    verbose=True
)
```

**DOCX Pipeline:**

```python
from src.DOCX_pipeline.pipeline import run_pipeline

result, json_str = run_pipeline(
    docx_path="resume.docx",
    verbose=True
)
```

---

## 🐳 Deployment

### Docker Deployment

**Build and Run:**

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**Services:**

- **Backend API**: Port 8000
- **Frontend** (if configured): Port 3000

### Docker Compose Configuration

```yaml
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./ml_model:/app/ml_model:ro
      - ./outputs:/app/outputs
    environment:
      - MODEL_PATH=/app/ml_model
      - HOST=0.0.0.0
      - PORT=8000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Production Deployment

**Using Gunicorn:**

```bash
gunicorn src.api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120
```

**Nginx Reverse Proxy:**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 🛠️ Development Tools

### Testing Scripts

```bash
# Test smart API
python test_smart_api.py

# Test complete parser
python test_complete_parser.py

# Test NER pipeline
python test_ner_pipeline.py

# Test specific pipeline
python test_refactored_pipeline.py

# Test layout detection
python test_enhanced_layout_detection.py

# Test multi-column splitting
python test_multi_column_splitting.py
```

### Quick Testing

```bash
# Quick parse single file
python quick_parse.py resume.pdf

# Quick validation
python quick_validation.py

# Test API integration
python test_api_integration.py
```

### Debugging Tools

```bash
# Debug segmentation
python debug_segmentation.py resume.pdf

# Visualize layout
python visualize_2d_layout.py resume.pdf

# Check word distribution
python visualize_word_distribution.py resume.pdf

# Debug histogram analysis
python debug_histogram_analysis.py resume.pdf

# Analyze section detection
python analyze_experience_sections.py
```

### Data Labeling Tools

**Resume Layout Labeling System**

For training and improving layout detection:

```bash
# Windows
start_labeling.bat

# Linux/Mac
chmod +x start_labeling.sh
./start_labeling.sh
```

**Advanced Labeling Tool**

```bash
# Windows
start_advanced_labeling.bat

# Linux/Mac
./start_advanced_labeling.sh
```

Features:

- PDF rendering with zoom
- Auto feature extraction (9+ numeric features)
- One-click Type 1/2/3 classification
- Auto-save to CSV and JSON
- Progress tracking
- Feature inspection

### Batch Processing Scripts

```bash
# Batch resume parsing
python batch_resume_parser.py --input_dir ./resumes --output_dir ./outputs

# Segment batch
python segment_batch.py --input_dir ./resumes

# Batch segmentation debugger
python batch_segmentation_debugger.py
```

---

## 📂 Project Structure

```
resume_parser/
├── src/
│   ├── api/                          # FastAPI application
│   │   ├── main.py                   # API entry point
│   │   ├── routes.py                 # API endpoints
│   │   ├── service.py                # Business logic
│   │   ├── models.py                 # Pydantic models
│   │   ├── config.py                 # Configuration
│   │   └── utils.py                  # Utilities
│   │
│   ├── core/                         # Core parsing modules
│   │   ├── complete_resume_parser.py # Complete parser with NER
│   │   ├── ner_pipeline.py           # NER-based pipeline
│   │   ├── unified_resume_pipeline.py # Unified pipeline orchestration
│   │   ├── document_detector.py      # Document type detection
│   │   ├── word_extractor.py         # Word extraction with metadata
│   │   ├── layout_detector_histogram.py # Histogram-based layout
│   │   ├── column_segmenter.py       # Column segmentation
│   │   ├── line_section_grouper.py   # Line and section grouping
│   │   ├── section_splitter.py       # Section splitting
│   │   ├── name_location_extractor.py # Name & location extraction
│   │   ├── ner_experience_extractor.py # Experience NER
│   │   ├── resume_info_extractor.py  # Resume information
│   │   ├── unknown_section_detector.py # Unknown section detection
│   │   ├── section_learner.py        # Section learning
│   │   ├── roles_mapper.py           # Role mapping
│   │   ├── parser.py                 # Legacy parser
│   │   └── batch_processor.py        # Batch processing
│   │
│   ├── PDF_pipeline/                 # PDF processing pipeline
│   │   ├── pipeline.py               # Main PDF pipeline
│   │   ├── get_words_pymupdf.py      # PyMuPDF word extraction
│   │   ├── get_words.py              # Word extraction wrapper
│   │   ├── get_lines.py              # Line grouping
│   │   ├── split_columns.py          # Column splitting
│   │   ├── histogram_column_detector.py # Histogram detection
│   │   ├── segment_sections.py       # Section segmentation
│   │   ├── region_detector.py        # Region detection
│   │   └── batch_process.py          # Batch PDF processing
│   │
│   ├── IMG_pipeline/                 # OCR/Image pipeline
│   │   ├── pipeline.py               # Main OCR pipeline
│   │   ├── get_words_ocr.py          # EasyOCR extraction
│   │   └── batch_process.py          # Batch OCR processing
│   │
│   ├── DOCX_pipeline/                # DOCX processing pipeline
│   │   ├── pipeline.py               # Main DOCX pipeline
│   │   ├── get_lines_from_docx.py    # DOCX line extraction
│   │   └── batch_process.py          # Batch DOCX processing
│   │
│   ├── ROBUST_pipeline/              # Robust fallback pipeline
│   │   ├── pipeline.py               # Main robust pipeline
│   │   ├── pipeline_ocr.py           # OCR variant
│   │   ├── adaptive_thresholds.py    # Adaptive processing
│   │   └── batch_process.py          # Batch robust processing
│   │
│   ├── app/                          # Application layer
│   │   ├── file_detector.py          # File type detection
│   │   ├── layout_analyzer.py        # Layout analysis
│   │   ├── quality_validator.py      # Quality validation
│   │   └── strategy_selector.py      # Strategy selection
│   │
│   ├── smart_parser.py               # Smart parser (MAIN ENTRY)
│   ├── layout_detector.py            # Layout detector
│   └── detect_layout.py              # Layout detection utilities
│
├── config/
│   ├── sections_database.json        # Section definitions
│   └── roles.py                      # Role mappings
│
├── frontend/                         # Frontend application (optional)
│   ├── index.html
│   ├── package.json
│   └── Dockerfile
│
├── scripts/                          # Utility scripts
│
├── outputs/                          # Output directory
│
├── ml_model/                         # NER model files (not in repo)
│
├── test_*.py                         # Test files
├── debug_*.py                        # Debug utilities
├── analyze_*.py                      # Analysis tools
├── label_resumes.py                  # Labeling tool
├── advanced_labeling_tool.py         # Advanced labeling
├── batch_resume_parser.py            # Batch parser
├── segment_*.py                      # Segmentation tools
├── visualize_*.py                    # Visualization tools
│
├── requirements.txt                  # Python dependencies
├── docker-compose.yml                # Docker composition
├── Dockerfile                        # Docker image
├── README.md                         # This file
├── IMPLEMENTATION_SUMMARY.md         # Implementation details
├── QUICK_START.md                    # Quick start guide
├── REFACTORED_PIPELINE_README.md     # Pipeline architecture
├── LABELING_README.md                # Labeling system docs
├── ADVANCED_LABELING_GUIDE.md        # Advanced labeling guide
└── LABELING_GUIDE.md                 # Labeling instructions
```

---

## 🐛 Troubleshooting

### Common Issues

#### OCR Not Working

**Error**: `ImportError: libGL.so.1: cannot open shared object file`

**Solution**:

```bash
# Ubuntu/Debian
sudo apt-get install libgl1

# RHEL/CentOS
sudo yum install mesa-libGL
```

#### spaCy Model Not Found

**Error**: `Can't find model 'en_core_web_sm'`

**Solution**:

```bash
python -m spacy download en_core_web_sm
```

#### Model Path Issues

**Error**: `Model path not found`

**Solution**:

```bash
# Set environment variable
export MODEL_PATH=/path/to/ml_model

# Or in docker-compose.yml
environment:
  - MODEL_PATH=/app/ml_model
```

#### Low Accuracy on Multi-Column PDFs

**Solution**: The smart parser automatically handles this, but you can force histogram detection:

```python
result = smart_parse_resume(
    "resume.pdf",
    force_pipeline="pdf"  # Uses histogram column detection
)
```

#### Slow Processing

**Solutions**:

- Enable GPU for OCR: `gpu=True`
- Reduce OCR DPI: `dpi=150` (default 300)
- Use PDF pipeline when possible (avoid forcing OCR)
- Increase worker threads for batch processing

#### Docker Memory Issues

**Solution**: Increase Docker memory allocation:

```bash
# In docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 4G
```

---

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

- **Accuracy**: Improve section detection for edge cases
- **Performance**: Optimize processing speed
- **Language Support**: Add more languages for OCR
- **Features**: Add new extraction capabilities
- **Documentation**: Improve guides and examples

### Development Setup

```bash
# Clone repository
git clone <repo-url>
cd resume_parser

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Install dev dependencies
pip install pytest pytest-asyncio black flake8
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test
pytest test_smart_api.py -v

# Run with coverage
pytest --cov=src tests/
```

---

## 📊 Performance Benchmarks

### Accuracy Metrics

| Layout Type    | Section Accuracy | Processing Time |
| -------------- | ---------------- | --------------- |
| Single-column  | 92-95%           | 1-2 seconds     |
| Two-column     | 88-93%           | 2-3 seconds     |
| Three-column   | 85-90%           | 3-4 seconds     |
| Complex/Hybrid | 80-88%           | 3-5 seconds     |

### Processing Speed

| Pipeline | Format      | Time per Page |
| -------- | ----------- | ------------- |
| PDF      | Native PDF  | 0.5-1.5s      |
| OCR      | Scanned PDF | 3-8s          |
| DOCX     | Word Doc    | 0.3-1s        |

_Tested on: Intel i7, 16GB RAM, no GPU_

---

## 📄 License

MIT License - see LICENSE file for details

---

## 📮 Support

For issues, questions, or feature requests:

- Create an issue in the repository
- Check existing documentation
- Review troubleshooting section

---

## 🙏 Acknowledgments

Built with:

- **FastAPI**: Modern web framework
- **PyMuPDF**: PDF processing
- **EasyOCR**: OCR text recognition
- **spaCy**: NLP and NER
- **Transformers**: NER model fine-tuning
- **sentence-transformers**: Semantic embeddings
- **pdfplumber**: PDF text extraction
- **python-docx**: DOCX parsing

---

<div align="center">

**Made with ❤️ for better resume parsing**

⭐ Star this repo if you find it useful!

</div>
