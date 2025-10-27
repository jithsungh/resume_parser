"""
Visualize word distribution to understand narrow column layouts
"""
import sys
from src.core.document_detector import DocumentDetector
from src.core.word_extractor import WordExtractor
import numpy as np

def visualize_word_distribution(pdf_path):
    """Visualize horizontal word distribution"""
    print(f"Analyzing: {pdf_path}")
    print("="*80)
    
    # Extract words
    doc_detector = DocumentDetector()
    doc_type = doc_detector.detect(pdf_path)
    
    word_extractor = WordExtractor()
    if doc_type.recommended_extraction == 'ocr':
        pages = word_extractor.extract_pdf_ocr(pdf_path)
    else:
        pages = word_extractor.extract_pdf_text_based(pdf_path)
    
    if not pages or not pages[0]:
        print("No words extracted!")
        return
    
    words = pages[0]
    print(f"Total words: {len(words)}")
    
    # Collect x-positions (left edges)
    x_lefts = sorted([w.bbox[0] for w in words])
    x_rights = sorted([w.bbox[2] for w in words])
    
    page_width = max(x_rights) + 10
    
    print(f"Page width: {page_width:.1f}")
    print(f"X-range: {min(x_lefts):.1f} to {max(x_rights):.1f}")
    print()
    
    # Create a simple ASCII histogram
    bins = 60  # Number of bins for visualization
    bin_width = page_width / bins
    histogram = [0] * bins
    
    for word in words:
        x_center = (word.bbox[0] + word.bbox[2]) / 2
        bin_idx = int(x_center / bin_width)
        if 0 <= bin_idx < bins:
            histogram[bin_idx] += 1
    
    max_count = max(histogram) if histogram else 1
    
    print("Horizontal Word Distribution (ASCII Histogram):")
    print("="*80)
    print("X-axis: page width (left to right)")
    print("Y-axis: word count (scaled)")
    print()
    
    # Print histogram
    for row in range(20, 0, -1):
        line = ""
        threshold = (row / 20.0) * max_count
        for count in histogram:
            if count >= threshold:
                line += "█"
            elif count >= threshold * 0.5:
                line += "▓"
            elif count >= threshold * 0.25:
                line += "▒"
            elif count > 0:
                line += "░"
            else:
                line += " "
        print(line)
    
    print("-" * bins)
    print("0" + " " * (bins//2 - 5) + f"{page_width/2:.0f}" + " " * (bins//2 - 5) + f"{page_width:.0f}")
    print()
    
    # Analyze gaps
    print("Gap Analysis:")
    print("="*80)
    
    x_positions = sorted([(w.bbox[0], w.bbox[2]) for w in words])
    gaps = []
    
    for i in range(len(x_positions) - 1):
        right_edge = x_positions[i][1]
        next_left_edge = x_positions[i + 1][0]
        gap = next_left_edge - right_edge
        if gap > 0:
            gaps.append((gap, right_edge, next_left_edge))
    
    gaps_sorted = sorted(gaps, reverse=True)
    
    print(f"Total gaps: {len(gaps)}")
    print(f"Top 20 largest gaps:")
    for i, (gap, right, left) in enumerate(gaps_sorted[:20], 1):
        mid = (right + left) / 2
        print(f"  {i:2d}. Gap: {gap:6.2f}pt at x={mid:6.1f} (between {right:.1f} and {left:.1f})")
    
    if gaps:
        gaps_values = [g[0] for g in gaps]
        print(f"\nGap statistics:")
        print(f"  Min: {min(gaps_values):.2f}")
        print(f"  Max: {max(gaps_values):.2f}")
        print(f"  Mean: {np.mean(gaps_values):.2f}")
        print(f"  Median: {np.median(gaps_values):.2f}")
        print(f"  P75: {np.percentile(gaps_values, 75):.2f}")
        print(f"  P90: {np.percentile(gaps_values, 90):.2f}")
        print(f"  P95: {np.percentile(gaps_values, 95):.2f}")
        print(f"  P99: {np.percentile(gaps_values, 99):.2f}")
    
    # Look for consistent vertical gaps (column separators)
    print(f"\nLooking for consistent vertical gaps (potential column separators):")
    print("="*80)
    
    # Group gaps by x-position (within 5pt tolerance)
    gap_groups = {}
    for gap, right, left in gaps:
        mid = (right + left) / 2
        
        # Find if this mid-point is close to an existing group
        found_group = False
        for group_mid in list(gap_groups.keys()):
            if abs(mid - group_mid) < 5:
                gap_groups[group_mid].append(gap)
                found_group = True
                break
        
        if not found_group:
            gap_groups[mid] = [gap]
    
    # Find groups with many gaps (consistent vertical spacing)
    consistent_gaps = [(mid, gaps) for mid, gaps in gap_groups.items() if len(gaps) >= 3]
    consistent_gaps.sort(key=lambda x: len(x[1]), reverse=True)
    
    if consistent_gaps:
        print(f"Found {len(consistent_gaps)} locations with consistent gaps:")
        for i, (mid, gap_list) in enumerate(consistent_gaps[:10], 1):
            avg_gap = np.mean(gap_list)
            print(f"  {i:2d}. x={mid:6.1f}: {len(gap_list)} gaps, avg={avg_gap:.2f}pt, range=[{min(gap_list):.2f}, {max(gap_list):.2f}]")
    else:
        print("No consistent vertical gaps found - likely single column layout")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python visualize_word_distribution.py <pdf_path>")
        sys.exit(1)
    
    visualize_word_distribution(sys.argv[1])
