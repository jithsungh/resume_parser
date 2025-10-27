"""
Test the Enhanced Layout Detector with Y-overlap analysis
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.document_detector import DocumentDetector
from src.core.word_extractor import WordExtractor
from src.core.layout_detector_y_overlap import EnhancedLayoutDetector


def test_enhanced_detection(file_path: str):
    """Test enhanced layout detection on a file"""
    print(f"Testing Enhanced Layout Detection")
    print("=" * 80)
    print(f"File: {file_path}")
    print()
    
    # Step 1: Detect document type
    print("Step 1: Document Detection")
    print("-" * 80)
    doc_detector = DocumentDetector(verbose=True)
    doc_type = doc_detector.detect(file_path)
    print()
    
    # Step 2: Extract words
    print("Step 2: Word Extraction")
    print("-" * 80)
    word_extractor = WordExtractor(verbose=True)
    
    if doc_type.file_type == 'pdf':
        if doc_type.recommended_extraction == 'ocr':
            pages = word_extractor.extract_pdf_ocr(file_path)
        else:
            pages = word_extractor.extract_pdf_text_based(file_path)
    else:
        print("Unsupported file type")
        return
    
    if not pages or not pages[0]:
        print("No words extracted!")
        return
    
    words = pages[0]
    print()
    
    # Step 3: Enhanced layout detection
    print("Step 3: Enhanced Layout Detection with Y-Overlap Analysis")
    print("=" * 80)
    
    detector = EnhancedLayoutDetector(verbose=True)
    layout = detector.detect_layout(words)
    
    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Layout Type: {layout.type_name} (Type {layout.type})")
    print(f"Number of Columns: {layout.num_columns}")
    print(f"Confidence: {layout.confidence:.1%}")
    print()
    print("Column Boundaries:")
    for i, (x_start, x_end) in enumerate(layout.column_boundaries, 1):
        width = x_end - x_start
        print(f"  Column {i}: x={x_start:6.1f} to {x_end:6.1f} (width={width:6.1f}pt)")
    
    print()
    print("Detection Method:", layout.metadata.get('detection_method', 'unknown'))
    
    # Additional info for Type 3
    if layout.type == 3:
        print()
        print("Type 3 (Hybrid) Details:")
        if 'left_column_count' in layout.metadata:
            print(f"  Left column lines: {layout.metadata['left_column_count']}")
        if 'right_column_count' in layout.metadata:
            print(f"  Right column lines: {layout.metadata['right_column_count']}")
        if 'y_overlap' in layout.metadata:
            print(f"  Y-overlap detected: {layout.metadata['y_overlap']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_enhanced_layout_detection.py <pdf_file>")
        sys.exit(1)
    
    test_enhanced_detection(sys.argv[1])
