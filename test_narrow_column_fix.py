"""
Test script to verify narrow column detection and spaced keyword fixes
"""

from src.core.layout_detector_histogram import LayoutDetector
from src.core.line_section_grouper import LineSectionGrouper
from src.core.word_extractor import WordMetadata

def test_spaced_keyword_cleaning():
    """Test that spaced keywords are properly cleaned"""
    grouper = LineSectionGrouper(verbose=True)
    
    test_cases = [
        ("E X P E R I E N C E", "experience"),
        ("E Xperience", "experience"),
        ("S K I L L S", "skills"),
        ("P R O J E C T S", "projects"),
        ("E D U C A T I O N", "education"),
        ("WORK EXPERIENCE", "work experience"),
        ("Professional Summary", "professional summary"),
    ]
    
    print("=" * 80)
    print("Testing Spaced Keyword Cleaning")
    print("=" * 80)
    
    for test_input, expected_output in test_cases:
        cleaned = grouper._clean_for_heading(test_input)
        cleaned_lower = cleaned.lower().strip()
        
        status = "✓" if cleaned_lower == expected_output else "✗"
        print(f"{status} Input: '{test_input}'")
        print(f"  Cleaned: '{cleaned}' (lowercase: '{cleaned_lower}')")
        print(f"  Expected: '{expected_output}'")
        print()

def test_narrow_column_detection():
    """Test that narrow columns are detected with adaptive threshold"""
    detector = LayoutDetector(
        min_gap_width=20,
        min_column_width=80,
        adaptive_threshold=True,
        verbose=True
    )
    
    print("\n" + "=" * 80)
    print("Testing Narrow Column Detection")
    print("=" * 80)
    
    # Simulate a narrow two-column layout
    # Left column: x=50-250, Right column: x=270-470
    # Gap: 250-270 = 20 points (exactly at threshold)
    
    words = []
    
    # Left column words
    for i in range(20):
        y = 100 + i * 20
        words.append(WordMetadata(
            text=f"word_left_{i}",
            bbox=(50, y, 240, y+12),
            font_size=12,
            font_name="Arial",
            is_bold=False,
            is_italic=False,
            color=(0, 0, 0),
            page=0
        ))
    
    # Right column words (with narrow gap)
    for i in range(20):
        y = 100 + i * 20
        words.append(WordMetadata(
            text=f"word_right_{i}",
            bbox=(270, y, 460, y+12),
            font_size=12,
            font_name="Arial",
            is_bold=False,
            is_italic=False,
            color=(0, 0, 0),
            page=0
        ))
    
    page_width = 612  # Standard letter size
    
    print(f"\nSimulated layout: 2 columns with {20}pt gap")
    print(f"Left column: x=50-240")
    print(f"Gap: x=240-270 (width=30pt)")
    print(f"Right column: x=270-460")
    print()
    
    layout = detector.detect_layout(words, page_width)
    
    print(f"\nDetection Results:")
    print(f"  Type: {layout.type_name} (Type {layout.type})")
    print(f"  Num Columns: {layout.num_columns}")
    print(f"  Confidence: {layout.confidence:.1%}")
    print(f"  Column Boundaries:")
    for i, (x_start, x_end) in enumerate(layout.column_boundaries):
        print(f"    Column {i+1}: x={x_start:.1f} to {x_end:.1f} (width={x_end-x_start:.1f})")
    
    # Verify
    if layout.num_columns >= 2:
        print("\n✓ SUCCESS: Narrow columns detected!")
    else:
        print("\n✗ FAILED: Narrow columns not detected")
    
    return layout.num_columns >= 2

def test_section_header_detection():
    """Test section header detection with spaced keywords"""
    grouper = LineSectionGrouper(verbose=True)
    
    print("\n" + "=" * 80)
    print("Testing Section Header Detection with Spaced Keywords")
    print("=" * 80)
    
    # Create test lines with spaced keywords
    from src.core.line_grouper import Line
    
    test_headers = [
        "E X P E R I E N C E",
        "E Xperience",
        "S K I L L S",
        "WORK EXPERIENCE",
        "P R O F E S S I O N A L  S U M M A R Y",
    ]
    
    results = []
    for header_text in test_headers:
        # Create a mock line
        words = [WordMetadata(
            text=word,
            bbox=(50 + i*20, 100, 50 + i*20 + 15, 112),
            font_size=14,
            font_name="Arial",
            is_bold=True,
            is_italic=False,
            color=(0, 0, 0),
            page=0
        ) for i, word in enumerate(header_text.split())]
        
        line = Line(
            text=header_text,
            words=words,
            bbox=(50, 100, 300, 112),
            page=0,
            line_id=0
        )
        
        is_header, confidence = grouper._is_section_header(line)
        
        status = "✓" if is_header else "✗"
        print(f"{status} '{header_text}' -> is_header={is_header}, confidence={confidence:.2f}")
        
        if is_header:
            matched_name = grouper._match_section_name(header_text)
            print(f"   Matched to: '{matched_name}'")
        
        results.append(is_header)
        print()
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"\nResults: {success_count}/{total_count} headers detected")
    
    return success_count >= total_count * 0.8  # 80% success rate

if __name__ == "__main__":
    print("\n" + "🔧 TESTING NARROW COLUMN AND SPACED KEYWORD FIXES" + "\n")
    
    # Test 1: Spaced keyword cleaning
    test_spaced_keyword_cleaning()
    
    # Test 2: Narrow column detection
    narrow_col_success = test_narrow_column_detection()
    
    # Test 3: Section header detection with spaced keywords
    header_success = test_section_header_detection()
    
    print("\n" + "=" * 80)
    print("OVERALL RESULTS")
    print("=" * 80)
    print(f"Narrow Column Detection: {'✓ PASS' if narrow_col_success else '✗ FAIL'}")
    print(f"Section Header Detection: {'✓ PASS' if header_success else '✗ FAIL'}")
    print()
    
    if narrow_col_success and header_success:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed. Please review the output above.")
