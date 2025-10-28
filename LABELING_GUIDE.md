# Resume Labeling System Documentation

## 🎯 Overview

A complete system for building labeled resume layout datasets with automatic feature extraction and interactive PDF labeling interface.

## 📦 Components

### 1. **ResumeFeatureExtractor** (`resume_feature_extractor.py`)

Extracts 9 numeric features from PDF resumes:

| Feature                  | Description                               | Type  |
| ------------------------ | ----------------------------------------- | ----- |
| `num_columns`            | Number of detected columns (1 or 2)       | int   |
| `mean_y_overlap`         | Average vertical overlap between words    | float |
| `coverage_gutter`        | Fraction of page with empty gutter        | float |
| `full_width_line_ratio`  | Ratio of lines spanning >75% width        | float |
| `valley_depth_ratio`     | Deepest histogram valley depth            | float |
| `horizontal_lines_count` | Count of full-width lines                 | int   |
| `header_fraction`        | Fraction of page before gutter stabilizes | float |
| `avg_word_width_ratio`   | Average word width / page width           | float |
| `line_density_variance`  | Variance in words per line                | float |

### 2. **Interactive Labeling App** (`label_resumes.py`)

Streamlit-based web interface for manual labeling with:

- PDF rendering with adjustable zoom
- Automatic feature extraction and display
- One-click labeling (Type 1/2/3)
- Progress tracking and persistence
- Auto-skip to next unlabeled PDF

### 3. **Test Script** (`test_labeling.py`)

Standalone feature extraction tester for validation.

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install streamlit PyMuPDF pandas numpy pillow

# Or if you have requirements.txt
pip install -r requirements.txt
```

### Running the Labeling App

```bash
# Start Streamlit app (default port 8501)
streamlit run label_resumes.py

# Custom port
streamlit run label_resumes.py --server.port 8502

# Run in headless mode (for remote servers)
streamlit run label_resumes.py --server.headless true
```

### Testing Feature Extraction

```bash
# Test with automatic PDF discovery
python test_labeling.py

# Test with specific PDF
python test_labeling.py path/to/resume.pdf
```

## 📖 Usage Guide

### Configuration

1. **PDF Directory**: Set the path to your resume PDFs

   - Default: `./freshteams_resume/Resumes`
   - Can be changed in sidebar or code

2. **Dataset Output**: Choose where to save labeled data
   - Default: `./dataset.csv`
   - Also saves JSON version: `./dataset.json`

### Labeling Workflow

1. **Start the app**: Run `streamlit run label_resumes.py`
2. **View PDF**: First page rendered automatically with zoom control
3. **Review features**: Check computed features in right panel
4. **Assign label**: Click Type 1, Type 2, or Type 3 button
5. **Auto-advance**: App automatically moves to next unlabeled PDF
6. **Progress tracking**: Sidebar shows completion status

### Label Types

| Type       | Description    | Characteristics                              |
| ---------- | -------------- | -------------------------------------------- |
| **Type 1** | Single Column  | Traditional layout, text flows top-to-bottom |
| **Type 2** | Multi-Column   | Clean 2-column throughout, consistent gutter |
| **Type 3** | Hybrid/Complex | Mixed layout, full-width headers + columns   |

### Navigation

- **Type 1/2/3 Buttons**: Label and auto-advance
- **Previous/Next**: Manual navigation
- **Skip to Next Unlabeled**: Jump to next incomplete PDF
- **Zoom Slider**: Adjust PDF preview size (1.0x - 3.0x)

### Dataset Format

**CSV Output** (`dataset.csv`):

```csv
filename,num_columns,mean_y_overlap,coverage_gutter,full_width_line_ratio,valley_depth_ratio,horizontal_lines_count,header_fraction,avg_word_width_ratio,line_density_variance,label
resume1.pdf,2,0.1234,0.8521,0.0456,0.0234,1,0.0678,0.0123,45.67,2
resume2.pdf,1,0.0892,0.1234,0.4567,0.9876,15,0.0000,0.0234,23.45,1
...
```

**JSON Output** (`dataset.json`):

```json
[
  {
    "filename": "resume1.pdf",
    "num_columns": 2,
    "mean_y_overlap": 0.1234,
    "coverage_gutter": 0.8521,
    "full_width_line_ratio": 0.0456,
    "valley_depth_ratio": 0.0234,
    "horizontal_lines_count": 1,
    "header_fraction": 0.0678,
    "avg_word_width_ratio": 0.0123,
    "line_density_variance": 45.67,
    "label": 2
  }
]
```

## 🔧 Advanced Usage

### Custom Configuration

Edit `label_resumes.py` to customize:

```python
# Change default PDF directory
default_dir = "./your/pdf/directory"

# Change dataset output path
dataset_path = "./custom_dataset.csv"

# Adjust feature extractor parameters
extractor = ResumeFeatureExtractor(verbose=True)
extractor.y_tolerance = 10  # Line grouping tolerance
extractor.full_width_fraction = 0.8  # Full-width threshold
extractor.band_count = 80  # Gutter analysis bands
```

### Feature Extraction API

```python
from resume_feature_extractor import ResumeFeatureExtractor

# Initialize extractor
extractor = ResumeFeatureExtractor(verbose=True)

# Extract features from PDF
words, width, height = extractor.extract_words_and_bbox("resume.pdf")
features = extractor.compute_features(words, width, height)

# Access feature values
print(f"Columns: {features.num_columns}")
print(f"Gutter: {features.coverage_gutter}")

# Export to dict
feature_dict = features.to_dict()
```

### Batch Processing

```python
from pathlib import Path
from resume_feature_extractor import ResumeFeatureExtractor
import pandas as pd

extractor = ResumeFeatureExtractor()
results = []

for pdf_path in Path("./resumes").glob("*.pdf"):
    words, w, h = extractor.extract_words_and_bbox(str(pdf_path))
    features = extractor.compute_features(words, w, h)

    results.append({
        'filename': pdf_path.name,
        **features.to_dict()
    })

df = pd.DataFrame(results)
df.to_csv("features_only.csv", index=False)
```

## 📊 Feature Interpretation

### Column Detection Features

- **num_columns**: 1 = single, 2 = multi-column
- **coverage_gutter**: High (>0.7) = strong column separation
- **valley_depth_ratio**: Low (<0.1) = clear gutter

### Layout Structure Features

- **full_width_line_ratio**: High (>0.3) = many full-width sections
- **horizontal_lines_count**: Count of headers/titles
- **header_fraction**: Where columns start (0 = top, 1 = bottom)

### Text Distribution Features

- **mean_y_overlap**: High = text aligned horizontally
- **avg_word_width_ratio**: Average relative word size
- **line_density_variance**: High = uneven text distribution

## 🎯 Tips for Labeling

1. **Focus on first page**: Most layout signals are visible on page 1
2. **Use zoom**: Increase zoom (2.0x-3.0x) for detailed inspection
3. **Check features**: Computed features provide helpful hints
4. **Consistent criteria**: Define clear rules for edge cases
5. **Take breaks**: Labeling fatigue affects consistency
6. **Resume anytime**: Progress is auto-saved, safe to close/reopen

## 🐛 Troubleshooting

### PDF Won't Render

- Check PDF is not corrupted
- Verify PyMuPDF installed: `pip install PyMuPDF`
- Try reducing zoom level

### Feature Extraction Fails

- Ensure PDF contains text (not scanned image)
- Check PDF is not password-protected
- Verify src/core/word_extractor.py exists

### Dataset Not Saving

- Check write permissions for output directory
- Verify dataset path is valid
- Look for error messages in terminal

### App Performance Issues

- Reduce zoom level (lower = faster)
- Disable "Show Computed Features" in sidebar
- Close other browser tabs
- Use smaller PDF directory batches

## 📝 Example Workflow

```bash
# 1. Test feature extraction
python test_labeling.py freshteams_resume/Resumes/1.pdf

# 2. Start labeling app
streamlit run label_resumes.py

# 3. In browser (http://localhost:8501):
#    - Review PDF
#    - Check computed features
#    - Click Type 1/2/3
#    - Repeat for all PDFs

# 4. Check progress
cat dataset.csv | wc -l  # Count labeled resumes

# 5. View dataset
python -c "import pandas as pd; print(pd.read_csv('dataset.csv'))"
```

## 🔍 Validation

After labeling, validate your dataset:

```python
import pandas as pd

df = pd.read_csv('dataset.csv')

# Check label distribution
print(df['label'].value_counts())

# Check feature ranges
print(df.describe())

# Find potential mislabels
# Type 1 should have num_columns=1
type1_multicolumn = df[(df['label'] == 1) & (df['num_columns'] == 2)]
print(f"Potential mislabels: {len(type1_multicolumn)}")
```

## 🚀 Next Steps

Once you have a labeled dataset:

1. **Train classifier**: Use features to train ML model
2. **Validate model**: Test on held-out PDFs
3. **Integrate**: Replace manual classification with model predictions
4. **Iterate**: Add more features if needed

## 📞 Support

For issues or questions:

- Check feature extraction with `test_labeling.py`
- Review computed features in app sidebar
- Verify PDF quality and text extraction
- Check console output for error messages

---

**Happy Labeling! 🎉**
