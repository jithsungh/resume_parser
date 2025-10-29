# Advanced Resume Labeling Tool - User Guide

## 🚀 Features

### Fast & Efficient
- **Precomputed Features**: All features are extracted at startup for instant labeling
- **Vectorized Operations**: NumPy-based computations for speed
- **Smart Caching**: Features cached in memory for quick access

### Enhanced Feature Set (25+ Features)
**Basic Features:**
- `num_columns`, `mean_y_overlap`, `coverage_gutter`
- `full_width_line_ratio`, `valley_depth_ratio`
- `horizontal_lines_count`, `header_fraction`
- `avg_word_width_ratio`, `line_density_variance`

**Peak Characteristics:**
- `peak_count`: Number of significant peaks in X-density
- `peak_widths`: Width of each peak (FWHM)
- `peak_heights`: Height of each peak
- `peak_separation`: Distance between primary peaks

**Valley Characteristics:**
- `valley_count`: Number of valleys
- `valley_depths`: Depth of each valley
- `valley_widths`: Width at half-depth
- `valley_position`: Normalized X position of primary valley

**Additional Discriminative Features:**
- `line_spacing_variance`: Variance in line spacing
- `text_density`: Words per page area
- `max_line_width_ratio`, `min_line_width_ratio`
- `width_bimodality`: Measure of two-column distribution

### Validation & Error Detection
- Automatic validation of all features
- Range checking (0-1 for ratios, positive values)
- Red highlighting for invalid/suspicious values
- Yellow warnings for questionable patterns
- Validation error messages in feature table

### Interactive GUI (Tkinter)
- **PDF Viewer**: High-quality rendering on left panel
- **Feature Inspector**: Scrollable table with color-coded validation
- **Quick Labeling**: Three prominent buttons (Type 1/2/3)
- **Navigation**: Previous, Next, Skip buttons
- **Progress Tracking**: Real-time progress bar and statistics
- **Keyboard Shortcuts**: 
  - `1`, `2`, `3` → Label as Type 1/2/3
  - `←`, `→` → Navigate Previous/Next
  - `Space` → Skip

### Data Persistence
- Saves to both CSV and JSON formats
- Appends new labels without overwriting
- Allows re-labeling (updates existing entries)
- Tracks labeled files to resume sessions
- Timestamped entries

---

## 📦 Installation

### Prerequisites
```bash
pip install PyMuPDF pandas numpy Pillow
```

All dependencies should already be in your `requirements.txt`.

---

## 🎯 Quick Start

### Windows
```cmd
start_advanced_labeling.bat
```

### Linux/Mac
```bash
chmod +x start_advanced_labeling.sh
./start_advanced_labeling.sh
```

### Manual Start
```bash
# Activate environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate.bat  # Windows

# Run tool
python advanced_labeling_tool.py --pdf-dir Resumes --output labeled_dataset.csv
```

---

## 💡 Usage Guide

### Main Workflow

1. **Startup**
   - Tool scans PDF directory
   - Precomputes features for all PDFs (may take 1-2 minutes)
   - Automatically jumps to first unlabeled PDF

2. **Labeling**
   - View PDF on left panel
   - Inspect features on right panel
   - Check validation status (✓ OK, ⚠ Warning, ✗ Error)
   - Click Type 1/2/3 button (or press 1/2/3 key)
   - Automatically moves to next unlabeled PDF

3. **Navigation**
   - **Next (→)**: Move forward (labeled or unlabeled)
   - **Previous (←)**: Move backward
   - **Skip (Space)**: Skip to next unlabeled without labeling

4. **Completion**
   - Popup shows completion message
   - Summary of label distribution
   - Dataset saved to CSV and JSON

### Feature Interpretation

**Type 1: Single Column**
- `num_columns` = 1
- `coverage_gutter` < 0.7
- `peak_count` = 1 (single central peak)
- `full_width_line_ratio` > 0.6

**Type 2: Multi-Column (Clean)**
- `num_columns` = 2
- `coverage_gutter` ≥ 0.7
- `peak_count` = 2 (two distinct peaks)
- `valley_depth_ratio` < 0.3 (deep valley)
- `width_bimodality` > 1.0

**Type 3: Hybrid/Complex**
- `num_columns` = 2 but mixed layout
- `horizontal_lines_count` ≥ 3 (full-width headers)
- `header_fraction` > 0.05
- Mixed peak/valley patterns
- Variable line widths

### Validation Warnings

**Red (Error):**
- Values out of valid range (e.g., ratio > 1.0)
- Negative values where not allowed
- Feature extraction failed

**Yellow (Warning):**
- Suspicious combinations (e.g., num_columns=2 but low gutter coverage)
- Borderline values
- Inconsistent signals

**Green (OK):**
- All values in valid range
- Consistent feature patterns

---

## 📊 Output Format

### CSV Columns
```
filename, num_columns, mean_y_overlap, coverage_gutter, 
full_width_line_ratio, valley_depth_ratio, horizontal_lines_count,
header_fraction, avg_word_width_ratio, line_density_variance,
peak_count, peak_widths, peak_heights, peak_separation,
valley_count, valley_depths, valley_widths, valley_position,
line_spacing_variance, text_density, max_line_width_ratio,
min_line_width_ratio, width_bimodality, is_valid, 
validation_errors, label, labeled_at
```

### List Features (CSV)
Lists are stored as comma-separated strings:
- `peak_widths`: "0.15,0.18"
- `valley_depths`: "0.05,0.12"

### JSON Format
Full structured data with proper arrays:
```json
{
  "filename": "resume.pdf",
  "peak_widths": [0.15, 0.18],
  "valley_depths": [0.05, 0.12],
  "label": 2
}
```

---

## 🔧 Advanced Options

### Custom PDF Directory
```bash
python advanced_labeling_tool.py --pdf-dir /path/to/pdfs
```

### Custom Output Path
```bash
python advanced_labeling_tool.py --output my_labels.csv
```

### Both Options
```bash
python advanced_labeling_tool.py --pdf-dir Resumes --output dataset_v2.csv
```

---

## 🐛 Troubleshooting

### "No PDFs found"
- Check that PDF directory exists
- Verify path is correct
- Ensure PDFs are in directory or subdirectories

### "Feature extraction failed"
- Check PDF is not corrupted
- Verify PDF contains text (not scanned image)
- Check logs in `labeling_tool.log`

### Slow startup
- Normal for large datasets (100+ PDFs)
- Features are precomputed once at startup
- Subsequent labeling is instant

### GUI not responsive
- Wait for feature preloading to complete
- Check console for progress messages
- See `labeling_tool.log` for errors

### Invalid features (red warnings)
- Review PDF manually
- May indicate extraction issues
- Can still label, but verify correctness

---

## 📈 Performance Tips

1. **Batch Processing**: Label similar resumes together for consistency
2. **Use Keyboard**: Shortcuts are faster than mouse clicks
3. **Skip Problematic**: Skip PDFs with extraction errors, review later
4. **Regular Saves**: Labels auto-save, but check CSV periodically
5. **Resume Sessions**: Tool remembers labeled files, can stop/restart

---

## 📝 Logging

All activity logged to `labeling_tool.log`:
- Feature extraction status
- Validation warnings
- Labeling actions
- Errors and exceptions

---

## 🎓 Best Practices

### Labeling Guidelines

**Type 1 Indicators:**
- Text flows top-to-bottom in single column
- No vertical gutter/gap
- Headers span full width naturally

**Type 2 Indicators:**
- Clear vertical split (gutter)
- Consistent two-column layout throughout
- Minimal full-width sections

**Type 3 Indicators:**
- Mixed layout: headers full-width, content in columns
- Multiple full-width sections interspersed
- Variable column usage

### Quality Checks
- Review validation status before labeling
- Compare features across similar resumes
- Re-label if initial choice seems wrong (tool handles updates)
- Use Skip for ambiguous cases, review later

---

## 🔍 Example Session

```
$ python advanced_labeling_tool.py

INFO - Found 228 PDF files
INFO - Preloading features for all PDFs...
INFO - Preloaded 10/228 PDFs
INFO - Preloaded 20/228 PDFs
...
INFO - Preloading complete!

[GUI opens, showing first unlabeled PDF]

Progress: Labeled 0/228 (0.0%)
Current File: Ajinkya_DevOps_Engineer_CV.pdf [1/228]

[Features displayed with validation status]
num_columns: 2 ✓
coverage_gutter: 0.8667 ✓
peak_count: 2 ✓
valley_depth_ratio: 0.0000 ✓

[Press '1' to label as Type 1]

INFO - Labeled Ajinkya_DevOps_Engineer_CV.pdf as Type 1

[Automatically moves to next unlabeled PDF]
```

---

## 📚 Additional Resources

- Feature extraction details: See `FeatureExtractor` class
- Validation rules: See `_validate_features` method
- GUI customization: Modify `_create_gui` method

---

## 🤝 Support

Check logs for errors:
```bash
tail -f labeling_tool.log
```

Common issues documented in code comments and docstrings.
