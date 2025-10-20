# IMG Pipeline - OCR for Scanned Documents

Handles scanned PDFs and image-based resumes using Optical Character Recognition (OCR).

## Purpose

Extract text from scanned documents, images, and PDFs that don't contain selectable text.

## Key File

### `pipeline.py`

**Main entry point** for OCR-based extraction.

**What it does**:

- Converts PDF pages to images
- Uses EasyOCR for text recognition
- Extracts text with bounding box coordinates
- Preserves layout and reading order
- Handles poor quality scans with preprocessing

## Technology Stack

### EasyOCR

We use **EasyOCR** (not Tesseract) because:

- ✅ Better accuracy out-of-the-box
- ✅ No installation hassles (pip install only)
- ✅ Supports 80+ languages
- ✅ Deep learning based (more robust)
- ✅ GPU acceleration support

### Image Preprocessing

Improves OCR accuracy:

- **Binarization**: Convert to black & white
- **Denoising**: Remove background noise
- **Deskewing**: Straighten rotated text
- **Contrast enhancement**: Make text clearer

## How It Works

### 1. PDF to Image Conversion

```python
# Convert each PDF page to high-res image
pdf_document = fitz.open("scanned_resume.pdf")
page = pdf_document[0]
pix = page.get_pixmap(dpi=300)  # High DPI for quality
image = PIL.Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
```

### 2. Image Preprocessing (Optional)

```python
# Convert to grayscale
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# Binarization (black & white)
_, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

# Denoising
denoised = cv2.fastNlMeansDenoising(binary)
```

### 3. OCR Text Extraction

```python
import easyocr

reader = easyocr.Reader(['en'], gpu=True)  # English, with GPU
results = reader.readtext(image)

# Results format:
# [
#   ([[x1,y1], [x2,y2], [x3,y3], [x4,y4]], 'TEXT', confidence),
#   ...
# ]
```

### 4. Layout Reconstruction

- Sort detected text by Y-coordinate (top to bottom)
- Group into lines with same Y-coordinate
- Order left-to-right within each line
- Reconstruct reading order

### 5. Section Detection

Same as PDF pipeline:

- Keyword matching
- Font size estimation (from bounding box height)
- Spacing analysis
- Semantic matching

## Usage

### Basic OCR

```python
from src.IMG_pipeline.pipeline import run_pipeline_ocr

result, simplified_json = run_pipeline_ocr(
    "scanned_resume.pdf",
    dpi=300,  # Resolution for PDF->image conversion
    gpu=True,  # Use GPU if available
    verbose=True
)
```

### High-Quality OCR

```python
result, simplified_json = run_pipeline_ocr(
    "poor_quality_scan.pdf",
    dpi=400,  # Higher DPI for better quality
    gpu=True,
    preprocess=True,  # Enable image preprocessing
    languages=['en'],  # Specify languages
    verbose=True
)
```

### Multi-Language Support

```python
# Support English and French
result, simplified_json = run_pipeline_ocr(
    "multilingual_resume.pdf",
    languages=['en', 'fr'],
    gpu=False,
    verbose=True
)
```

## Configuration

Key parameters:

```python
dpi: int = 300
    # Resolution for PDF to image conversion
    # Higher = better quality but slower
    # Recommended: 300 (good balance), 400 (high quality)

gpu: bool = False
    # Use GPU acceleration (much faster)
    # Requires CUDA-capable GPU

preprocess: bool = False
    # Enable image preprocessing
    # Useful for poor quality scans

languages: list = ['en']
    # OCR languages to detect
    # See EasyOCR docs for full list

min_confidence: float = 0.5
    # Minimum confidence to accept detected text
    # Lower = more text but more errors
```

## Performance

| Setup        | Speed per Page | Accuracy |
| ------------ | -------------- | -------- |
| CPU, 300 DPI | ~5-8 seconds   | Good     |
| CPU, 400 DPI | ~8-12 seconds  | Better   |
| GPU, 300 DPI | ~1-3 seconds   | Good     |
| GPU, 400 DPI | ~2-5 seconds   | Better   |

**Recommendation**: Use GPU if available, 300 DPI for speed, 400 DPI for quality.

## When to Use

OCR pipeline is automatically triggered when:

- PDF has no selectable text (scanned)
- PDF extraction yields very little text
- Image files (.jpg, .png, .tiff)
- Poor quality digital PDFs with rendering issues

## Advantages

1. **Works on scanned docs**: Only option for scanned PDFs
2. **Image support**: Can process image files directly
3. **Multi-language**: Supports 80+ languages
4. **Robust**: Deep learning handles various fonts and styles

## Limitations

1. **Slower**: 5-10x slower than PDF text extraction
2. **OCR errors**: May misread characters (O→0, l→1, etc.)
3. **Layout challenges**: Complex layouts harder to reconstruct
4. **Handwriting**: Not good with handwritten text
5. **Memory intensive**: High-resolution images use significant RAM

## Common Issues & Solutions

### Issue: Slow performance

**Solution**:

- Use GPU acceleration
- Reduce DPI to 200-250
- Process fewer pages at once

### Issue: Poor accuracy

**Solution**:

- Increase DPI to 400
- Enable preprocessing
- Ensure good scan quality
- Check language setting

### Issue: Wrong reading order

**Solution**:

- OCR gives coordinates - we reconstruct order
- May need manual review for very complex layouts

### Issue: Out of memory

**Solution**:

- Reduce DPI
- Process one page at a time
- Close other applications

## Supported Languages

EasyOCR supports 80+ languages including:

- English, French, German, Spanish, Italian
- Chinese (Simplified & Traditional), Japanese, Korean
- Arabic, Hindi, Russian, Portuguese
- And many more...

Specify in `languages` parameter: `['en', 'fr', 'de']`

## Best Practices

1. **Check if OCR is needed**: Try PDF extraction first
2. **Use GPU**: 3-5x faster than CPU
3. **Optimize DPI**: 300 is usually sufficient
4. **Preprocessing for poor scans**: Only if needed (adds time)
5. **Validate results**: OCR can make mistakes - review output
6. **Batch processing**: Process multiple files together for efficiency

## Integration with Unified Pipeline

The unified pipeline automatically:

1. Detects scanned PDFs
2. Routes to IMG_pipeline
3. Applies optimal DPI setting
4. Validates OCR quality
5. Falls back to other strategies if OCR fails

You don't need to call IMG_pipeline directly - use `UnifiedPipeline`!

## Example Output

```json
{
  "sections": [
    {
      "section": "Experience",
      "lines": [
        "Software Engineer at Google",
        "Jan 2020 - Present",
        "Built scalable systems"
      ]
    }
  ],
  "meta": {
    "extraction_method": "ocr",
    "ocr_engine": "easyocr",
    "avg_confidence": 0.87,
    "total_words": 245,
    "processing_time": 4.2
  }
}
```

## Tips for Better Results

1. **Scan at 300+ DPI** when creating PDFs
2. **High contrast**: Black text on white background best
3. **Straight alignment**: Avoid skewed/rotated pages
4. **Clean scans**: Remove background noise, stains
5. **Standard fonts**: Arial, Times, Calibri work best
6. **Good lighting**: For photo-based resumes
