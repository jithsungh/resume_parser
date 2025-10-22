"""
Quick Validation - Check if fixes are working
"""

print("🔍 Validating Resume Parser Fixes\n")
print("="*70)

# Check 1: Verify PDF pipeline imports
print("\n1️⃣  Checking PDF Pipeline availability...")
try:
    from src.PDF_pipeline.get_words import get_words_from_pdf
    from src.PDF_pipeline.split_columns import split_columns
    from src.PDF_pipeline.get_lines import get_column_wise_lines
    from src.PDF_pipeline.segment_sections import segment_sections_from_columns
    print("   ✅ PDF Pipeline imports successful")
except Exception as e:
    print(f"   ❌ PDF Pipeline import failed: {e}")

# Check 2: Verify service imports
print("\n2️⃣  Checking API Service...")
try:
    from src.api.service import ResumeParserService
    print("   ✅ API Service imports successful")
except Exception as e:
    print(f"   ❌ API Service import failed: {e}")

# Check 3: Verify name extractor
print("\n3️⃣  Checking Name/Location Extractor...")
try:
    from src.core.name_location_extractor import NameLocationExtractor
    extractor = NameLocationExtractor()
    print(f"   ✅ Name Extractor initialized")
    print(f"   SpaCy available: {extractor.spacy_available}")
except Exception as e:
    print(f"   ❌ Name Extractor failed: {e}")

# Check 4: Test filename extraction
print("\n4️⃣  Testing Filename Name Extraction...")
try:
    from src.core.name_location_extractor import NameLocationExtractor
    extractor = NameLocationExtractor()
    
    # Test with example filename
    test_filename = "Ayush_Kumar_Resume.pdf"
    name = extractor._extract_name_from_filename(test_filename)
    
    if name:
        print(f"   ✅ Extracted '{name}' from '{test_filename}'")
    else:
        print(f"   ⚠️  Could not extract name from filename")
except Exception as e:
    print(f"   ❌ Filename extraction test failed: {e}")

# Check 5: Test segmentation on a sample
print("\n5️⃣  Testing PDF Segmentation...")
try:
    from pathlib import Path
    from src.PDF_pipeline.get_words import get_words_from_pdf
    from src.PDF_pipeline.split_columns import split_columns
    from src.PDF_pipeline.get_lines import get_column_wise_lines
    from src.PDF_pipeline.segment_sections import segment_sections_from_columns
    
    test_file = Path("freshteams_resume/Golang Developer/AnirudhReddy_Resume.pdf")
    
    if test_file.exists():
        print(f"   Testing with: {test_file.name}")
        
        pages = get_words_from_pdf(str(test_file))
        columns = split_columns(pages, min_words_per_column=10, dynamic_min_words=True)
        columns_with_lines = get_column_wise_lines(columns, y_tolerance=1.0)
        result = segment_sections_from_columns(columns_with_lines)
        
        sections = result.get('sections', [])
        section_names = [s.get('section') for s in sections]
        
        print(f"   ✅ Segmentation successful!")
        print(f"   Sections found: {', '.join(section_names)}")
        
        # Check if Experience section exists
        if 'Experience' in section_names:
            print(f"   ✅ Experience section detected!")
        else:
            print(f"   ⚠️  Experience section not found")
    else:
        print(f"   ⚠️  Test file not found: {test_file}")
        
except Exception as e:
    print(f"   ❌ Segmentation test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("✅ Validation complete!")
print("\nNext steps:")
print("1. Start API: python -m uvicorn src.api.main:app --reload")
print("2. Run tests: python test_fixed_api.py")
