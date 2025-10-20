"""
Region-based Layout Detector for Hybrid Resume Layouts
=======================================================

Detects hybrid layouts where different regions of the page have different column structures.
Example:
- Top 25%: Single column (name, contact, summary)
- Bottom 75%: Two columns (experience | skills, projects, education)

Strategy:
1. Detect horizontal separator lines (actual lines or whitespace gaps)
2. Segment page into regions based on Y-coordinates
3. Analyze each region for column structure using histogram
4. Return region boundaries with column configuration
"""

import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Region:
    """Represents a horizontal region of the page."""
    y_start: float
    y_end: float
    num_columns: int
    column_boundaries: List[Tuple[float, float]]
    confidence: float
    words: List[Dict[str, Any]]
    
    def __repr__(self):
        return f"Region(y={self.y_start:.0f}-{self.y_end:.0f}, cols={self.num_columns}, conf={self.confidence:.2f})"


def detect_horizontal_lines(page_dict: Dict[str, Any], min_line_width: float = 100) -> List[float]:
    """
    Detect horizontal separator lines in the PDF.
    
    Args:
        page_dict: Page dictionary (may contain 'drawings' or 'lines')
        min_line_width: Minimum width to consider a line as separator
        
    Returns:
        List of Y-coordinates where horizontal lines are found
    """
    import fitz
    
    lines = []
    
    # Try to get lines from drawings (pdfplumber format)
    if 'drawings' in page_dict:
        for drawing in page_dict.get('drawings', []):
            # Check if it's a horizontal line
            if drawing.get('type') == 'line':
                y0, y1 = drawing.get('y0', 0), drawing.get('y1', 0)
                x0, x1 = drawing.get('x0', 0), drawing.get('x1', 0)
                
                width = abs(x1 - x0)
                height = abs(y1 - y0)
                
                # Horizontal line: width >> height
                if width > min_line_width and height < 5:
                    y_pos = (y0 + y1) / 2
                    lines.append(y_pos)
    
    # Also check for explicit lines from PyMuPDF
    if 'lines' in page_dict:
        for line in page_dict.get('lines', []):
            x0, y0, x1, y1 = line[:4]
            width = abs(x1 - x0)
            height = abs(y1 - y0)
            
            if width > min_line_width and height < 5:
                y_pos = (y0 + y1) / 2
                lines.append(y_pos)
    
    return sorted(set(lines))


def detect_whitespace_gaps(words: List[Dict[str, Any]], min_gap_height: float = 20) -> List[float]:
    """
    Detect large vertical whitespace gaps that likely separate regions.
    
    Args:
        words: List of word dictionaries with y0, y1
        min_gap_height: Minimum gap height to consider as separator
        
    Returns:
        List of Y-coordinates (middle of gaps) where whitespace separators are found
    """
    if not words:
        return []
    
    # Sort words by vertical position
    words_sorted = sorted(words, key=lambda w: w.get('y0', 0))
    
    gaps = []
    for i in range(len(words_sorted) - 1):
        current_bottom = words_sorted[i].get('y1', 0)
        next_top = words_sorted[i + 1].get('y0', 0)
        
        gap_height = next_top - current_bottom
        
        if gap_height >= min_gap_height:
            gap_mid = (current_bottom + next_top) / 2
            gaps.append(gap_mid)
    
    return gaps


def compute_vertical_histogram_for_region(
    words: List[Dict[str, Any]], 
    page_width: float,
    y_start: float,
    y_end: float
) -> np.ndarray:
    """
    Compute vertical histogram for words within a specific Y-range.
    
    Args:
        words: List of all words on page
        page_width: Page width
        y_start: Top of region
        y_end: Bottom of region
        
    Returns:
        Histogram array for the region
    """
    from src.PDF_pipeline.histogram_column_detector import compute_vertical_histogram
    
    # Filter words within region
    region_words = [
        w for w in words 
        if y_start <= w.get('y0', 0) <= y_end or y_start <= w.get('y1', 0) <= y_end
    ]
    
    return compute_vertical_histogram(region_words, page_width)


def analyze_region_columns(
    words: List[Dict[str, Any]],
    page_width: float,
    y_start: float,
    y_end: float,
    smooth_window: int = 7,
    min_gap_width: int = 15
) -> Tuple[int, List[Tuple[float, float]], float]:
    """
    Analyze column structure within a specific region.
    
    Args:
        words: All words on page
        page_width: Page width
        y_start: Region top
        y_end: Region bottom
        smooth_window: Histogram smoothing window
        min_gap_width: Minimum gap to detect column separator
        
    Returns:
        (num_columns, column_boundaries, confidence)
    """
    from src.PDF_pipeline.histogram_column_detector import (
        smooth_histogram,
        detect_valleys,
        detect_column_boundaries_histogram
    )
    
    # Get words in this region
    region_words = [
        w for w in words 
        if y_start <= w.get('y0', 0) <= y_end or y_start <= w.get('y1', 0) <= y_end
    ]
    
    if len(region_words) < 10:
        # Too few words, assume single column
        return 1, [(0, page_width)], 0.5
      # Detect column boundaries
    boundaries = detect_column_boundaries_histogram(
        region_words, page_width, min_gap_width, smooth_window
    )
    
    # Filter out narrow columns (likely false positives from margins/gaps)
    MIN_COLUMN_WIDTH = 80  # Minimum 80px width for valid column
    MIN_WORDS_PER_COLUMN = 15  # Minimum 15 words per column
    
    filtered_boundaries = []
    for x_start, x_end in boundaries:
        col_width = x_end - x_start
        words_in_col = [
            w for w in region_words 
            if x_start <= (w.get('x0', 0) + w.get('x1', 0)) / 2 < x_end
        ]
        
        if col_width >= MIN_COLUMN_WIDTH and len(words_in_col) >= MIN_WORDS_PER_COLUMN:
            filtered_boundaries.append((x_start, x_end))
    
    # If filtering removed all columns, fall back to single column
    if not filtered_boundaries:
        filtered_boundaries = [(0, page_width)]
    
    boundaries = filtered_boundaries
    num_columns = len(boundaries)
    
    # Compute confidence based on valley depth
    histogram = compute_vertical_histogram_for_region(region_words, page_width, y_start, y_end)
    smoothed = smooth_histogram(histogram, smooth_window)
    valleys = detect_valleys(smoothed, min_valley_width=min_gap_width)
    
    if num_columns == 1:
        confidence = 0.9 if not valleys else 0.6
    else:
        # Confidence based on strongest valley depth
        if valleys:
            max_depth = max(v[2] for v in valleys)
            confidence = min(0.95, max_depth)
        else:
            confidence = 0.5
    
    return num_columns, boundaries, confidence


def segment_page_into_regions(
    page_dict: Dict[str, Any],
    min_region_height: float = 50,
    max_regions: int = 5
) -> List[Region]:
    """
    Segment page into horizontal regions based on separators and column analysis.
    
    Strategy:
    1. Detect horizontal lines and whitespace gaps
    2. Merge nearby separators (within 10px)
    3. Create region candidates
    4. Analyze each region for column structure
    5. Merge regions with same column structure if adjacent
    
    Args:
        page_dict: Page dictionary with words, width, height
        min_region_height: Minimum height for a region
        max_regions: Maximum number of regions to detect
        
    Returns:
        List of Region objects
    """
    words = page_dict.get('words', [])
    page_width = page_dict.get('page_width', 612)
    page_height = page_dict.get('page_height', 792)
    
    if not words:
        return [Region(
            y_start=0,
            y_end=page_height,
            num_columns=1,
            column_boundaries=[(0, page_width)],
            confidence=1.0,
            words=[]
        )]
    
    # Step 1: Detect separators
    horizontal_lines = detect_horizontal_lines(page_dict)
    whitespace_gaps = detect_whitespace_gaps(words, min_gap_height=30)
    
    # Combine and deduplicate separators (merge within 10px)
    all_separators = sorted(horizontal_lines + whitespace_gaps)
    merged_separators = []
    
    if all_separators:
        current = all_separators[0]
        for sep in all_separators[1:]:
            if sep - current < 10:
                current = (current + sep) / 2  # Average
            else:
                merged_separators.append(current)
                current = sep
        merged_separators.append(current)
    
    # Step 2: Create region boundaries
    region_boundaries = [0] + merged_separators + [page_height]
    
    # Step 3: Analyze each region
    regions = []
    for i in range(len(region_boundaries) - 1):
        y_start = region_boundaries[i]
        y_end = region_boundaries[i + 1]
        
        height = y_end - y_start
        if height < min_region_height:
            continue
        
        # Analyze column structure
        num_cols, col_bounds, confidence = analyze_region_columns(
            words, page_width, y_start, y_end
        )
        
        # Get words in region
        region_words = [
            w for w in words
            if y_start <= w.get('y0', 0) <= y_end or y_start <= w.get('y1', 0) <= y_end
        ]
        
        regions.append(Region(
            y_start=y_start,
            y_end=y_end,
            num_columns=num_cols,
            column_boundaries=col_bounds,
            confidence=confidence,
            words=region_words
        ))
    
    # Step 4: Merge adjacent regions with same column structure
    if len(regions) > 1:
        merged = []
        current_region = regions[0]
        
        for next_region in regions[1:]:
            # Merge if same column count and high confidence
            if (current_region.num_columns == next_region.num_columns and 
                current_region.confidence > 0.7 and next_region.confidence > 0.7):
                # Merge
                current_region = Region(
                    y_start=current_region.y_start,
                    y_end=next_region.y_end,
                    num_columns=current_region.num_columns,
                    column_boundaries=current_region.column_boundaries,
                    confidence=(current_region.confidence + next_region.confidence) / 2,
                    words=current_region.words + next_region.words
                )
            else:
                merged.append(current_region)
                current_region = next_region
        
        merged.append(current_region)
        regions = merged
    
    # Step 5: Limit to max_regions (keep largest ones)
    if len(regions) > max_regions:
        regions.sort(key=lambda r: len(r.words), reverse=True)
        regions = regions[:max_regions]
        regions.sort(key=lambda r: r.y_start)
    
    return regions


def visualize_regions(
    page_dict: Dict[str, Any],
    regions: List[Region],
    output_path: Optional[str] = None
) -> None:
    """
    Visualize detected regions and their column boundaries.
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
    except ImportError:
        print("matplotlib not installed - skipping visualization")
        return
    
    page_width = page_dict.get('page_width', 612)
    page_height = page_dict.get('page_height', 792)
    
    fig, ax = plt.subplots(figsize=(10, 14))
    
    # Draw page boundary
    ax.add_patch(patches.Rectangle((0, 0), page_width, page_height, 
                                   linewidth=2, edgecolor='black', facecolor='white'))
    
    # Color palette for regions
    colors = ['lightblue', 'lightgreen', 'lightyellow', 'lightcoral', 'lightpink']
    
    # Draw regions
    for idx, region in enumerate(regions):
        color = colors[idx % len(colors)]
        
        # Draw region background
        ax.add_patch(patches.Rectangle(
            (0, region.y_start), 
            page_width, 
            region.y_end - region.y_start,
            linewidth=2, 
            edgecolor='blue', 
            facecolor=color,
            alpha=0.3
        ))
        
        # Draw column boundaries
        for col_idx, (x_start, x_end) in enumerate(region.column_boundaries):
            ax.add_patch(patches.Rectangle(
                (x_start, region.y_start),
                x_end - x_start,
                region.y_end - region.y_start,
                linewidth=1,
                edgecolor='red',
                facecolor='none',
                linestyle='--'
            ))
            
            # Label column
            mid_x = (x_start + x_end) / 2
            mid_y = (region.y_start + region.y_end) / 2
            ax.text(mid_x, mid_y, f'R{idx+1}C{col_idx+1}', 
                   ha='center', va='center', fontsize=10, fontweight='bold')
        
        # Label region info
        ax.text(5, region.y_start + 10, 
               f'Region {idx+1}: {region.num_columns} col(s), conf={region.confidence:.2f}',
               fontsize=9, color='darkblue', fontweight='bold',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    ax.set_xlim(0, page_width)
    ax.set_ylim(0, page_height)
    ax.invert_yaxis()  # PDF coordinates start from top
    ax.set_aspect('equal')
    ax.set_title('Region-based Layout Detection', fontsize=14, fontweight='bold')
    ax.set_xlabel('X Position (pixels)')
    ax.set_ylabel('Y Position (pixels)')
    ax.grid(alpha=0.2)
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Region visualization saved to: {output_path}")
    else:
        plt.show()
    
    plt.close()


def get_words_by_region_and_column(regions: List[Region]) -> List[Dict[str, Any]]:
    """
    Convert regions into column format for the existing pipeline.
    
    Returns:
        List of column dictionaries compatible with the pipeline
    """
    all_columns = []
    global_column_index = 0
    
    for region_idx, region in enumerate(regions):
        # For each column in this region
        for col_idx, (x_start, x_end) in enumerate(region.column_boundaries):
            # Filter words in this column
            col_words = [
                w for w in region.words
                if x_start <= (w.get('x0', 0) + w.get('x1', 0)) / 2 < x_end
            ]
            
            if len(col_words) < 5:
                continue
            
            all_columns.append({
                'page': region.words[0].get('page', 0) if region.words else 0,
                'column_index': global_column_index,
                'region_index': region_idx,
                'boundaries': {
                    'x0': x_start,
                    'x1': x_end,
                    'y0': region.y_start,
                    'y1': region.y_end,
                },
                'words': col_words,
                'num_words': len(col_words),
            })
            
            global_column_index += 1
    
    return all_columns
