#!/usr/bin/env python3
"""
Debug script to visualize region-based layout detection.
Shows how the page is segmented into regions with different column structures.
"""

import sys
from pathlib import Path
from src.PDF_pipeline.get_words import get_words_from_pdf
from src.PDF_pipeline.region_detector import (
    segment_page_into_regions,
    visualize_regions,
    get_words_by_region_and_column
)


def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_regions.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    print(f"Analyzing: {pdf_path}\n")
    
    # Extract words
    pages = get_words_from_pdf(pdf_path)
    if not pages:
        print("No pages extracted!")
        return
    
    page = pages[0]
    print(f"Page dimensions: {page.get('page_width', 0):.0f} x {page.get('page_height', 0):.0f}")
    print(f"Total words: {len(page.get('words', []))}\n")
    
    # Segment into regions
    regions = segment_page_into_regions(page)
    
    print(f"Detected {len(regions)} region(s):\n")
    for idx, region in enumerate(regions):
        print(f"Region {idx + 1}:")
        print(f"  Y-range: {region.y_start:.0f} - {region.y_end:.0f} (height={region.y_end - region.y_start:.0f})")
        print(f"  Columns: {region.num_columns}")
        print(f"  Confidence: {region.confidence:.2f}")
        print(f"  Words: {len(region.words)}")
        print(f"  Column boundaries:")
        for col_idx, (x_start, x_end) in enumerate(region.column_boundaries):
            words_in_col = sum(1 for w in region.words 
                             if x_start <= (w['x0'] + w['x1'])/2 < x_end)
            print(f"    Column {col_idx + 1}: x={x_start:.0f}-{x_end:.0f} ({words_in_col} words)")
        print()
    
    # Get columns for pipeline
    columns = get_words_by_region_and_column(regions)
    print(f"Total columns for pipeline: {len(columns)}\n")
    
    # Visualize
    output_path = Path(pdf_path).stem + "_regions.png"
    visualize_regions(page, regions, output_path=output_path)


if __name__ == "__main__":
    main()
