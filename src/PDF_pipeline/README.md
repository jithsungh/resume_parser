# PDF Pipeline - Digital PDF Extraction

Handles text extraction from digital (non-scanned) PDF files with sophisticated layout awareness.

## Purpose

Extract text from PDFs while preserving structure, handling multi-column layouts, and maintaining reading order.

## Key Files

### `pipeline.py` ⭐

**Main entry point** for PDF extraction.

**What it does**:

- Orchestrates the complete PDF parsing workflow
- Handles single and multi-column layouts
- Preserves text structure and hierarchy
- Segments content into logical sections

**Strategies**:

- **Simple mode**: Single-column PDFs (fast)
- **Histogram mode**: Multi-column detection via text distribution
- **Region mode**: Complex layouts with multiple regions

---

### `get_words.py` / `get_words_pymupdf.py`

**Purpose**: Extract raw words with coordinates from PDF.

**What they do**:

- Extract every word with (x, y, width, height, font_size)
- Two implementations:
  - `get_words.py`: Uses pdfplumber (more accurate)
  - `get_words_pymupdf.py`: Uses PyMuPDF (faster)

**Returns**:

```python
[
    {
        'text': 'Experience',
        'x0': 72.0,
        'y0': 150.5,
        'x1': 150.0,
        'y1': 165.5,
        'font_size': 14.0
    },
    ...
]
```

---

### `get_lines.py`

**Purpose**: Group words into logical lines.

**What it does**:

- Groups words by Y-coordinate (same horizontal line)
- Handles slight vertical misalignments
- Preserves reading order (left-to-right)
- Maintains font information for each line

**Key Parameters**:

- `y_tolerance`: How much vertical variance to allow in same line (default: 1.0)

---

### `histogram_column_detector.py`

**Purpose**: Detect columns using histogram analysis.

**What it does**:

- Creates histogram of text distribution across page width
- Identifies gaps (white space) between columns
- Determines column boundaries automatically
- Works for 1, 2, 3+ column layouts

**Algorithm**:

```
1. Create histogram: Count words at each X-position
2. Smooth histogram to reduce noise
3. Find valleys (gaps) in histogram
4. Valleys = column boundaries
5. Classify words into columns based on X-position
```

**Advantages**:

- Automatic - no manual column width specification
- Handles irregular column widths
- Robust to slight misalignments

---

### `region_detector.py`

**Purpose**: Detect distinct regions with different layouts.

**What it does**:

- Identifies regions with different column structures on same page
- Example: Header (1-column) + Body (2-column) + Footer (1-column)
- Processes each region independently with appropriate strategy

**Use Case**:

```
┌────────────────────────────┐
│      Name & Contact        │  ← Region 1: Single column
│       (Centered)           │
├──────────────┬─────────────┤
│  Experience  │   Skills    │  ← Region 2: Two columns
│  - Job 1     │   - Python  │
│  - Job 2     │   - AWS     │
├──────────────┴─────────────┤
│         Footer             │  ← Region 3: Single column
└────────────────────────────┘
```

---

### `split_columns.py`

**Purpose**: Split multi-column layouts into single columns.

**What it does**:

- Takes detected column boundaries
- Assigns each word/line to its column
- Maintains proper reading order within columns
- Handles column spans (text across multiple columns)

---

### `segment_sections.py`

**Purpose**: Identify resume sections (Experience, Education, Skills, etc.)

**What it does**:

- Detects section headers using multiple signals:
  - **Keyword matching**: "Experience", "Education", etc.
  - **Formatting**: Larger font, bold, uppercase
  - **Position**: Standalone lines, extra spacing
  - **Semantic**: Sentence-transformers embeddings
- Groups content under each section
- Maps creative headers to standard sections

**Standard Sections**:

- Contact Information
- Summary/Objective
- Experience/Work History
- Education
- Skills (Technical, Soft, Languages)
- Projects
- Certifications
- Achievements
- Publications
- Research
- Volunteer
- Hobbies
- References
- Declarations

**Section Detection Scoring**:

```python
score = 0.0
if keyword_match: score += 0.4
if large_font: score += 0.1
if uppercase: score += 0.15
if isolated_line: score += 0.1
if semantic_similarity > 0.7: score += 0.2
# If score > 0.5: It's a section header!
```

---

### `batch_process.py`

**Purpose**: Batch process multiple PDFs (legacy).

**Status**: Replaced by `src/core/batch_processor.py`. Kept for compatibility.

---

## Pipeline Flow

```
1. PDF Input
      ↓
2. get_words() - Extract words with coordinates
      ↓
3. get_lines() - Group words into lines
      ↓
4. histogram_column_detector() - Detect columns
   OR region_detector() - Detect regions
      ↓
5. split_columns() - Separate column content
      ↓
6. segment_sections() - Identify sections
      ↓
7. Output structured JSON
```

## Usage Examples

### Simple Single-Column PDF

```python
from src.PDF_pipeline.pipeline import run_pipeline

result, simplified_json = run_pipeline(
    "simple_resume.pdf",
    verbose=True
)
```

### Multi-Column PDF

```python
result, simplified_json = run_pipeline(
    "two_column_resume.pdf",
    use_histogram_columns=True,  # Enable column detection
    min_words_per_column=10,
    verbose=True
)
```

### Complex Region-Based Layout

```python
result, simplified_json = run_pipeline(
    "complex_resume.pdf",
    use_region_detection=True,  # Enable region detection
    verbose=True
)
```

## Configuration

Key parameters in `pipeline.py`:

```python
# Column detection
use_histogram_columns: bool = True
min_words_per_column: int = 10  # Min words to consider a column valid

# Line grouping
y_tolerance: float = 1.0  # Vertical tolerance for same line

# Section detection
min_section_score: float = 0.5  # Min score to be a section header
```

## Performance

- **Simple PDFs**: ~0.5-1 second per page
- **Multi-column**: ~1-2 seconds per page
- **Complex layouts**: ~2-3 seconds per page

## When to Use

| Layout Type           | Recommended Strategy          |
| --------------------- | ----------------------------- |
| Single column, simple | `run_pipeline()` default      |
| Two/three columns     | `use_histogram_columns=True`  |
| Mixed regions         | `use_region_detection=True`   |
| Very complex          | Use `ROBUST_pipeline` instead |

## Limitations

- Doesn't handle scanned PDFs (use IMG_pipeline/OCR)
- May struggle with highly creative layouts
- Assumes left-to-right, top-to-bottom reading order
- Tables may not parse perfectly (content is extracted but structure may be lost)

## Advanced Features

### Font-Based Hierarchy Detection

Larger fonts = headers/important content

### Semantic Section Matching

Uses sentence-transformers to match creative section names:

- "Where I've Worked" → Experience
- "What I Know" → Skills
- "My Background" → Education

### Dynamic Threshold Adjustment

Adapts section detection based on document characteristics
