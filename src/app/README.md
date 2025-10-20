# App Module - Application Layer

The app module contains intelligent decision-making components that analyze documents and select optimal parsing strategies.

## Purpose

Provides the "intelligence" layer between the core orchestrator and the specific parsing pipelines. Makes decisions about HOW to parse based on WHAT the document is.

## Files

### `file_detector.py`

**Purpose**: Detects and validates file types.

**What it does**:

- Identifies file format (PDF, DOCX, DOC, image)
- Validates file accessibility and readability
- Checks for corruption or invalid formats
- Determines if PDF is scanned or digital

**Returns**:

```python
{
    'file_type': 'pdf',  # or 'docx', 'doc', 'image'
    'is_scanned': False,
    'is_valid': True,
    'file_size': 245678,
    'pages': 2
}
```

---

### `layout_analyzer.py`

**Purpose**: Analyzes document layout characteristics.

**What it does**:

- Detects number of columns (1-col, 2-col, 3-col, mixed)
- Identifies layout patterns (simple, complex, hybrid)
- Measures text density and distribution
- Detects tables, images, and special regions
- Assigns complexity score (0.0-1.0)

**Key Metrics**:

- **Column structure**: Single-column, multi-column, or hybrid
- **Text density**: Sparse vs. dense content
- **Complexity score**: Simple (0.0-0.3), Medium (0.3-0.7), Complex (0.7-1.0)
- **Special regions**: Headers, footers, sidebars

**Returns**:

```python
{
    'layout_type': 'multi_column',
    'num_columns': 2,
    'complexity': 0.65,
    'has_tables': True,
    'has_images': False,
    'regions': [...]
}
```

---

### `strategy_selector.py`

**Purpose**: Selects the optimal parsing strategy based on file and layout analysis.

**What it does**:

- Takes file detection + layout analysis results
- Applies decision tree logic to choose best strategy
- Returns ordered list of strategies to try (with fallbacks)
- Considers performance vs. accuracy trade-offs

**Available Strategies**:

1. **PDF_NATIVE**: Fast text extraction for simple digital PDFs
2. **PDF_HISTOGRAM**: Column-aware parsing for multi-column layouts
3. **PDF_REGION**: Advanced region-based parsing for complex layouts
4. **OCR_EASYOCR**: OCR for scanned documents
5. **DOCX_NATIVE**: Direct DOCX parsing

**Decision Logic**:

```
IF scanned:
    → OCR_EASYOCR
ELSE IF DOCX:
    → DOCX_NATIVE
ELSE IF simple layout:
    → PDF_NATIVE (fast)
ELSE IF multi-column:
    → PDF_HISTOGRAM → PDF_REGION (fallback)
ELSE IF complex:
    → PDF_REGION → ROBUST_PIPELINE (fallback)
```

**Returns**:

```python
{
    'primary_strategy': 'pdf_histogram',
    'fallback_strategies': ['pdf_region', 'pdf_native'],
    'reasoning': 'Multi-column layout detected'
}
```

---

### `quality_validator.py`

**Purpose**: Validates parsing quality and triggers fallback if needed.

**What it does**:

- Scores extraction quality (0.0-1.0)
- Checks section coverage and completeness
- Validates text quality (no garbled text)
- Detects common extraction failures
- Decides if fallback strategy should be tried

**Quality Metrics**:

- **Section coverage**: Number of standard sections found
- **Text quality**: Clean text vs. garbled characters
- **Completeness**: All pages processed successfully
- **Structure**: Proper hierarchy and organization

**Quality Thresholds**:

- **Excellent** (0.8-1.0): Perfect extraction, no fallback needed
- **Good** (0.6-0.8): Acceptable quality, may try fallback
- **Poor** (0.4-0.6): Definitely try fallback strategy
- **Failed** (0.0-0.4): Must try alternative approach

**Returns**:

```python
{
    'quality_score': 0.75,
    'is_acceptable': True,
    'should_retry': False,
    'issues': ['Missing contact info'],
    'suggestions': ['Try OCR fallback']
}
```

---

## How They Work Together

```
1. FILE INPUT
      ↓
2. FileDetector
   - Validates file
   - Detects format
   - Checks if scanned
      ↓
3. LayoutAnalyzer
   - Analyzes structure
   - Measures complexity
   - Identifies regions
      ↓
4. StrategySelector
   - Chooses best strategy
   - Provides fallbacks
      ↓
5. PARSING HAPPENS (PDF/DOCX/IMG pipelines)
      ↓
6. QualityValidator
   - Scores result
   - Triggers fallback if poor quality
      ↓
7. RETURN BEST RESULT
```

## Example Flow

**Digital Single-Column PDF**:

```
FileDetector: PDF, digital, simple
LayoutAnalyzer: 1-column, low complexity (0.2)
StrategySelector: PDF_NATIVE (fast!)
QualityValidator: Score 0.9 ✓
Result: Success in <1 second
```

**Scanned Multi-Column PDF**:

```
FileDetector: PDF, scanned ⚠️
LayoutAnalyzer: 2-column, high complexity (0.8)
StrategySelector: OCR_EASYOCR → PDF_REGION (fallback)
QualityValidator: OCR score 0.65 → Try fallback
StrategySelector: Try PDF_REGION
QualityValidator: Score 0.85 ✓
Result: Success after fallback in ~5 seconds
```

**Complex Digital PDF with Mixed Layout**:

```
FileDetector: PDF, digital, complex
LayoutAnalyzer: Hybrid (1-col header + 2-col body), complexity 0.75
StrategySelector: PDF_REGION → ROBUST_PIPELINE (fallback)
QualityValidator: Score 0.72 (acceptable but not great)
StrategySelector: Try ROBUST_PIPELINE for better result
QualityValidator: Score 0.92 ✓
Result: Success after optimization in ~3 seconds
```

## Configuration

These modules use heuristics and thresholds that can be tuned:

```python
# In strategy_selector.py
COMPLEXITY_THRESHOLD_SIMPLE = 0.3  # Below this = simple
COMPLEXITY_THRESHOLD_COMPLEX = 0.7  # Above this = complex

# In quality_validator.py
MIN_SECTIONS_REQUIRED = 3
MIN_TEXT_LENGTH = 100
MIN_QUALITY_SCORE = 0.6
```

## When to Customize

- **Add new file type**: Extend `FileDetector`
- **New layout pattern**: Update `LayoutAnalyzer` heuristics
- **Custom strategy**: Add to `StrategySelector` decision tree
- **Different quality standards**: Adjust `QualityValidator` thresholds
