"""
Analyze Type 3 Detection Signals
=================================
Detailed analysis of detection signals for Type 3 resumes
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.document_detector import DocumentDetector
from src.core.word_extractor import WordExtractor
from src.core.layout_detector_y_overlap import EnhancedLayoutDetector, LayoutConfig


def analyze_resume(file_path: str):
    """Analyze detection signals for a single resume"""
    
    print(f"\n{'='*80}")
    print(f"Analyzing: {Path(file_path).name}")
    print(f"{'='*80}\n")
    
    # Extract words
    doc_detector = DocumentDetector()
    doc_type = doc_detector.detect(file_path)
    
    word_extractor = WordExtractor()
    if doc_type.recommended_extraction == 'ocr':
        pages = word_extractor.extract_pdf_ocr(file_path)
    else:
        pages = word_extractor.extract_pdf_text_based(file_path)
    
    if not pages or not pages[0]:
        print("ERROR: No words extracted")
        return
    
    # Detect layout with verbose mode
    config = LayoutConfig(verbose=True)
    detector = EnhancedLayoutDetector(config=config)
    layout = detector.detect_layout(pages[0])
    
    # Print detailed metrics
    print(f"\nDetection Results:")
    print(f"  Layout Type: Type {layout.type} ({layout.type_name})")
    print(f"  Confidence: {layout.confidence:.3f}")
    print(f"  Num Columns: {layout.num_columns}")
    print(f"  Detection Method: {layout.metadata.get('detection_method', 'unknown')}")
    
    print(f"\nGutter Metrics:")
    gm = layout.metadata.get('gutter_metrics', {})
    print(f"  Coverage: {gm.get('coverage', 0):.3f}")
    print(f"  Header Fraction: {gm.get('header_frac', 0):.3f}")
    print(f"  Gutter X: {gm.get('gutter_x', 0):.1f}")
    
    print(f"\nOther Signals:")
    print(f"  Y-overlap ratio: {layout.metadata.get('y_overlap_ratio', 0):.3f}")
    print(f"  Valley depth ratio: {layout.metadata.get('valley_depth_ratio', 0):.3f}")
    print(f"  Full-width lines: {layout.metadata.get('full_width_lines', 0)}")
    print(f"  Total words: {layout.metadata.get('total_words', 0)}")
    
    print(f"\nColumn Boundaries:")
    for i, (left, right) in enumerate(layout.column_boundaries):
        print(f"  Column {i+1}: [{left:.1f}, {right:.1f}]")
      # Analyze why it was classified as it was
    print(f"\nClassification Logic:")
    coverage = gm.get('coverage', 0)
    header_frac = gm.get('header_frac', 0)
    full_width_lines = layout.metadata.get('full_width_lines', 0)
    has_horizontal = full_width_lines >= 3
    
    if layout.num_columns == 1:
        print("  → Single column detected")
    elif coverage >= 0.7:
        print(f"  → Strong gutter detected (coverage={coverage:.3f} >= 0.7)")
        print(f"  → Full-width lines: {full_width_lines} (has_horizontal={has_horizontal})")
        print(f"  → Header fraction: {header_frac:.3f}")
        
        if has_horizontal or header_frac > 0.05:
            print(f"    → Type 3 condition met: has_horizontal={has_horizontal} OR header_frac={header_frac:.3f} > 0.05")
            print(f"    → Should classify as Type 3 (hybrid/complex)")
        else:
            print(f"    → Type 2 condition met: has_horizontal={has_horizontal} AND header_frac={header_frac:.3f} <= 0.05")
            print(f"    → Should classify as Type 2 (multi-column)")
            
        print(f"  → ACTUAL: Type {layout.type} ({layout.type_name})")
    else:
        print(f"  → Weak gutter (coverage={coverage:.3f} < 0.7)")
        print(f"  → Using fallback scoring...")


def main():
    # Test Type 3 resumes that are failing
    test_resumes = [
        "Resumes/Azid.pdf",
        "Resumes/BARATH_KUMAR_M_resume.pdf",
        "Resumes/KaushikJanmanchi.pdf",
        "Resumes/Lakshay_Resume_3YoE.pdf",
        "Resumes/Md_Shehbaaz_Resume.pdf",
        # One that works
        "Resumes/Karthik_automation.pdf",
        # Type 2 that's being misclassified
        "Resumes/Gnanasai_Dachiraju_Resume.pdf",
    ]
    
    for resume_path in test_resumes:
        try:
            analyze_resume(resume_path)
        except Exception as e:
            print(f"\nERROR analyzing {resume_path}: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
