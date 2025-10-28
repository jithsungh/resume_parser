# 📄 Resume Layout Labeling System

**Build high-quality labeled datasets for resume layout classification with automatic feature extraction and interactive labeling.**

---

## ✨ Features

- 🖼️ **PDF Rendering**: High-quality visualization with adjustable zoom
- 🤖 **Auto Feature Extraction**: 9 numeric features computed automatically
- 🎯 **One-Click Labeling**: Simple Type 1/2/3 classification
- 💾 **Auto-Save**: Progress persisted to CSV and JSON
- 📊 **Progress Tracking**: Real-time statistics and completion status
- ⚡ **Smart Navigation**: Auto-skip to next unlabeled PDF
- 🔍 **Feature Inspection**: Debug computed features in real-time

---

## 🚀 Quick Start

### Option 1: Use Start Script (Recommended)

**Windows:**

```bash
# Double-click or run in terminal
start_labeling.bat
```

**Linux/Mac:**

```bash
chmod +x start_labeling.sh
./start_labeling.sh
```

### Option 2: Manual Start

```bash
# Install dependencies
pip install streamlit PyMuPDF pandas numpy pillow

# Test feature extraction
python test_labeling.py

# Start labeling app
streamlit run label_resumes.py
```

Then open **http://localhost:8501** in your browser.

---

## 📋 Usage

### 1. Configure Settings

In the sidebar:

- **PDF Directory**: Path to your resume PDFs (default: `./freshteams_resume/Resumes`)
- **Dataset Output**: Where to save labels (default: `./dataset.csv`)

### 2. Label Resumes

For each PDF:

1. **Review** the rendered PDF (left panel)
2. **Check** computed features (right panel)
3. **Click** Type 1, Type 2, or Type 3 button
4. **Auto-advance** to next unlabeled PDF

### 3. Track Progress

- Sidebar shows: Total PDFs, Labeled count, Remaining
- Progress bar updates in real-time
- Can stop/resume anytime (progress is saved)

---

## 🏷️ Layout Types

| Type       | Name           | Description                      | Indicators                                          |
| ---------- | -------------- | -------------------------------- | --------------------------------------------------- |
| **Type 1** | Single Column  | Traditional top-to-bottom layout | `num_columns=1`, high `full_width_line_ratio`       |
| **Type 2** | Multi-Column   | Clean 2-column throughout        | `coverage_gutter>0.7`, low `full_width_line_ratio`  |
| **Type 3** | Hybrid/Complex | Mixed single + multi-column      | `coverage_gutter>0.7`, high `full_width_line_ratio` |

---

## 📊 Extracted Features

| Feature                  | Description                   | Range   |
| ------------------------ | ----------------------------- | ------- |
| `num_columns`            | Detected column count         | 1-2     |
| `mean_y_overlap`         | Average vertical text overlap | 0.0-1.0 |
| `coverage_gutter`        | Empty gutter coverage         | 0.0-1.0 |
| `full_width_line_ratio`  | Ratio of full-width lines     | 0.0-1.0 |
| `valley_depth_ratio`     | Histogram valley depth        | 0.0-1.0 |
| `horizontal_lines_count` | Full-width line count         | 0+      |
| `header_fraction`        | Header section size           | 0.0-1.0 |
| `avg_word_width_ratio`   | Average word width            | 0.0-1.0 |
| `line_density_variance`  | Text distribution variance    | 0+      |

---

## 📁 Output Format

### CSV (`dataset.csv`)

```csv
filename,num_columns,mean_y_overlap,coverage_gutter,full_width_line_ratio,valley_depth_ratio,horizontal_lines_count,header_fraction,avg_word_width_ratio,line_density_variance,label
resume1.pdf,2,0.1234,0.8521,0.0456,0.0234,1,0.0678,0.0123,45.67,2
resume2.pdf,1,0.0892,0.1234,0.4567,0.9876,15,0.0000,0.0234,23.45,1
```

### JSON (`dataset.json`)

```json
[
  {
    "filename": "resume1.pdf",
    "num_columns": 2,
    "mean_y_overlap": 0.1234,
    "coverage_gutter": 0.8521,
    "label": 2
  }
]
```

---

## 🛠️ Components

### 1. `resume_feature_extractor.py`

Core feature extraction engine:

- `ResumeFeatureExtractor`: Main extraction class
- `ResumeFeatures`: Feature container dataclass
- Methods: `extract_words_and_bbox()`, `compute_features()`

### 2. `label_resumes.py`

Streamlit web application:

- `ResumeLabelingApp`: Main app controller
- Interactive PDF viewer
- Feature display and debugging
- Label persistence

### 3. `test_labeling.py`

Standalone testing utility:

- Test feature extraction on single PDF
- Validate feature computation
- Debug extraction pipeline

### 4. `LABELING_GUIDE.md`

Comprehensive documentation:

- Detailed usage instructions
- Feature interpretation guide
- Troubleshooting tips
- Advanced usage examples

---

## 🔧 Advanced Usage

### Customize Feature Extraction

```python
from resume_feature_extractor import ResumeFeatureExtractor

extractor = ResumeFeatureExtractor(verbose=True)

# Adjust parameters
extractor.y_tolerance = 10  # Line grouping tolerance
extractor.full_width_fraction = 0.8  # Full-width threshold
extractor.gutter_zero_max = 0.05  # Gutter detection sensitivity
extractor.band_count = 80  # Bands for gutter analysis

# Extract features
words, width, height = extractor.extract_words_and_bbox("resume.pdf")
features = extractor.compute_features(words, width, height)
```

### Batch Feature Extraction

```python
from pathlib import Path
from resume_feature_extractor import ResumeFeatureExtractor
import pandas as pd

extractor = ResumeFeatureExtractor()
results = []

for pdf_path in Path("./resumes").glob("*.pdf"):
    words, w, h = extractor.extract_words_and_bbox(str(pdf_path))
    features = extractor.compute_features(words, w, h)
    results.append({'filename': pdf_path.name, **features.to_dict()})

pd.DataFrame(results).to_csv("features.csv", index=False)
```

### Validate Labeled Dataset

```python
import pandas as pd

df = pd.read_csv('dataset.csv')

# Label distribution
print(df['label'].value_counts())

# Feature statistics
print(df.groupby('label').mean())

# Find potential mislabels
inconsistent = df[
    ((df['label'] == 1) & (df['num_columns'] == 2)) |
    ((df['label'] == 2) & (df['coverage_gutter'] < 0.5))
]
print(f"Potential mislabels: {len(inconsistent)}")
```

---

## 🎯 Tips for Quality Labeling

1. **Review first page only**: Most layout signals visible on page 1
2. **Use feature hints**: Computed features guide classification
3. **Define clear rules**: Document edge case decisions
4. **Take breaks**: Maintain consistency with regular breaks
5. **Validate regularly**: Check for mislabels every 50-100 PDFs
6. **Use zoom**: Increase zoom for detailed inspection

---

## 🐛 Troubleshooting

| Issue              | Solution                                    |
| ------------------ | ------------------------------------------- |
| PDF won't render   | Check PyMuPDF installation, reduce zoom     |
| Features fail      | Verify PDF has text (not scanned image)     |
| Dataset not saving | Check write permissions, verify path        |
| Slow performance   | Reduce zoom, disable feature display        |
| Missing PDFs       | Check directory path, verify .pdf extension |

---

## 📈 Next Steps

Once you have 100+ labeled examples:

1. **Train classifier**: Use features to train ML model
2. **Evaluate**: Test on held-out validation set
3. **Integrate**: Replace manual labeling with predictions
4. **Monitor**: Track model performance on new PDFs
5. **Iterate**: Add more features if needed

---

## 📚 Documentation

- **Quick Start**: This README
- **Full Guide**: [LABELING_GUIDE.md](LABELING_GUIDE.md)
- **Feature Details**: See `ResumeFeatureExtractor` docstrings
- **API Reference**: See class and method documentation

---

## 🎉 Examples

### Example 1: Quick Test

```bash
python test_labeling.py freshteams_resume/Resumes/1.pdf
```

### Example 2: Label 10 PDFs

```bash
streamlit run label_resumes.py
# Label first 10 PDFs, check dataset.csv
```

### Example 3: Resume Labeling

```bash
# Stop app (Ctrl+C)
# Resume from where you left off
streamlit run label_resumes.py
```

---

## 📞 Support

For detailed documentation, see [LABELING_GUIDE.md](LABELING_GUIDE.md)

For feature extraction issues, run:

```bash
python test_labeling.py your_resume.pdf
```

---

**Happy Labeling! 🚀**

Built with ❤️ using Streamlit, PyMuPDF, and NumPy.
