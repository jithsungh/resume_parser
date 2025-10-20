# Core Module

The core module contains the main pipeline orchestration and learning components.

## Files

### `unified_pipeline.py` ⭐ **MAIN ENTRY POINT**

**Purpose**: Single unified interface for all resume parsing operations.

**What it does**:

- Detects file type (PDF, DOCX, scanned)
- Analyzes document layout and complexity
- Selects optimal parsing strategy automatically
- Orchestrates extraction with automatic fallback
- Validates quality and triggers re-parsing if needed
- Learns from parsed resumes to improve future parsing

**Usage**:

```python
from src.core.unified_pipeline import UnifiedPipeline

pipeline = UnifiedPipeline(enable_learning=True)
result = pipeline.parse("resume.pdf", verbose=True)
```

**Key Features**:

- Automatic strategy selection
- Fallback mechanism (tries multiple strategies if one fails)
- Quality validation
- Section learning integration
- Comprehensive metadata tracking

---

### `batch_processor.py`

**Purpose**: Batch processing with parallelization and progress tracking.

**What it does**:

- Processes multiple resumes in parallel using ThreadPoolExecutor
- Provides progress bars and statistics
- Exports results to Excel with proper formatting
- Handles errors gracefully with retry logic

**Usage**:

```python
from src.core.batch_processor import BatchProcessor

processor = BatchProcessor(max_workers=4)
results = processor.process_folder("resumes/", recursive=True)
processor.export_to_excel(results, "output.xlsx")
```

---

### `section_learner.py`

**Purpose**: Self-learning system that improves section detection over time.

**What it does**:

- Learns section header patterns from parsed resumes
- Builds embedding-based similarity matching
- Updates sections database with new patterns
- Handles variations in section naming (e.g., "Experience" vs "Work History")

**How it works**:

1. Extracts section headers from parsed resumes
2. Computes semantic embeddings using sentence-transformers
3. Clusters similar headers together
4. Updates `config/sections_database.json` with learned patterns

**Benefits**:

- Adapts to organization-specific resume formats
- Recognizes creative section names
- Improves accuracy over time without manual intervention

---

### `parser.py` 🔧 **LEGACY - DEPRECATED**

**Purpose**: Original parser implementation (now replaced by unified_pipeline).

**Status**: Kept for backward compatibility but should not be used for new code.

**Recommendation**: Use `unified_pipeline.py` instead.

---

## Architecture

```
UnifiedPipeline (Main Orchestrator)
    ↓
    ├─→ FileDetector (app/file_detector.py)
    ├─→ LayoutAnalyzer (app/layout_analyzer.py)
    ├─→ StrategySelector (app/strategy_selector.py)
    ├─→ PDF/DOCX/IMG/ROBUST Pipelines
    ├─→ QualityValidator (app/quality_validator.py)
    └─→ SectionLearner (core/section_learner.py)
```

## When to Use What

| Scenario                    | Use This                                              |
| --------------------------- | ----------------------------------------------------- |
| Parse single resume         | `UnifiedPipeline.parse()`                             |
| Parse folder of resumes     | `BatchProcessor` or `scripts/batch_folder_process.py` |
| Custom pipeline integration | `UnifiedPipeline` with custom config                  |
| Learn from resumes          | Enable `enable_learning=True` in UnifiedPipeline      |

## Configuration

### `config/sections_database.json`

Contains learned section patterns and mappings:

```json
{
  "sections": {
    "Experience": {
      "keywords": ["experience", "work history", "employment"],
      "embeddings": [...],
      "count": 150
    }
  }
}
```

## Performance Tips

1. **Disable learning for production**: Set `enable_learning=False` if not training
2. **Adjust workers**: More workers = faster batch processing (but more memory)
3. **Use strategy hints**: If you know document type, force specific strategy
4. **Cache results**: UnifiedPipeline caches intermediate results within session
