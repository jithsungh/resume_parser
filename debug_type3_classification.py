#!/usr/bin/env python3
"""
Debug script to understand why Type 3 resumes are being misclassified as Type 2

Provides detailed analysis of histogram valley depth and classification signals
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.document_detector import DocumentDetector
from src.core.word_extractor import WordExtractor
from src.core.layout_detector_y_overlap import EnhancedLayoutDetector


def debug_type3_resume(pdf_path: str):
    """Analyze a Type 3 resume in detail"""
    print("="*80)
    print(f"DEBUGGING: {Path(pdf_path).name}")
    print("="*80)
    
    # Extract words
    doc_detector = DocumentDetector(verbose=False)
    doc_type = doc_detector.detect(pdf_path)
    
    word_extractor = WordExtractor(verbose=False)
    pages_words = word_extractor.extract_pdf_text_based(pdf_path)
    
    if not pages_words or not pages_words[0]:
        print("ERROR: No words extracted")
        return
    
    # Analyze with VERBOSE mode
    detector = EnhancedLayoutDetector(
        bin_width=5,
        min_gap_width=20,
        min_column_width=80,
        adaptive_threshold=True,
        valley_threshold=0.3,
        verbose=True  # VERBOSE!
    )
    
    layout = detector.detect_layout(pages_words[0])
    
    print("\n" + "="*80)
    print(f"FINAL RESULT: {layout.type_name} (Type {layout.type})")
    print("="*80)
    print(f"Confidence: {layout.confidence:.1%}")
    print(f"Column Boundaries: {layout.column_boundaries}")
    print(f"Detection Method: {layout.metadata.get('detection_method')}")
    
    return layout


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_type3_classification.py <resume.pdf>")
        sys.exit(1)
    
    debug_type3_resume(sys.argv[1])
