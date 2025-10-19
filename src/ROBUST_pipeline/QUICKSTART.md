# Quick Start Guide - Robust Resume Parser

## Installation

1. **Install dependencies:**

```bash
pip install -r requirements.txt
```

Key dependencies for robust pipeline:

- `opencv-python` - Image processing and layout detection
- `pymupdf` - PDF rendering
- `easyocr` - OCR for text extraction
- `numpy`, `pandas` - Data processing

## Basic Usage

### 1. Parse a Single Resume

```python
from src.ROBUST_pipeline.pipeline import robust_pipeline

# Process resume
result, simplified_json = robust_pipeline(
    path="resume.pdf",
    use_ocr=True,      # Use OCR for text extraction
    use_gpu=False,     # Set True if you have CUDA GPU
    dpi=300,           # Resolution (higher = better quality, slower)
    max_depth=3,       # Recursion depth for block splitting
    verbose=True       # Print progress
)

# Print simplified output
print(simplified_json)

# Access structured data
for section in result['sections']:
    print(f"\n{section['section']}:")
    for line in section['lines']:
        print(f"  {line['text']}")
```

### 2. Batch Process Multiple Resumes

```python
from src.ROBUST_pipeline.batch_process import batch_process_resumes

# Process entire folder
df = batch_process_resumes(
    input_dir="freshteams_resume/Automation Testing/",
    output_dir="outputs/robust_results/",
    use_ocr=True,
    max_workers=4,     # Parallel processing
    file_pattern="*.pdf"
)

# Check results
print(f"Processed: {len(df)} files")
print(f"Success: {df['success'].sum()}")
print(f"Failed: {(~df['success']).sum()}")
```

### 3. Command Line Usage

```bash
# Single file
python -m src.ROBUST_pipeline.pipeline \
    --pdf freshteams_resume/Automation\ Testing/Amarnathd.pdf \
    --dpi 300 \
    --save output.json

# Batch processing
python -m src.ROBUST_pipeline.batch_process \
    --input freshteams_resume/Automation\ Testing/ \
    --output outputs/robust_batch/ \
    --workers 4
```

## Testing on Your Resumes

### Test Single File

```bash
# Test with your challenging resume
python src/ROBUST_pipeline/test_robust.py \
    --pdf freshteams_resume/challenging/complex_layout.pdf
```

This will:

- Run both robust and standard pipelines
- Show side-by-side comparison
- Highlight sections found by each method

### Test Adaptive Thresholds

```bash
# Test on multiple resumes to see threshold adaptation
python src/ROBUST_pipeline/test_robust.py \
    --batch \
    freshteams_resume/Automation\ Testing/Amarnathd.pdf \
    freshteams_resume/Backend\ Java\ Developer/resume1.pdf \
    freshteams_resume/ReactJs/resume2.pdf
```

## Understanding the Output

### Simplified JSON Format

```json
[
  {
    "section": "Contact Information",
    "lines": ["John Doe", "john@email.com"]
  },
  {
    "section": "Experience",
    "lines": [
      "Senior Engineer | Company | 2020-2023",
      "- Developed features",
      "- Led team of 5"
    ]
  }
]
```

### Full JSON Format

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
          "text": "Senior Engineer",
          "x0": 72.0,
          "y0": 250.5,
          "x1": 280.3,
          "y1": 265.8,
          "confidence": 0.95
        }
      ],
      "line_count": 28
    }
  ]
}
```

## Performance Tips

### For Speed

```python
# Use lower DPI
result, _ = robust_pipeline(path="resume.pdf", dpi=200)

# Disable OCR if PDF has text layer
result, _ = robust_pipeline(path="resume.pdf", use_ocr=False)

# Reduce max recursion depth
result, _ = robust_pipeline(path="resume.pdf", max_depth=2)
```

### For Accuracy

```python
# Use higher DPI
result, _ = robust_pipeline(path="resume.pdf", dpi=400)

# Enable GPU acceleration
result, _ = robust_pipeline(path="resume.pdf", use_gpu=True)

# Increase recursion depth for complex layouts
result, _ = robust_pipeline(path="resume.pdf", max_depth=4)
```

## Handling Different Resume Types

### Simple Single-Column Resume

```python
# Fast settings - don't need deep recursion
result, _ = robust_pipeline(
    path="simple_resume.pdf",
    dpi=200,
    max_depth=1,
    use_ocr=False  # If PDF has text
)
```

### Complex Multi-Column Resume

```python
# Accuracy settings - need full analysis
result, _ = robust_pipeline(
    path="complex_resume.pdf",
    dpi=300,
    max_depth=3,
    use_ocr=True
)
```

### Scanned Image Resume

```python
# Must use OCR
result, _ = robust_pipeline(
    path="scanned_resume.pdf",
    dpi=300,
    use_ocr=True,
    use_gpu=True  # If available
)
```

## Troubleshooting

### Problem: Missing Sections

**Solution 1**: Check if keywords are recognized

```python
from src.PDF_pipeline.segment_sections import guess_section_name

# Test your heading
heading = "WORK EXPERIENCE"
section = guess_section_name(heading)
print(f"'{heading}' → '{section}'")
```

**Solution 2**: Lower heading threshold

```python
from src.ROBUST_pipeline.adaptive_thresholds import AdaptiveThresholds

adaptive = AdaptiveThresholds()
adaptive.heading_score_threshold = 0.25  # Lower = more permissive
```

### Problem: Incorrect Column Detection

**Solution**: Adjust column tolerance

```python
from src.ROBUST_pipeline.adaptive_thresholds import AdaptiveThresholds

adaptive = AdaptiveThresholds()
adaptive.column_tolerance = 0.08  # Higher = merge more columns
# or
adaptive.column_tolerance = 0.03  # Lower = split into more columns
```

### Problem: Slow Processing

**Solutions**:

1. Use lower DPI: `dpi=200`
2. Disable OCR if possible: `use_ocr=False`
3. Reduce workers in batch mode: `max_workers=2`
4. Process files sequentially instead of parallel

### Problem: Out of Memory

**Solutions**:

1. Reduce DPI: `dpi=150`
2. Process one file at a time
3. Reduce max_workers: `max_workers=1`
4. Close other applications

## Comparing with Standard Pipeline

```python
from src.ROBUST_pipeline.pipeline import robust_pipeline
from src.PDF_pipeline.pipeline import run_pipeline

# Standard pipeline
std_result, std_json = run_pipeline(pdf_path="resume.pdf")

# Robust pipeline
robust_result, robust_json = robust_pipeline(path="resume.pdf")

# Compare
print("Standard sections:", [s['section'] for s in std_result['sections']])
print("Robust sections:", [s['section'] for s in robust_result['sections']])
```

## Integration with Existing Code

### Drop-in Replacement

```python
# Old code
from src.PDF_pipeline.pipeline import run_pipeline
result, simplified = run_pipeline(pdf_path="resume.pdf")

# New code (same interface)
from src.ROBUST_pipeline.pipeline import robust_pipeline
result, simplified = robust_pipeline(path="resume.pdf")
```

### Using with Batch Processor

```python
# Modify your existing batch processor
from src.ROBUST_pipeline.pipeline import robust_pipeline

def process_resume_file(file_path):
    # Replace your old pipeline call
    result, simplified = robust_pipeline(
        path=file_path,
        use_ocr=True,
        verbose=False
    )
    return result
```

## Next Steps

1. **Test on your resume collection**: Run `test_robust.py` on various resumes
2. **Compare accuracy**: Check which pipeline finds more sections correctly
3. **Tune thresholds**: Adjust `AdaptiveThresholds` for your document types
4. **Add custom sections**: Edit `SECTIONS` dict in `segment_sections.py`
5. **Batch process**: Use `batch_process.py` for production runs

## Getting Help

- Check `README.md` for detailed documentation
- Review `test_robust.py` for examples
- Examine output files to understand structure
- Enable `verbose=True` to see processing steps

## Performance Benchmarks

Typical processing times (Intel i7, 16GB RAM, no GPU):

- **Simple resume** (1 page, single column): 1-2 seconds
- **Standard resume** (2 pages, some formatting): 3-5 seconds
- **Complex resume** (2 pages, multi-column): 5-8 seconds
- **Scanned resume** (2 pages, OCR needed): 8-15 seconds

Batch processing (100 resumes):

- **4 workers**: ~10-15 minutes
- **8 workers**: ~6-10 minutes

With GPU (for OCR):

- **Speed improvement**: 2-3x faster
- **Recommended**: NVIDIA GPU with CUDA support
