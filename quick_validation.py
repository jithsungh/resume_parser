"""
Quick Validation: Test Core Imports and Basic Functionality
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("="*70)
print("QUICK VALIDATION TEST")
print("="*70)
print()

# Test 1: Import section splitter
try:
    from src.core.section_splitter import get_section_splitter
    splitter = get_section_splitter()
    print("✅ Section Splitter: Imported successfully")
except Exception as e:
    print(f"❌ Section Splitter: {e}")

# Test 2: Import section learner
try:
    from src.core.section_learner import SectionLearner
    config_path = project_root / "config" / "sections_database.json"
    learner = SectionLearner(str(config_path))
    print("✅ Section Learner: Imported successfully")
except Exception as e:
    print(f"❌ Section Learner: {e}")

# Test 3: Import split_columns
try:
    from src.PDF_pipeline.split_columns import split_columns_by_multi_section_header
    print("✅ Column Splitter: Imported successfully")
except Exception as e:
    print(f"❌ Column Splitter: {e}")

# Test 4: Import segment_sections
try:
    from src.PDF_pipeline.segment_sections import segment_sections_from_columns
    print("✅ Section Segmenter: Imported successfully")
except Exception as e:
    print(f"❌ Section Segmenter: {e}")

# Test 5: Test multi-section detection
print()
print("Testing Multi-Section Detection:")
try:
    splitter = get_section_splitter()
    test_text = "EXPERIENCE SKILLS"
    result = splitter.detect_multi_section_header(test_text)
    
    if len(result) >= 2:
        sections = [s[0] for s in result]
        print(f"  ✅ '{test_text}' → {sections}")
    else:
        print(f"  ⚠️ '{test_text}' → Only {len(result)} section(s) found")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 6: Test pattern learning
print()
print("Testing Pattern Learning:")
try:
    learner = SectionLearner(str(config_path))
    test_patterns = [
        "GO DEVELOPER",
        "REACT JS DEVELOPER",
        "SOFTWARE ENGINEER"
    ]
    
    for pattern in test_patterns:
        result = learner.learn_from_pattern(pattern)
        if result:
            section, confidence = result
            print(f"  ✅ '{pattern}' → {section} ({confidence:.2f})")
        else:
            print(f"  ⚠️ '{pattern}' → No pattern match")
except Exception as e:
    print(f"  ❌ Error: {e}")

print()
print("="*70)
print("VALIDATION COMPLETE")
print("="*70)
print()
print("If all tests passed (✅), the features are ready!")
print()
