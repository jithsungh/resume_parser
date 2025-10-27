"""
Comprehensive Type 3 Resume Analysis
=====================================
Analyzes multiple Type 3 resumes to understand their characteristics
and improve detection logic.
"""

import sys
from pathlib import Path
from collections import defaultdict
import json

sys.path.insert(0, str(Path(__file__).parent))

from src.core.document_detector import DocumentDetector
from src.core.word_extractor import WordExtractor
from src.core.layout_detector_y_overlap import EnhancedLayoutDetector


def analyze_resume_layout(file_path: str) -> dict:
    """
    Comprehensive layout analysis of a single resume
    
    Returns:
        Dictionary with detailed layout characteristics
    """
    print(f"\n{'='*80}")
    print(f"Analyzing: {Path(file_path).name}")
    print('='*80)
    
    # Extract words
    doc_detector = DocumentDetector()
    doc_type = doc_detector.detect(file_path)
    
    word_extractor = WordExtractor()
    if doc_type.recommended_extraction == 'ocr':
        pages = word_extractor.extract_pdf_ocr(file_path)
    else:
        pages = word_extractor.extract_pdf_text_based(file_path)
    
    if not pages or not pages[0]:
        print("ERROR: No words found!")
        return None
    
    words = pages[0]
    page_width = max(w.bbox[2] for w in words)
    page_height = max(w.bbox[3] for w in words)
    
    print(f"Total words: {len(words)}")
    print(f"Page size: {page_width:.1f} x {page_height:.1f}")
    
    # Group into lines
    lines = defaultdict(list)
    y_tolerance = 5
    
    for word in words:
        y_center = (word.bbox[1] + word.bbox[3]) / 2
        found_line = False
        for line_y in list(lines.keys()):
            if abs(y_center - line_y) <= y_tolerance:
                lines[line_y].append(word)
                found_line = True
                break
        if not found_line:
            lines[y_center] = [word]
    
    sorted_lines = sorted(lines.items(), key=lambda x: x[0])
    
    # Analyze line characteristics
    mid_x = page_width / 2
    left_lines = []
    right_lines = []
    full_width_lines = []
    line_gaps = []  # Horizontal gaps within lines
    
    for y_pos, line_words in sorted_lines:
        line_words.sort(key=lambda w: w.bbox[0])
        x_start = line_words[0].bbox[0]
        x_end = line_words[-1].bbox[2]
        width = x_end - x_start
        
        # Find gaps within line
        max_gap_in_line = 0
        for i in range(len(line_words) - 1):
            gap = line_words[i + 1].bbox[0] - line_words[i].bbox[2]
            if gap > max_gap_in_line:
                max_gap_in_line = gap
        
        if max_gap_in_line > 10:
            line_gaps.append(max_gap_in_line)
        
        # Classify line
        if width > page_width * 0.75:
            full_width_lines.append((y_pos, x_start, x_end, width))
        elif x_start < mid_x * 0.6 and x_end < mid_x * 1.3:
            left_lines.append((y_pos, x_start, x_end, width))
        elif x_start > mid_x * 0.7:
            right_lines.append((y_pos, x_start, x_end, width))
        else:
            full_width_lines.append((y_pos, x_start, x_end, width))
    
    # Calculate characteristics
    characteristics = {
        'file_name': Path(file_path).name,
        'total_words': len(words),
        'total_lines': len(sorted_lines),
        'page_width': page_width,
        'page_height': page_height,
        'left_lines': len(left_lines),
        'right_lines': len(right_lines),
        'full_width_lines': len(full_width_lines),
    }
    
    # Y-overlap analysis
    if left_lines and right_lines:
        left_y_min = min(y for y, _, _, _ in left_lines)
        left_y_max = max(y for y, _, _, _ in left_lines)
        right_y_min = min(y for y, _, _, _ in right_lines)
        right_y_max = max(y for y, _, _, _ in right_lines)
        
        y_overlap = not (left_y_max < right_y_min or right_y_max < left_y_min)
        
        if y_overlap:
            overlap_range = min(left_y_max, right_y_max) - max(left_y_min, right_y_min)
            total_range = max(left_y_max, right_y_max) - min(left_y_min, right_y_min)
            overlap_pct = (overlap_range / total_range) * 100 if total_range > 0 else 0
        else:
            overlap_pct = 0
        
        # Column boundaries
        left_x_max = max(x_end for _, _, x_end, _ in left_lines) if left_lines else 0
        right_x_min = min(x_start for _, x_start, _, _ in right_lines) if right_lines else page_width
        col_gap = right_x_min - left_x_max
        col_boundary = (left_x_max + right_x_min) / 2
        
        characteristics.update({
            'has_y_overlap': y_overlap,
            'y_overlap_pct': overlap_pct,
            'left_y_range': (left_y_min, left_y_max),
            'right_y_range': (right_y_min, right_y_max),
            'left_x_max': left_x_max,
            'right_x_min': right_x_min,
            'column_gap': col_gap,
            'column_boundary': col_boundary,
            'boundary_position_pct': (col_boundary / page_width) * 100,
        })
    else:
        characteristics.update({
            'has_y_overlap': False,
            'y_overlap_pct': 0,
        })
    
    # Gap analysis
    if line_gaps:
        characteristics.update({
            'has_horizontal_gaps': True,
            'max_horizontal_gap': max(line_gaps),
            'avg_horizontal_gap': sum(line_gaps) / len(line_gaps),
            'num_lines_with_gaps': len(line_gaps),
        })
    else:
        characteristics.update({
            'has_horizontal_gaps': False,
            'max_horizontal_gap': 0,
            'avg_horizontal_gap': 0,
            'num_lines_with_gaps': 0,
        })
    
    # Test with enhanced detector
    detector = EnhancedLayoutDetector(verbose=True)
    layout_result = detector.detect_layout(words, page_width)
    
    characteristics.update({
        'detected_type': layout_result.type,
        'detected_type_name': layout_result.type_name,
        'detected_columns': layout_result.num_columns,
        'detection_confidence': layout_result.confidence,
        'detection_method': layout_result.metadata.get('detection_method', 'unknown'),
    })
    
    # Print summary
    print(f"\n{'─'*80}")
    print("LAYOUT CHARACTERISTICS")
    print('─'*80)
    print(f"Lines: {characteristics['total_lines']} total")
    print(f"  - Left column: {characteristics['left_lines']} lines")
    print(f"  - Right column: {characteristics['right_lines']} lines")
    print(f"  - Full width: {characteristics['full_width_lines']} lines")
    print()
    
    if characteristics['has_y_overlap']:
        print(f"✓ Y-OVERLAP DETECTED:")
        print(f"  - Overlap: {characteristics['y_overlap_pct']:.1f}%")
        print(f"  - Left Y: {characteristics['left_y_range'][0]:.1f} - {characteristics['left_y_range'][1]:.1f}")
        print(f"  - Right Y: {characteristics['right_y_range'][0]:.1f} - {characteristics['right_y_range'][1]:.1f}")
        print(f"  - Column gap: {characteristics['column_gap']:.1f}pt")
        print(f"  - Column boundary: x={characteristics['column_boundary']:.1f} ({characteristics['boundary_position_pct']:.1f}% of page)")
    else:
        print("✗ No Y-overlap detected")
    print()
    
    if characteristics['has_horizontal_gaps']:
        print(f"Horizontal gaps within lines:")
        print(f"  - Max gap: {characteristics['max_horizontal_gap']:.1f}pt")
        print(f"  - Avg gap: {characteristics['avg_horizontal_gap']:.1f}pt")
        print(f"  - Lines with gaps: {characteristics['num_lines_with_gaps']}")
    else:
        print("No significant horizontal gaps within lines")
    print()
    
    print(f"{'─'*80}")
    print("DETECTION RESULT")
    print('─'*80)
    print(f"Type: {characteristics['detected_type_name']} (Type {characteristics['detected_type']})")
    print(f"Columns: {characteristics['detected_columns']}")
    print(f"Confidence: {characteristics['detection_confidence']:.1%}")
    print(f"Method: {characteristics['detection_method']}")
    
    if layout_result.column_boundaries:
        print(f"\nColumn Boundaries:")
        for i, (x0, x1) in enumerate(layout_result.column_boundaries, 1):
            print(f"  Column {i}: x={x0:6.1f} to {x1:6.1f} (width={x1-x0:6.1f}pt)")
    
    return characteristics


def analyze_all_type3_resumes():
    """Analyze all Type 3 resumes and compare characteristics"""
    
    type3_resumes = [
        "freshteams_resume/Resumes/Azid.pdf",
        "freshteams_resume/Resumes/BARATH_KUMAR_M_resume.pdf",
        "freshteams_resume/Resumes/Karthik_automation.pdf",
        "freshteams_resume/Resumes/KaushikJanmanchi.pdf",
        "freshteams_resume/Resumes/Lakshay_Resume_3YoE.pdf",
        "freshteams_resume/Resumes/Md_Shehbaaz_Resume.pdf",
        # Skip the complex one for now
        # "freshteams_resume/Resumes/Manish_Kumar_Rai_CV_QA_Updated_Sepember_2025_(1).pdf",
    ]
    
    all_characteristics = []
    
    for resume_path in type3_resumes:
        try:
            characteristics = analyze_resume_layout(resume_path)
            if characteristics:
                all_characteristics.append(characteristics)
        except Exception as e:
            print(f"\n❌ ERROR analyzing {resume_path}: {e}")
            import traceback
            traceback.print_exc()
    
    # Comparative analysis
    print(f"\n\n{'='*80}")
    print("COMPARATIVE ANALYSIS OF ALL TYPE 3 RESUMES")
    print('='*80)
    
    if not all_characteristics:
        print("No resumes analyzed successfully")
        return
    
    # Summary table
    print(f"\n{'File':<40} {'Lines':<8} {'L/R/F':<12} {'Y-Ovlp':<8} {'Gap':<8} {'Type':<6} {'Method':<10}")
    print('─'*100)
    
    for char in all_characteristics:
        l_r_f = f"{char['left_lines']}/{char['right_lines']}/{char['full_width_lines']}"
        y_overlap = f"{char['y_overlap_pct']:.0f}%" if char['has_y_overlap'] else "No"
        gap = f"{char['column_gap']:.0f}pt" if char['has_y_overlap'] else "N/A"
        detected = f"T{char['detected_type']}"
        method = char['detection_method'][:10]
        
        print(f"{char['file_name']:<40} {char['total_lines']:<8} {l_r_f:<12} {y_overlap:<8} {gap:<8} {detected:<6} {method:<10}")
    
    # Identify patterns for Type 3
    print(f"\n{'─'*80}")
    print("TYPE 3 PATTERNS IDENTIFIED:")
    print('─'*80)
    
    type3_detected = [c for c in all_characteristics if c['detected_type'] == 3]
    type2_detected = [c for c in all_characteristics if c['detected_type'] == 2]
    type1_detected = [c for c in all_characteristics if c['detected_type'] == 1]
    
    print(f"\nCorrectly detected as Type 3: {len(type3_detected)}/{len(all_characteristics)}")
    print(f"Incorrectly detected as Type 2: {len(type2_detected)}/{len(all_characteristics)}")
    print(f"Incorrectly detected as Type 1: {len(type1_detected)}/{len(all_characteristics)}")
    
    if type3_detected:
        print(f"\nType 3 Characteristics (correctly detected):")
        avg_y_overlap = sum(c['y_overlap_pct'] for c in type3_detected) / len(type3_detected)
        avg_left_lines = sum(c['left_lines'] for c in type3_detected) / len(type3_detected)
        avg_right_lines = sum(c['right_lines'] for c in type3_detected) / len(type3_detected)
        avg_col_gap = sum(c.get('column_gap', 0) for c in type3_detected) / len(type3_detected)
        
        print(f"  - Avg Y-overlap: {avg_y_overlap:.1f}%")
        print(f"  - Avg left lines: {avg_left_lines:.1f}")
        print(f"  - Avg right lines: {avg_right_lines:.1f}")
        print(f"  - Avg column gap: {avg_col_gap:.1f}pt")
    
    if type2_detected or type1_detected:
        print(f"\n⚠️  MISDETECTED RESUMES:")
        for c in (type2_detected + type1_detected):
            print(f"  - {c['file_name']}: Detected as Type {c['detected_type']}, has Y-overlap={c['y_overlap_pct']:.0f}%")
    
    # Recommendations
    print(f"\n{'─'*80}")
    print("RECOMMENDATIONS FOR IMPROVED DETECTION:")
    print('─'*80)
    
    min_left_lines = min(c['left_lines'] for c in all_characteristics if c['has_y_overlap'])
    min_right_lines = min(c['right_lines'] for c in all_characteristics if c['has_y_overlap'])
    min_y_overlap = min(c['y_overlap_pct'] for c in all_characteristics if c['has_y_overlap'])
    max_col_gap = max(c.get('column_gap', 0) for c in all_characteristics if c['has_y_overlap'])
    
    print(f"1. Minimum thresholds for Type 3 detection:")
    print(f"   - Left column lines: >= {min_left_lines} (currently using 3)")
    print(f"   - Right column lines: >= {min_right_lines} (currently using 3)")
    print(f"   - Y-overlap percentage: >= {min_y_overlap:.0f}% (currently using 30%)")
    print(f"   - Column gap: Can be negative up to {abs(min(c.get('column_gap', 0) for c in all_characteristics if c['has_y_overlap'])):.0f}pt")
    
    print(f"\n2. Column boundary validation:")
    boundary_positions = [c.get('boundary_position_pct', 50) for c in all_characteristics if c['has_y_overlap']]
    if boundary_positions:
        min_boundary = min(boundary_positions)
        max_boundary = max(boundary_positions)
        print(f"   - Boundary position range: {min_boundary:.0f}% - {max_boundary:.0f}% of page width")
        print(f"   - Currently using: 30% - 70%")
        if min_boundary < 30 or max_boundary > 70:
            print(f"   - ⚠️  ADJUST: Use {min_boundary-5:.0f}% - {max_boundary+5:.0f}%")
    
    # Save analysis to JSON
    output_file = "type3_analysis_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_characteristics, f, indent=2)
    print(f"\n✓ Detailed analysis saved to: {output_file}")


if __name__ == "__main__":
    analyze_all_type3_resumes()
