#!/usr/bin/env python3
"""
Test Refactored Pipeline
========================
Tests the complete refactored pipeline with all components.

Usage:
    python test_refactored_pipeline.py
"""

import sys
from pathlib import Path

# Test imports
def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        from src.core.document_detector import DocumentDetector
        print("  ✅ DocumentDetector")
    except Exception as e:
        print(f"  ❌ DocumentDetector: {e}")
        return False
    
    try:
        from src.core.word_extractor import WordExtractor
        print("  ✅ WordExtractor")
    except Exception as e:
        print(f"  ❌ WordExtractor: {e}")
        return False
    
    try:
        from src.core.layout_detector_histogram import LayoutDetector
        print("  ✅ LayoutDetector")
    except Exception as e:
        print(f"  ❌ LayoutDetector: {e}")
        return False
    
    try:
        from src.core.column_segmenter import ColumnSegmenter
        print("  ✅ ColumnSegmenter")
    except Exception as e:
        print(f"  ❌ ColumnSegmenter: {e}")
        return False
    
    try:
        from src.core.line_section_grouper import LineGrouper, SectionDetector
        print("  ✅ LineGrouper, SectionDetector")
    except Exception as e:
        print(f"  ❌ LineGrouper/SectionDetector: {e}")
        return False
    
    try:
        from src.core.unknown_section_detector import UnknownSectionDetector
        print("  ✅ UnknownSectionDetector")
    except Exception as e:
        print(f"  ❌ UnknownSectionDetector: {e}")
        return False
    
    try:
        from src.core.unified_resume_pipeline import UnifiedResumeParser
        print("  ✅ UnifiedResumeParser")
    except Exception as e:
        print(f"  ❌ UnifiedResumeParser: {e}")
        return False
    
    try:
        from src.core.section_learner import SectionLearner
        print("  ✅ SectionLearner")
    except Exception as e:
        print(f"  ❌ SectionLearner: {e}")
        return False
    
    return True


def test_section_database():
    """Test that sections database loads correctly"""
    print("\nTesting sections database...")
    
    try:
        from src.core.line_section_grouper import load_sections_database, KNOWN_SECTIONS, SECTION_MAPPING
        
        db = load_sections_database()
        print(f"  ✅ Database loaded: {len(db.get('sections', {}))} sections")
        print(f"  ✅ Known sections: {len(KNOWN_SECTIONS)} variants")
        print(f"  ✅ Section mapping: {len(SECTION_MAPPING)} entries")
        
        # Show sample
        print("\n  Sample canonical sections:")
        for i, section_name in enumerate(list(db.get('sections', {}).keys())[:5], 1):
            variants = db['sections'][section_name].get('variants', [])
            print(f"    {i}. {section_name}: {len(variants)} variants")
        
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_section_learner():
    """Test section learner functionality"""
    print("\nTesting section learner...")
    
    try:
        from src.core.section_learner import SectionLearner
        
        learner = SectionLearner(auto_save=False)
        print("  ✅ SectionLearner initialized")
        
        # Test observe_section
        test_sections = [
            "Professional Experience",
            "Technical Skills",
            "Work History",
            "Education",
            "Projects"
        ]
        
        for section in test_sections:
            learner.observe_section(section)
        
        print(f"  ✅ Observed {len(test_sections)} sections")
        
        # Test get_learning_suggestions
        suggestions = learner.get_learning_suggestions()
        print(f"  ✅ Generated learning suggestions")
        print(f"     - Add variants: {len(suggestions['add_variants'])}")
        print(f"     - New sections: {len(suggestions['add_new_sections'])}")
        print(f"     - Review unknown: {len(suggestions['review_unknown'])}")
        
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pipeline_initialization():
    """Test pipeline initialization"""
    print("\nTesting pipeline initialization...")
    
    try:
        from src.core.unified_resume_pipeline import UnifiedResumeParser
        
        # Test with embeddings disabled (faster)
        parser = UnifiedResumeParser(
            use_ocr_if_scanned=False,
            use_embeddings=False,
            verbose=False
        )
        print("  ✅ Pipeline initialized (OCR disabled, embeddings disabled)")
        
        # Test with embeddings enabled (if available)
        try:
            parser_with_embeddings = UnifiedResumeParser(
                use_ocr_if_scanned=False,
                use_embeddings=True,
                verbose=False
            )
            print("  ✅ Pipeline initialized (with embeddings)")
        except Exception as e:
            print(f"  ⚠️  Embeddings not available: {e}")
        
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sample_file():
    """Test pipeline on a sample file if available"""
    print("\nTesting pipeline on sample file...")
    
    # Look for sample PDFs
    sample_dirs = [
        Path("freshteams_resume"),
        Path("outputs"),
        Path(".")
    ]
    
    sample_file = None
    for dir_path in sample_dirs:
        if not dir_path.exists():
            continue
        
        pdfs = list(dir_path.glob("**/*.pdf"))
        if pdfs:
            sample_file = pdfs[0]
            break
    
    if not sample_file:
        print("  ⚠️  No sample PDF found, skipping file test")
        return True
    
    try:
        from src.core.unified_resume_pipeline import UnifiedResumeParser
        
        print(f"  📄 Testing with: {sample_file.name}")
        
        parser = UnifiedResumeParser(
            use_ocr_if_scanned=False,
            use_embeddings=False,  # Disable for faster test
            verbose=False
        )
        
        result = parser.parse(str(sample_file))
        
        if result.success:
            print(f"  ✅ Parsing successful")
            print(f"     - Pages: {result.total_pages}")
            print(f"     - Words: {result.total_words}")
            print(f"     - Sections: {len(result.sections)}")
            print(f"     - Time: {result.processing_time:.2f}s")
            
            # Show sections
            if result.sections:
                print(f"\n     Detected sections:")
                for section in result.sections[:5]:
                    print(f"       - {section.section_name}")
        else:
            print(f"  ❌ Parsing failed: {result.error}")
            return False
        
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("="*70)
    print("REFACTORED PIPELINE TEST SUITE")
    print("="*70)
    
    tests = [
        ("Module Imports", test_imports),
        ("Sections Database", test_section_database),
        ("Section Learner", test_section_learner),
        ("Pipeline Initialization", test_pipeline_initialization),
        ("Sample File Processing", test_sample_file)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*70}")
        print(f"TEST: {test_name}")
        print(f"{'='*70}")
        
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ Test crashed: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
