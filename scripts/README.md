# Scripts Directory

Command-line utilities and tools for resume parsing operations.

## Files

### `batch_folder_process.py` ⭐ **MOST USED**

**Purpose**: Batch process entire folders and export to Excel.

**What it does**:

- Finds all PDF/DOCX files in a folder (recursive)
- Processes them in parallel with progress bar
- Exports sections to a clean Excel spreadsheet
- One row per resume, one column per section

**Usage**:

```bash
# Basic usage
python scripts/batch_folder_process.py --folder "resumes/" --output "results.xlsx"

# With options
python scripts/batch_folder_process.py \
    --folder "resumes/" \
    --output "outputs/batch_results.xlsx" \
    --workers 8 \
    --no-recursive \
    --quiet
```

**Options**:

- `--folder`: Path to folder containing resumes (required)
- `--output`: Output Excel file path (default: outputs/batch_results.xlsx)
- `--workers`: Number of parallel workers (default: 4)
- `--no-recursive`: Don't search subfolders
- `--quiet`: No progress output

**Output Excel Format**:

```
| File Name    | Contact Info | Summary | Skills | Experience | ... |
|--------------|--------------|---------|--------|------------|-----|
| resume1.pdf  | John Doe...  | ...     | ...    | ...        | ... |
| resume2.docx | Jane Smith.. | ...     | ...    | ...        | ... |
```

**Performance**:

- With 4 workers: ~2-5 files/second
- With 8 workers: ~3-8 files/second (if you have CPU cores)

---

### `test_pipeline.py`

**Purpose**: Test and verify the complete pipeline works.

**What it does**:

- Tests single resume parsing
- Tests batch processing
- Validates all components
- Checks for common issues

**Usage**:

```bash
python scripts/test_pipeline.py
```

**Output**:

```
============================================================
TEST 1: Single Resume Parsing
============================================================
Parsing: freshteams_resume/Resumes/Azid.pdf
✓ Success: True
  Strategy: pdf_histogram
  Sections found: 8
  Processing time: 1.23s

============================================================
TEST 2: Batch Processing
============================================================
Processing 5 test files...
Progress: 100%|██████████| 5/5 [00:06<00:00,  1.2s/file]
✓ Batch complete: 5 files processed
  Success rate: 100%
  Avg time: 1.2s/file
```

**When to use**:

- After installation to verify setup
- After making changes to pipeline
- Before processing large batches
- To debug issues

---

### `view_results.py`

**Purpose**: Web-based viewer for parsed resume results.

**What it does**:

- Launches Flask web server
- Displays Excel results in browser
- Shows original PDF side-by-side with extracted sections
- Interactive navigation and search

**Usage**:

```bash
python scripts/view_results.py

# Then open browser to:
# http://localhost:5000
```

**Features**:

- **File browser**: Select resume from list
- **Side-by-side view**: Original PDF + extracted sections
- **Section highlighting**: Click section to highlight in PDF
- **Search**: Find specific resumes or content
- **Export**: Download individual results as JSON

**Requirements**:

- Flask installed: `pip install flask`
- Excel file from batch_folder_process.py
- Original PDF files available

**Configuration**:
Edit top of `view_results.py`:

```python
DEFAULT_XLSX = "outputs/batch_results.xlsx"
PORT = 5000
```

---

### `index.html`

**Purpose**: Frontend for view_results.py web interface.

**What it is**:

- HTML/CSS/JavaScript single-page app
- Works with view_results.py Flask backend
- Responsive design for desktop and tablet

**Don't edit** unless customizing the web interface.

---

## Workflow

### Typical Usage Flow:

1. **Test first**:

   ```bash
   python scripts/test_pipeline.py
   ```

2. **Batch process**:

   ```bash
   python scripts/batch_folder_process.py \
       --folder "path/to/resumes/" \
       --output "outputs/results.xlsx" \
       --workers 4
   ```

3. **View results**:

   ```bash
   python scripts/view_results.py
   # Open http://localhost:5000
   ```

4. **Review and validate** in browser

5. **Use Excel** for further analysis

---

## Common Scenarios

### Process new batch of resumes:

```bash
python scripts/batch_folder_process.py \
    --folder "new_applicants/" \
    --output "outputs/new_batch.xlsx" \
    --workers 8
```

### Process specific subfolder only:

```bash
python scripts/batch_folder_process.py \
    --folder "resumes/engineering/" \
    --output "outputs/engineering.xlsx" \
    --no-recursive
```

### Quick test on small set:

```bash
# Edit test_pipeline.py to point to your test files
python scripts/test_pipeline.py
```

### Debug single file:

```python
python -c "
from src.core.unified_pipeline import UnifiedPipeline
pipeline = UnifiedPipeline()
result = pipeline.parse('problem_resume.pdf', verbose=True)
print(result)
"
```

---

## Performance Tips

### Optimize Workers

```bash
# Check CPU cores
python -c "import os; print(f'CPU cores: {os.cpu_count()}')"

# Use 75% of cores for batch processing
# e.g., 8 cores → use --workers 6
```

### Large Batches

For 100+ resumes:

```bash
# Process in chunks to avoid memory issues
python scripts/batch_folder_process.py \
    --folder "resumes/batch1/" \
    --output "outputs/batch1.xlsx" \
    --workers 6

python scripts/batch_folder_process.py \
    --folder "resumes/batch2/" \
    --output "outputs/batch2.xlsx" \
    --workers 6
```

### Quiet Mode

For cron jobs or background processing:

```bash
python scripts/batch_folder_process.py \
    --folder "resumes/" \
    --output "results.xlsx" \
    --quiet \
    >> batch_process.log 2>&1
```

---

## Troubleshooting

### Issue: batch_folder_process.py not finding files

**Check**:

```bash
# Verify folder exists
ls "path/to/folder/"

# Check for PDF/DOCX files
find "path/to/folder/" -name "*.pdf" -o -name "*.docx"
```

### Issue: view_results.py can't find Excel file

**Solution**:

- Check Excel file path in view_results.py
- Ensure Excel file exists
- Use absolute path if needed

### Issue: Slow processing

**Solutions**:

- Increase workers: `--workers 8`
- Check if OCR is being triggered (much slower)
- Reduce DPI for OCR: Edit pipeline config

### Issue: Import errors

**Solution**:

```bash
# Make sure you're in project root
cd c:\Users\jithsungh.v\projects\resume_parser

# Run from root, not from scripts/
python scripts/batch_folder_process.py --folder "resumes/"
```

---

## Advanced Usage

### Custom Section Configuration

```python
# Edit before running
from src.core.unified_pipeline import UnifiedPipeline

pipeline = UnifiedPipeline(
    config_path="custom_sections.json",
    enable_learning=True
)

# Then use in batch_folder_process.py
```

### Programmatic Usage

Instead of command-line, use Python:

```python
import sys
sys.path.insert(0, ".")

from scripts.batch_folder_process import process_folder

process_folder(
    folder_path="resumes/",
    output_excel="results.xlsx",
    max_workers=4,
    recursive=True,
    verbose=True
)
```

### Export to Different Formats

Modify batch_folder_process.py to export JSON/CSV:

```python
# In save_to_excel(), add:
import json
with open("results.json", "w") as f:
    json.dump(results, f, indent=2)
```

---

## Integration

These scripts are designed to be:

- **Standalone**: Run from command-line
- **Importable**: Use as Python modules
- **Customizable**: Easy to modify for specific needs
- **Production-ready**: Handle errors, logging, progress
