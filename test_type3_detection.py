"""
Test Type 3 Detection on Multiple Resumes
==========================================
Verifies that all Type 3 (hybrid/complex) resumes are correctly detected.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.document_detector import DocumentDetector
from src.core.word_extractor import WordExtractor
from src.core.layout_detector_y_overlap import EnhancedLayoutDetector


def test_type3_resume(file_path: str) -> dict:
    """Test a single resume and return detection results"""
    
    # Extract words
    doc_detector = DocumentDetector()
    doc_type = doc_detector.detect(file_path)
    
    word_extractor = WordExtractor()
    if doc_type.recommended_extraction == 'ocr':
        pages = word_extractor.extract_pdf_ocr(file_path)
    else:
        pages = word_extractor.extract_pdf_text_based(file_path)
    
    if not pages or not pages[0]:
        return {'error': 'No words extracted'}
    
    # Detect layout
    detector = EnhancedLayoutDetector(verbose=False)
    layout = detector.detect_layout(pages[0])
    
    return {
        'file': Path(file_path).name,
        'type': layout.type,
        'type_name': layout.type_name,
        'num_columns': layout.num_columns,
        'confidence': layout.confidence,
        'method': layout.metadata.get('detection_method', 'unknown'),
        'total_words': len(pages[0]),
        'is_correct': layout.type == 3  # Should be Type 3
    }


def main():
    """Test all known Type 3 resumes"""
    
    # List of Type 3 resumes
    type3_resumes = [
        "Resumes/Azid.pdf",
        "Resumes/BARATH_KUMAR_M_resume.pdf",
        "Resumes/Karthik_automation.pdf",
        "Resumes/KaushikJanmanchi.pdf",
        "Resumes/Lakshay_Resume_3YoE.pdf",
        "Resumes/Md_Shehbaaz_Resume.pdf",
    ]
    
    # Also test some Type 2 resumes for comparison
    type2_resumes = [
        "Resumes/Gnanasai_Dachiraju_Resume.pdf",
        "Resumes/Gaganasri-M-FullStack_1.pdf",
        "Resumes/Naukri_LovepreetBehal_11y_5m_.pdf"
    ]
    
    print("=" * 80)
    print("TYPE 3 (HYBRID/COMPLEX) DETECTION TEST")
    print("=" * 80)
    print()
    
    # Test Type 3 resumes
    print("Testing Known Type 3 Resumes:")
    print("-" * 80)
    
    type3_results = []
    for resume in type3_resumes:
        try:
            result = test_type3_resume(resume)
            type3_results.append(result)
            
            status = "✓" if result['is_correct'] else "✗"
            print(f"{status} {result['file']:40} -> Type {result['type']} ({result['type_name']:20}) [{result['method']}]")
            
        except Exception as e:
            print(f"✗ {Path(resume).name:40} -> ERROR: {e}")
    
    print()
    
    # Test Type 2 resumes (should NOT be Type 3)
    print("Testing Known Type 2 Resumes (for comparison):")
    print("-" * 80)
    
    type2_results = []
    for resume in type2_resumes:
        try:
            result = test_type3_resume(resume)
            result['is_correct'] = result['type'] == 2  # Should be Type 2
            type2_results.append(result)
            
            status = "✓" if result['is_correct'] else "✗"
            print(f"{status} {result['file']:40} -> Type {result['type']} ({result['type_name']:20}) [{result['method']}]")
            
        except Exception as e:
            print(f"✗ {Path(resume).name:40} -> ERROR: {e}")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    # Type 3 summary
    type3_correct = sum(1 for r in type3_results if r.get('is_correct', False))
    type3_total = len(type3_results)
    type3_accuracy = (type3_correct / type3_total * 100) if type3_total > 0 else 0
    
    print(f"Type 3 Detection: {type3_correct}/{type3_total} correct ({type3_accuracy:.1f}%)")
    
    if type3_correct < type3_total:
        print("\nFailed Type 3 detections:")
        for r in type3_results:
            if not r.get('is_correct', False):
                print(f"  - {r['file']}: Detected as Type {r['type']} ({r['type_name']})")
    
    # Type 2 summary
    if type2_results:
        type2_correct = sum(1 for r in type2_results if r.get('is_correct', False))
        type2_total = len(type2_results)
        type2_accuracy = (type2_correct / type2_total * 100) if type2_total > 0 else 0
        
        print(f"Type 2 Detection: {type2_correct}/{type2_total} correct ({type2_accuracy:.1f}%)")
        
        if type2_correct < type2_total:
            print("\nFailed Type 2 detections:")
            for r in type2_results:
                if not r.get('is_correct', False):
                    print(f"  - {r['file']}: Detected as Type {r['type']} ({r['type_name']})")
    
    print()
    
    # Overall
    all_correct = type3_correct + (sum(1 for r in type2_results if r.get('is_correct', False)) if type2_results else 0)
    all_total = type3_total + len(type2_results)
    overall_accuracy = (all_correct / all_total * 100) if all_total > 0 else 0
    
    print(f"Overall: {all_correct}/{all_total} correct ({overall_accuracy:.1f}%)")
    
    if overall_accuracy >= 90:
        print("\n🎉 EXCELLENT! Type 3 detection is working well!")
    elif overall_accuracy >= 70:
        print("\n⚠️  GOOD, but needs improvement")
    else:
        print("\n❌ POOR - needs significant improvement")
    
    return overall_accuracy >= 90


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
