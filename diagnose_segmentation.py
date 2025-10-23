"""
Quick diagnostic script to test section segmentation flow
"""
import sys
from pathlib import Path

# Test file - use any PDF you have
TEST_FILE = "freshteams_resume/Resumes/Anirudh_Resume.pdf"

print("="*60)
print("SEGMENTATION DIAGNOSTIC")
print("="*60)

# 1. Test layout detector
print("\n[1/4] Testing layout detector...")
try:
    from src.layout_detector import detect_resume_layout
    
    if not Path(TEST_FILE).exists():
        print(f"❌ Test file not found: {TEST_FILE}")
        print("Please update TEST_FILE variable with an actual PDF path")
        sys.exit(1)
    
    analysis = detect_resume_layout(TEST_FILE)
    print(f"✅ Layout detection works!")
    print(f"   - Recommended: {analysis['recommended_pipeline']}")
    print(f"   - Confidence: {analysis['confidence']:.1%}")
    print(f"   - Columns: {analysis['num_columns']}")
    print(f"   - Scanned: {analysis['is_scanned']}")
    print(f"   - Complexity: {analysis['layout_complexity']}")
except Exception as e:
    print(f"❌ Layout detector failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 2. Test smart parser
print("\n[2/4] Testing smart parser...")
try:
    from src.smart_parser import smart_parse_resume
    
    result, simplified, metadata = smart_parse_resume(
        TEST_FILE,
        verbose=False
    )
    
    sections_count = len(result.get('sections', []))
    print(f"✅ Smart parser works!")
    print(f"   - Pipeline used: {metadata['pipeline_used']}")
    print(f"   - Sections found: {sections_count}")
    print(f"   - Processing time: {metadata['processing_time']:.2f}s")
    print(f"   - Success: {metadata['success']}")
    
    if sections_count == 0:
        print("   ⚠️ WARNING: No sections found!")
        
except Exception as e:
    print(f"❌ Smart parser failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 3. Test service layer
print("\n[3/4] Testing service layer...")
try:
    import asyncio
    from src.api.service import ResumeParserService
    
    service = ResumeParserService(model_path="ml_model")
    service.initialize()
    
    async def test_service():
        result = await service.segment_sections_from_file(
            TEST_FILE,
            use_smart_parser=True
        )
        return result
    
    result = asyncio.run(test_service())
    
    print(f"✅ Service layer works!")
    print(f"   - Sections found: {result.total_sections}")
    print(f"   - Processing time: {result.processing_time_seconds}s")
    print(f"   - Strategy used: {result.metadata.get('strategy_used', 'unknown')}")
    
    if result.total_sections > 0:
        print(f"\n   Sections extracted:")
        for i, section in enumerate(result.sections[:5], 1):
            content_preview = section.content[:50].replace('\n', ' ')
            print(f"   {i}. {section.section_name}: {content_preview}...")
            
        if len(result.sections) > 5:
            print(f"   ... and {len(result.sections) - 5} more sections")
    else:
        print("   ⚠️ WARNING: No sections extracted!")
        if result.metadata:
            print(f"   Metadata: {result.metadata}")
        
except Exception as e:
    print(f"❌ Service layer failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. Test PDF pipeline directly (fallback check)
print("\n[4/4] Testing PDF pipeline directly...")
try:
    from src.PDF_pipeline.pipeline import run_pipeline
    
    result, simplified = run_pipeline(TEST_FILE, verbose=False)
    sections_count = len(result.get('sections', []))
    
    print(f"✅ PDF pipeline works!")
    print(f"   - Sections found: {sections_count}")
    
    if sections_count > 0:
        print(f"   Section names:")
        for section in result['sections'][:5]:
            print(f"   - {section.get('section_name', 'Unknown')}")
    
except Exception as e:
    print(f"❌ PDF pipeline failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("DIAGNOSTIC COMPLETE")
print("="*60)
print("\nIf all tests passed, the segmentation system is working correctly!")
print("If tests failed, check the error messages above for details.")
