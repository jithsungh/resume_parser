#!/usr/bin/env python3
"""
Quick test script to verify the complete pipeline works.
Tests single file parsing and batch processing.
"""

import sys
import json
from pathlib import Path

def test_single_resume():
    """Test parsing a single resume."""
    print("="*60)
    print("TEST 1: Single Resume Parsing")
    print("="*60)
    
    from src.core.unified_pipeline import UnifiedPipeline
    
    pipeline = UnifiedPipeline()
    test_pdf = "freshteams_resume/Resumes/Azid.pdf"
    
    if not Path(test_pdf).exists():
        print(f"❌ Test file not found: {test_pdf}")
        return False
    print(f"\nParsing: {test_pdf}")
    result = pipeline.parse(test_pdf, verbose=True)
    
    print(f"\n✓ Success: {result['success']}")
    print(f"  Strategy: {result['metadata'].get('strategy', 'unknown')}")
    
    if result['result'] and 'sections' in result['result']:
        sections = result['result']['sections']
        print(f"  Sections: {len(sections)}")
        print(f"  Time: {result['metadata']['processing_time']:.2f}s")
        
        print(f"\n  Detected sections:")
        for section in sections:
            lines = len(section.get('lines', []))
            print(f"    - {section['section']}: {lines} lines")
    
    return result['success']


def test_batch_processing():
    """Test batch processing."""
    print("\n" + "="*60)
    print("TEST 2: Batch Processing")
    print("="*60)
    
    from src.core.batch_processor import BatchProcessor
    
    test_folder = "freshteams_resume/Resumes"
    output_file = "test_batch_output.xlsx"
    
    if not Path(test_folder).exists():
        print(f"❌ Test folder not found: {test_folder}")
        return False
    
    # Test with just 3 files
    test_files = list(Path(test_folder).glob("*.pdf"))[:3]
    
    if not test_files:
        print(f"❌ No PDF files found in {test_folder}")
        return False
    
    print(f"\nProcessing {len(test_files)} test files...")
    
    processor = BatchProcessor()
    results = processor.process_batch(
        input_paths=[str(f) for f in test_files],
        output_excel=output_file,
        max_workers=2,
        verbose=False
    )
    
    print(f"\n✓ Processed: {results['total_processed']}")
    print(f"  Successful: {results['successful']}")
    print(f"  Failed: {results['failed']}")
    print(f"  Time: {results['total_time']:.2f}s")
    print(f"  Output: {output_file}")
    
    # Cleanup
    if Path(output_file).exists():
        Path(output_file).unlink()
        print(f"  (cleaned up test file)")
    
    return results['successful'] > 0


def test_section_learning():
    """Test section learning system."""
    print("\n" + "="*60)
    print("TEST 3: Section Learning")
    print("="*60)
    
    from src.core.section_learner import SectionLearner
    
    learner = SectionLearner()
    
    # Test known section
    is_valid, section_name, confidence = learner.classify_section("Work Experience")
    print(f"\n✓ Known section test:")
    print(f"  Input: 'Work Experience'")
    print(f"  Valid: {is_valid}, Match: {section_name}, Confidence: {confidence:.2f}")
    
    # Test variant
    is_valid, section_name, confidence = learner.classify_section("professional skills")
    print(f"\n✓ Variant test:")
    print(f"  Input: 'professional skills'")
    print(f"  Valid: {is_valid}, Match: {section_name}, Confidence: {confidence:.2f}")
    
    # Test unknown section
    is_valid, section_name, confidence = learner.classify_section("Random Gibberish XYZ123")
    print(f"\n✓ Unknown section test:")
    print(f"  Input: 'Random Gibberish XYZ123'")
    print(f"  Valid: {is_valid}, Match: {section_name}, Confidence: {confidence:.2f}")
    
    return True


def main():
    """Run all tests."""
    print("\n🧪 Testing Resume Parser Pipeline\n")
    
    results = {
        'single_resume': False,
        'batch_processing': False,
        'section_learning': False
    }
    
    try:
        results['single_resume'] = test_single_resume()
    except Exception as e:
        print(f"\n❌ Single resume test failed: {e}")
    
    try:
        results['batch_processing'] = test_batch_processing()
    except Exception as e:
        print(f"\n❌ Batch processing test failed: {e}")
    
    try:
        results['section_learning'] = test_section_learning()
    except Exception as e:
        print(f"\n❌ Section learning test failed: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name.replace('_', ' ').title()}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
