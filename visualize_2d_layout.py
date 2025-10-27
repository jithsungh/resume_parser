"""
2D Layout Visualizer - Shows word positions in X-Y space
Helps identify multi-column layouts and complex arrangements
"""

import sys
from pathlib import Path
from collections import defaultdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.document_detector import DocumentDetector
from src.core.word_extractor import WordExtractor


def visualize_2d_layout(file_path: str):
    """Visualize word positions in 2D space"""
    print(f"Analyzing: {file_path}")
    print("=" * 80)
    
    # Extract words
    doc_detector = DocumentDetector()
    doc_type = doc_detector.detect(file_path)
    
    word_extractor = WordExtractor()
    if doc_type.recommended_extraction == 'ocr':
        pages = word_extractor.extract_pdf_ocr(file_path)
    else:
        pages = word_extractor.extract_pdf_text_based(file_path)
    
    if not pages or not pages[0]:
        print("No words found!")
        return
    
    words = pages[0]
    print(f"Total words: {len(words)}")
    
    # Get page dimensions
    page_width = max(w.bbox[2] for w in words)
    page_height = max(w.bbox[3] for w in words)
    
    print(f"Page dimensions: {page_width:.1f} x {page_height:.1f}")
    print()
    
    # Group words by Y-position (lines)
    lines = defaultdict(list)
    y_tolerance = 5  # Points tolerance for same line
    
    for word in words:
        y_center = (word.bbox[1] + word.bbox[3]) / 2
        # Find or create line
        found_line = False
        for line_y in list(lines.keys()):
            if abs(y_center - line_y) <= y_tolerance:
                lines[line_y].append(word)
                found_line = True
                break
        
        if not found_line:
            lines[y_center] = [word]
    
    # Sort lines by Y position
    sorted_lines = sorted(lines.items(), key=lambda x: x[0])
    
    print(f"Detected {len(sorted_lines)} lines")
    print()
    
    # Analyze line structure for multi-column detection
    print("Line Analysis (detecting multi-column patterns):")
    print("=" * 80)
    print("Format: [Line Y] X-range | Text sample")
    print()
    
    multi_column_candidates = []
    
    for i, (y_pos, line_words) in enumerate(sorted_lines[:50]):  # First 50 lines
        line_words.sort(key=lambda w: w.bbox[0])  # Sort by X
        
        x_min = min(w.bbox[0] for w in line_words)
        x_max = max(w.bbox[2] for w in line_words)
        x_range = x_max - x_min
        
        # Get text sample (first 60 chars)
        text_sample = ' '.join(w.text for w in line_words)[:60]
        
        # Check for gaps within the line (potential column separator)
        gaps = []
        for j in range(len(line_words) - 1):
            gap = line_words[j + 1].bbox[0] - line_words[j].bbox[2]
            if gap > 10:  # Significant gap
                gaps.append((gap, line_words[j].bbox[2], line_words[j + 1].bbox[0]))
        
        # Calculate X coverage (what % of page width is covered)
        coverage = (x_range / page_width) * 100
        
        # Detect potential multi-column indicator
        is_multi_col = False
        if gaps and max(g[0] for g in gaps) > 30:  # Large gap
            is_multi_col = True
            multi_column_candidates.append((y_pos, gaps, text_sample))
        
        indicator = " <-- MULTI-COL?" if is_multi_col else ""
        
        print(f"[{y_pos:6.1f}] x={x_min:5.1f}-{x_max:5.1f} ({coverage:5.1f}%) | {text_sample}{indicator}")
        
        if gaps and is_multi_col:
            for gap_size, gap_start, gap_end in gaps:
                print(f"          └─ Gap: {gap_size:.1f}pt at x={gap_start:.1f}-{gap_end:.1f}")
    
    print()
    
    if multi_column_candidates:
        print("=" * 80)
        print(f"FOUND {len(multi_column_candidates)} lines with potential column structure!")
        print()
        print("These lines have large horizontal gaps suggesting side-by-side content:")
        for y_pos, gaps, text_sample in multi_column_candidates[:10]:
            max_gap = max(g[0] for g in gaps)
            print(f"  Y={y_pos:.1f}, Max gap={max_gap:.1f}pt: {text_sample}")
    else:
        print("=" * 80)
        print("NO multi-column structure detected.")
        print("This appears to be a single-column layout.")
    
    print()
    
    # Check for "type 3" pattern: alternating left/right content
    print("Checking for Type 3 (Hybrid) Pattern:")
    print("=" * 80)
    
    # Group lines by X-start position
    left_column_lines = []  # Lines starting on left side
    right_column_lines = []  # Lines starting on right side
    full_width_lines = []  # Lines spanning full width
    
    mid_x = page_width / 2
    
    for y_pos, line_words in sorted_lines:
        line_words.sort(key=lambda w: w.bbox[0])
        x_start = line_words[0].bbox[0]
        x_end = line_words[-1].bbox[2]
        width = x_end - x_start
        
        if width > page_width * 0.8:  # Spans >80% of page
            full_width_lines.append((y_pos, line_words))
        elif x_start < mid_x * 0.5:  # Starts on left third
            if x_end < mid_x * 1.2:  # Doesn't extend far right
                left_column_lines.append((y_pos, line_words))
            else:
                full_width_lines.append((y_pos, line_words))
        elif x_start > mid_x * 0.8:  # Starts on right side
            right_column_lines.append((y_pos, line_words))
        else:
            full_width_lines.append((y_pos, line_words))
    
    print(f"Left-column lines: {len(left_column_lines)}")
    print(f"Right-column lines: {len(right_column_lines)}")
    print(f"Full-width lines: {len(full_width_lines)}")
    print()
    
    if left_column_lines and right_column_lines:
        # Check if left and right have overlapping Y ranges
        left_y_range = (min(y for y, _ in left_column_lines), max(y for y, _ in left_column_lines))
        right_y_range = (min(y for y, _ in right_column_lines), max(y for y, _ in right_column_lines))
        
        overlap = not (left_y_range[1] < right_y_range[0] or right_y_range[1] < left_y_range[0])
        
        if overlap:
            print("✓ TYPE 3 DETECTED: Side-by-side columns with overlapping Y-ranges!")
            print(f"  Left column Y-range: {left_y_range[0]:.1f} - {left_y_range[1]:.1f}")
            print(f"  Right column Y-range: {right_y_range[0]:.1f} - {right_y_range[1]:.1f}")
            
            # Find column boundary
            left_x_max = max(max(w.bbox[2] for w in words) for _, words in left_column_lines)
            right_x_min = min(min(w.bbox[0] for w in words) for _, words in right_column_lines)
            col_boundary = (left_x_max + right_x_min) / 2
            
            print(f"  Column boundary at: x={col_boundary:.1f}")
            print(f"  Gap between columns: {right_x_min - left_x_max:.1f}pt")
        else:
            print("✗ Sequential layout: Left and right columns don't overlap vertically")
    else:
        print("✗ No multi-column pattern detected")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python visualize_2d_layout.py <pdf_file>")
        sys.exit(1)
    
    visualize_2d_layout(sys.argv[1])
