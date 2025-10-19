"""
Histogram-based column detection for multi-column layouts.
Uses vertical projection histograms to detect column boundaries.
"""

import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from scipy.signal import find_peaks
from collections import Counter


def compute_vertical_histogram(words: List[Dict[str, Any]], page_width: float) -> np.ndarray:
    """
    Compute vertical projection histogram from word bounding boxes.
    Returns array where each index represents x-coordinate density.
    
    Args:
        words: List of word dictionaries with 'x0', 'x1', 'y0', 'y1'
        page_width: Width of the page
        
    Returns:
        numpy array of length int(page_width) with word density at each x position
    """
    bins = int(page_width)
    histogram = np.zeros(bins, dtype=int)
    
    for word in words:
        x0 = int(word.get('x0', 0))
        x1 = int(word.get('x1', 0))
        
        # Clip to page bounds
        x0 = max(0, min(x0, bins - 1))
        x1 = max(0, min(x1, bins - 1))
        
        # Fill histogram for this word's horizontal span
        histogram[x0:x1] += 1
    
    return histogram


def smooth_histogram(histogram: np.ndarray, window_size: int = 5) -> np.ndarray:
    """Apply moving average smoothing to reduce noise."""
    if window_size <= 1:
        return histogram
    
    kernel = np.ones(window_size) / window_size
    return np.convolve(histogram, kernel, mode='same')


def detect_valleys(histogram: np.ndarray, min_valley_width: int = 5) -> List[Tuple[int, int, float]]:
    """
    Detect valleys (gaps) in the histogram that likely represent column boundaries.
    
    Returns:
        List of (start_x, end_x, depth_ratio) tuples for each valley
    """
    valleys = []
    
    # Find local minima
    inverted = -histogram
    peaks, properties = find_peaks(inverted, distance=min_valley_width)
    
    if len(peaks) == 0:
        return valleys
    
    max_height = histogram.max()
    if max_height == 0:
        return valleys
    
    # Analyze each valley
    for peak_idx in peaks:
        valley_x = peak_idx
        valley_depth = histogram[valley_x]
        
        # Find valley boundaries (where it rises again)
        left = valley_x
        right = valley_x
        
        # Extend left
        while left > 0 and histogram[left] <= valley_depth * 1.5:
            left -= 1
        
        # Extend right
        while right < len(histogram) - 1 and histogram[right] <= valley_depth * 1.5:
            right += 1
        
        valley_width = right - left
        depth_ratio = 1.0 - (valley_depth / max_height)
        
        if valley_width >= min_valley_width and depth_ratio > 0.3:
            valleys.append((left, right, depth_ratio))
    
    return valleys


def detect_column_boundaries_histogram(
    words: List[Dict[str, Any]], 
    page_width: float,
    min_gap_width: int = 10,
    smooth_window: int = 5
) -> List[Tuple[float, float]]:
    """
    Detect column boundaries using vertical histogram analysis.
    
    Args:
        words: List of word dictionaries
        page_width: Width of the page
        min_gap_width: Minimum gap width to consider as column separator
        smooth_window: Smoothing window size
        
    Returns:
        List of (x_start, x_end) tuples representing column boundaries
    """
    if not words:
        return [(0, page_width)]
    
    # Compute histogram
    histogram = compute_vertical_histogram(words, page_width)
    
    # Smooth to reduce noise
    histogram = smooth_histogram(histogram, smooth_window)
    
    # Detect valleys (gaps between columns)
    valleys = detect_valleys(histogram, min_valley_width=min_gap_width)
    
    if not valleys:
        # No clear valleys - single column
        return [(0, page_width)]
    
    # Sort valleys by depth (strongest signals first)
    valleys.sort(key=lambda v: v[2], reverse=True)
    
    # Build column boundaries
    boundaries = []
    split_points = [0]
    
    for valley_start, valley_end, depth in valleys[:3]:  # Max 3 columns (2 gaps)
        # Use middle of valley as split point
        split_x = (valley_start + valley_end) // 2
        split_points.append(split_x)
    
    split_points.append(int(page_width))
    split_points.sort()
    
    # Create column ranges
    for i in range(len(split_points) - 1):
        boundaries.append((float(split_points[i]), float(split_points[i + 1])))
    
    return boundaries


def assign_words_to_histogram_columns(
    words: List[Dict[str, Any]],
    column_boundaries: List[Tuple[float, float]]
) -> List[List[Dict[str, Any]]]:
    """
    Assign words to columns based on histogram-detected boundaries.
    
    Args:
        words: List of word dictionaries
        column_boundaries: List of (x_start, x_end) tuples
        
    Returns:
        List of word lists, one per column
    """
    columns = [[] for _ in range(len(column_boundaries))]
    
    for word in words:
        x_mid = (word.get('x0', 0) + word.get('x1', 0)) / 2
        
        # Find which column this word belongs to
        for col_idx, (x_start, x_end) in enumerate(column_boundaries):
            if x_start <= x_mid < x_end:
                columns[col_idx].append(word)
                break
    
    return columns


def detect_columns_with_histogram(
    pages: List[Dict[str, Any]],
    min_gap_width: int = 15,
    smooth_window: int = 7,
    min_words_per_column: int = 10
) -> List[Dict[str, Any]]:
    """
    Main entry point: Detect columns using histogram analysis.
    
    Args:
        pages: List of page dictionaries with 'words' and 'page_width'
        min_gap_width: Minimum gap width to consider as column separator
        smooth_window: Smoothing window for histogram
        min_words_per_column: Minimum words required to consider a column valid
        
    Returns:
        List of column dictionaries with page, column_index, boundaries, words
    """
    all_columns = []
    global_column_index = 0
    
    for page_dict in pages:
        page_num = page_dict.get('page', 0)
        words = page_dict.get('words', [])
        page_width = page_dict.get('page_width', 612)  # Default letter width
        page_height = page_dict.get('page_height', 792)
        
        if not words:
            continue
        
        # Detect column boundaries
        boundaries = detect_column_boundaries_histogram(
            words, page_width, min_gap_width, smooth_window
        )
        
        # Assign words to columns
        column_words = assign_words_to_histogram_columns(words, boundaries)
        
        # Create column objects
        for col_idx, col_words in enumerate(column_words):
            if len(col_words) < min_words_per_column:
                continue
            
            x_start, x_end = boundaries[col_idx]
            
            all_columns.append({
                'page': page_num,
                'column_index': global_column_index,
                'boundaries': {
                    'x0': x_start,
                    'x1': x_end,
                    'y0': 0,
                    'y1': page_height,
                },
                'words': col_words,
                'num_words': len(col_words),
            })
            
            global_column_index += 1
    
    return all_columns


def visualize_histogram(
    words: List[Dict[str, Any]], 
    page_width: float,
    output_path: Optional[str] = None
) -> None:
    """
    Visualize the vertical histogram and detected valleys.
    Useful for debugging column detection.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed - skipping visualization")
        return
    
    histogram = compute_vertical_histogram(words, page_width)
    smoothed = smooth_histogram(histogram, window_size=7)
    valleys = detect_valleys(smoothed, min_valley_width=10)
    
    plt.figure(figsize=(12, 4))
    plt.plot(histogram, label='Raw histogram', alpha=0.5)
    plt.plot(smoothed, label='Smoothed histogram', linewidth=2)
    
    # Mark valleys
    for valley_start, valley_end, depth in valleys:
        valley_mid = (valley_start + valley_end) / 2
        plt.axvline(valley_mid, color='red', linestyle='--', alpha=0.7, label=f'Valley (depth={depth:.2f})')
        plt.axvspan(valley_start, valley_end, alpha=0.2, color='red')
    
    plt.xlabel('X Position (pixels)')
    plt.ylabel('Word Density')
    plt.title('Vertical Histogram - Column Detection')
    plt.legend()
    plt.grid(alpha=0.3)
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Histogram visualization saved to: {output_path}")
    else:
        plt.show()
    
    plt.close()
