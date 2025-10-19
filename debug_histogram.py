#!/usr/bin/env python3
"""
Debug script to visualize histogram-based column detection.
Shows the vertical projection histogram and detected column boundaries.
"""

import sys
from pathlib import Path
from src.PDF_pipeline.get_words import get_words_from_pdf
from src.PDF_pipeline.histogram_column_detector import (
    compute_vertical_histogram,
    smooth_histogram,
    detect_valleys,
    detect_column_boundaries_histogram,
    visualize_histogram
)

def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_histogram.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    print(f"Analyzing: {pdf_path}\n")
    
    # Extract words
    pages = get_words_from_pdf(pdf_path)
    if not pages:
        print("No pages extracted!")
        return
    
    page = pages[0]
    words = page.get('words', [])
    page_width = page.get('page_width', 612)
    
    print(f"Page width: {page_width}")
    print(f"Total words: {len(words)}\n")
    
    # Compute histogram
    histogram = compute_vertical_histogram(words, page_width)
    smoothed = smooth_histogram(histogram, window_size=7)
    
    print(f"Histogram stats:")
    print(f"  Max density: {histogram.max()}")
    print(f"  Mean density: {histogram.mean():.2f}")
    print(f"  Non-zero bins: {(histogram > 0).sum()}/{len(histogram)}\n")
    
    # Detect valleys
    valleys = detect_valleys(smoothed, min_valley_width=10)
    print(f"Detected {len(valleys)} valleys:")
    for i, (start, end, depth) in enumerate(valleys):
        mid = (start + end) / 2
        width = end - start
        print(f"  Valley {i+1}: x={mid:.1f} (width={width}, depth={depth:.2f})")
    print()
    
    # Detect column boundaries
    boundaries = detect_column_boundaries_histogram(words, page_width, min_gap_width=15, smooth_window=7)
    print(f"Column boundaries ({len(boundaries)} columns):")
    for i, (x_start, x_end) in enumerate(boundaries):
        width = x_end - x_start
        words_in_col = sum(1 for w in words if x_start <= (w['x0'] + w['x1'])/2 < x_end)
        print(f"  Column {i+1}: x={x_start:.1f} to {x_end:.1f} (width={width:.1f}, {words_in_col} words)")
    print()
    
    # Visualize
    output_path = Path(pdf_path).stem + "_histogram.png"
    visualize_histogram(words, page_width, output_path=output_path)
    print(f"Visualization saved to: {output_path}")

if __name__ == "__main__":
    main()
