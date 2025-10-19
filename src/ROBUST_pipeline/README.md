# Robust Resume Parser Pipeline

A layout-aware, recursive, hybrid approach for parsing complex resume layouts.

## 🔹 Key Features

### 1. **Layout-Aware Processing**

- Automatically detects document layout type: vertical, horizontal, hybrid, or simple
- Handles multi-column layouts with global coordinate tracking
- Processes mixed horizontal/vertical sections within the same document

### 2. **Recursive Block Splitting**

- Recursively splits complex layouts into manageable blocks
- Each block is processed independently with localized statistics
- Handles nested structures (e.g., two-column section within a single-column page)

### 3. **Adaptive Thresholds**

- Dynamically adjusts detection thresholds based on document characteristics
- Analyzes font sizes, spacing, layout patterns
- Optimizes for each document type (dense vs. sparse, simple vs. complex)

### 4. **Context-Aware Heading Detection**

- Uses localized block statistics instead of global heuristics
- Considers multiple signals: keywords, font size, spacing, capitalization, position
- Supports stylized headings (e.g., "E X P E R I E N C E", "S-K-I-L-L-S")

### 5. **Multi-Column Support**

- Maintains global column positions across pages
- Correctly handles column-based layouts
- Preserves reading order within and across columns

## 🔹 How It Works

### Pipeline Flow

```
PDF/Image Input
    ↓
Load & Preprocess (binary conversion, line removal)
    ↓
Detect Text Blocks
    ↓
Analyze Layout (columns, bands, hybrid detection)
    ↓
Recursive Block Splitting
    ↓
[For Each Block]
    ↓
Extract Text (OCR or PyMuPDF)
    ↓
Detect Headings (localized analysis)
    ↓
Split Sections (heading-based)
    ↓
[End For Each Block]
    ↓
Merge Sections (global)
    ↓
Output Structured JSON
```

### Block Detection Algorithm

1. **Horizontal Analysis**: Cluster blocks by x-coordinates → detect columns
2. **Vertical Analysis**: Cluster blocks by y-coordinates → detect bands
3. **Layout Classification**:

   - `vertical`: Single column, multiple bands
   - `horizontal`: Multiple columns, few bands
   - `hybrid`: Multiple columns AND multiple bands
   - `simple`: Single column, few bands

4. **Recursive Splitting**: If hybrid/horizontal, split into columns and recursively process each

### Heading Detection Algorithm

For each line in a block:

1. **Extract Features**:

   - Text characteristics: length, word count, capitalization
   - Layout features: font size ratio, spacing ratio, position
   - Semantic features: keyword matching, trailing colon

2. **Compute Score**:

   - Keyword match: +0.4 (strongest signal)
   - Short length: +0.15
   - Uppercase/title case: +0.15-0.20
   - Trailing colon: +0.1
   - Large font: +0.1
   - Extra spacing above: +0.15
   - Top position: +0.05

3. **Adaptive Threshold**:

   - Default: 0.3
   - Adjusts based on document variance (0.25-0.35)

4. **Section Mapping**:
   - Match against 300+ section keywords
   - Support for exact and fuzzy matching
   - Handle stylized formats

## 🔹 Usage

### Basic Usage

```python
from src.ROBUST_pipeline.pipeline import robust_pipeline

# Process a single resume
result, simplified = robust_pipeline(
    path="resume.pdf",
    use_ocr=True,
    use_gpu=False,
    dpi=300,
    max_depth=3,
    verbose=True
)

print(simplified)  # Simplified JSON output
```

### Batch Processing

```python
from src.ROBUST_pipeline.batch_process import batch_process_resumes

# Process multiple resumes
df = batch_process_resumes(
    input_dir="resumes/",
    output_dir="output/",
    use_ocr=True,
    use_gpu=False,
    dpi=300,
    max_depth=3,
    max_workers=4,
    file_pattern="*.pdf"
)

# Results saved to output/ directory
# Summary in batch_summary.xlsx
```

### Command Line

```bash
# Single file
python -m src.ROBUST_pipeline.pipeline \
    --pdf resume.pdf \
    --dpi 300 \
    --max_depth 3 \
    --gpu \
    --save output.json

# Batch processing
python -m src.ROBUST_pipeline.batch_process \
    --input resumes/ \
    --output results/ \
    --pattern "*.pdf" \
    --workers 4 \
    --dpi 300
```

### With Adaptive Thresholds

```python
from src.ROBUST_pipeline.adaptive_thresholds import AdaptiveThresholds
from src.ROBUST_pipeline.pipeline import robust_pipeline

# Create adaptive threshold manager
adaptive = AdaptiveThresholds()

# Process resume
result, simplified = robust_pipeline(
    path="resume.pdf",
    use_ocr=True,
    verbose=True
)

# Analyze and adjust thresholds
stats = adaptive.analyze_document([result])
thresholds = adaptive.adjust_thresholds(stats)

print("Adjusted thresholds:", thresholds)
```

## 🔹 Configuration Parameters

### `robust_pipeline()`

- **`path`** (str): Path to PDF or image file
- **`use_ocr`** (bool, default=True): Use OCR for text extraction
- **`use_gpu`** (bool, default=False): Use GPU acceleration for OCR
- **`dpi`** (int, default=300): Resolution for PDF rendering
- **`max_depth`** (int, default=3): Maximum recursion depth for block splitting
- **`verbose`** (bool, default=True): Print progress information

### `batch_process_resumes()`

- **`input_dir`** (str): Directory containing resume files
- **`output_dir`** (str): Directory to save results
- **`max_workers`** (int, default=4): Number of parallel workers
- **`file_pattern`** (str, default="\*.pdf"): Glob pattern for files

## 🔹 Adaptive Thresholds

The pipeline automatically adjusts thresholds based on document characteristics:

### Font Size Variance

- **High variance** (std/mean > 0.5): Distinct heading styles → lower threshold (0.25)
- **Medium variance** (0.3-0.5): Normal variation → default threshold (0.30)
- **Low variance** (<0.3): Similar fonts → higher threshold (0.35)

### Spacing Distribution

- **High variance**: More liberal spacing requirements (1.3x median)
- **Low variance**: Stricter spacing requirements (1.8x median)

### Layout Type

- **Horizontal** (multi-column): Tighter column tolerance (3%)
- **Vertical** (single column): Looser tolerance (8%)
- **Hybrid**: Balanced thresholds (5%)

### Document Density

- **Dense** (>50 lines/page): Smaller min block area (50px²)
- **Normal** (30-50 lines): Default block area (100px²)
- **Sparse** (<30 lines): Larger block area (150px²)

## 🔹 Advantages Over Linear Pipelines

| Aspect              | Linear Pipeline             | Robust Pipeline                     |
| ------------------- | --------------------------- | ----------------------------------- |
| **Layout**          | Horizontal OR vertical      | Recursive hybrid detection          |
| **Headings**        | Global spacing heuristics   | Localized block analysis + keywords |
| **Columns**         | Often ignored or mishandled | Global coordinate tracking          |
| **Complex layouts** | Frequently breaks           | Handles via recursive splitting     |
| **Thresholds**      | Fixed                       | Adaptive per document               |
| **Misassignment**   | Common with mixed layouts   | Rare due to block isolation         |

## 🔹 Output Format

### Simplified JSON

```json
[
  {
    "section": "Contact Information",
    "lines": ["John Doe", "john@example.com", "+1-234-567-8900"]
  },
  {
    "section": "Summary",
    "lines": ["Experienced software engineer with 5+ years..."]
  },
  {
    "section": "Experience",
    "lines": [
      "Senior Software Engineer | Company A | 2020-2023",
      "- Led team of 5 developers",
      "- Built scalable microservices"
    ]
  }
]
```

### Full JSON

```json
{
  "meta": {
    "pages": 2,
    "sections": 7,
    "total_lines": 143
  },
  "sections": [
    {
      "section": "Experience",
      "lines": [
        {
          "text": "Senior Software Engineer",
          "x0": 72.0,
          "y0": 250.5,
          "x1": 280.3,
          "y1": 265.8,
          "confidence": 0.95
        }
      ],
      "line_count": 28
    }
  ],
  "contact": {}
}
```

## 🔹 Performance

- **CPU-only**: No GPU required (but optional for faster OCR)
- **Memory efficient**: Processes blocks independently
- **Parallel processing**: Batch mode supports multi-core CPUs
- **Typical speed**: 2-5 seconds per page (300 DPI, OCR enabled)

## 🔹 Requirements

```
pymupdf>=1.23.0          # PDF rendering
opencv-python>=4.8.0     # Image processing
easyocr>=1.7.0          # OCR (optional but recommended)
numpy>=1.24.0           # Numerical operations
pandas>=2.0.0           # Data handling
tqdm>=4.66.0            # Progress bars
```

## 🔹 Troubleshooting

### Low accuracy on stylized headings

- The pipeline handles many stylized formats (spaced, dashed, etc.)
- If still missing, check that keywords are in `SECTION_MAP`
- Adjust `heading_score_threshold` lower (e.g., 0.25)

### Incorrect column detection

- Increase/decrease `column_tolerance` in adaptive thresholds
- Check if `max_depth` is sufficient for nested layouts
- Verify `min_block_area` isn't filtering out small columns

### Slow processing

- Reduce `dpi` (e.g., 200 instead of 300)
- Disable OCR if using native PDF text
- Enable GPU for OCR with `use_gpu=True`
- Reduce `max_depth` to limit recursion

### Memory issues

- Process fewer files in parallel (reduce `max_workers`)
- Lower `dpi` setting
- Process pages individually instead of entire document

## 🔹 Future Enhancements

- [ ] Table extraction within sections
- [ ] Contact info extraction from complex layouts
- [ ] Machine learning-based heading classifier
- [ ] Support for more file formats (DOCX images, HTML)
- [ ] GPU-accelerated image processing
- [ ] Real-time preview during processing
- [ ] Confidence scores for each section
- [ ] Automatic quality assessment

## 🔹 Contributing

To add new section keywords:

1. Edit `src/PDF_pipeline/segment_sections.py`
2. Add variants to the `SECTIONS` dictionary
3. Keywords are auto-normalized (case-insensitive, spacing-flexible)

## 🔹 License

Same as parent project.
