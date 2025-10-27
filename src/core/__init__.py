"""
Core pipeline modules for resume parsing.

New Refactored Pipeline (v2.0):
- UnifiedResumeParser: Main pipeline orchestration
- DocumentDetector: PDF/DOCX and scan detection
- WordExtractor: Rich metadata extraction
- LayoutDetector: Histogram-based layout analysis
- ColumnSegmenter: Column splitting
- LineGrouper, SectionDetector: Line and section grouping
- UnknownSectionDetector: Ambiguous section detection
- SectionLearner: Auto-learning of section variants

Legacy Components (v1.0):
- UnifiedPipeline, BatchProcessor (old unified system)
"""

# === NEW REFACTORED PIPELINE (v2.0) ===
try:
    from .unified_resume_pipeline import UnifiedResumeParser, PipelineResult
    from .document_detector import DocumentDetector, DocumentType
    from .word_extractor import WordExtractor, WordMetadata
    from .layout_detector_histogram import LayoutDetector, LayoutType
    from .column_segmenter import ColumnSegmenter, Column
    from .line_section_grouper import LineGrouper, SectionDetector, Line, Section, KNOWN_SECTIONS
    from .unknown_section_detector import UnknownSectionDetector, UnknownSection
    REFACTORED_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Refactored pipeline not available: {e}")
    REFACTORED_AVAILABLE = False

# === LEGACY COMPONENTS (v1.0) ===
from .unified_pipeline import UnifiedPipeline
from .batch_processor import BatchProcessor
from .section_learner import SectionLearner

__all__ = [
    # Legacy (always available)
    'UnifiedPipeline',
    'BatchProcessor', 
    'SectionLearner',
]

# Add refactored components if available
if REFACTORED_AVAILABLE:
    __all__.extend([
        'UnifiedResumeParser',
        'PipelineResult',
        'DocumentDetector',
        'DocumentType',
        'WordExtractor',
        'WordMetadata',
        'LayoutDetector',
        'LayoutType',
        'ColumnSegmenter',
        'Column',
        'LineGrouper',
        'SectionDetector',
        'Line',
        'Section',
        'UnknownSectionDetector',
        'UnknownSection',
        'KNOWN_SECTIONS',
    ])
