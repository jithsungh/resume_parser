"""
Step 3: Layout Detection via Histograms
========================================
Detects document layout type using vertical projection histograms.

Layout Types:
1. Single-column (Type 1): One main peak in histogram
2. Multi-column (Type 2): Multiple peaks with valleys reaching 0
3. Hybrid/Complex (Type 3): Multiple peaks with valleys not reaching 0

Method:
- Compute vertical projection histogram (word count per x-position)
- Analyze peak structure to classify layout
- Identify column boundaries
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import numpy as np
from collections import defaultdict

from .word_extractor import WordMetadata


@dataclass
class LayoutType:
    """Layout detection result"""
    type: int  # 1=single, 2=multi, 3=hybrid
    type_name: str
    num_columns: int
    column_boundaries: List[Tuple[float, float]]  # List of (x_start, x_end)
    histogram: Dict[int, int]  # x_position -> word_count
    peaks: List[int]  # x positions of peaks
    valleys: List[int]  # x positions of valleys
    confidence: float
    page_width: float
    metadata: Dict[str, Any]


class LayoutDetector:
    """Detects page layout using adaptive histogram analysis with gap detection"""    
    def __init__(
        self,
        bin_width: int = 5,
        min_gap_width: float = 20,  # Minimum gap width to consider as column separator
        min_column_width: float = 80,  # Minimum width for a valid column
        adaptive_threshold: bool = True,  # Use adaptive thresholds based on page stats
        verbose: bool = False
    ):
        """
        Initialize layout detector with adaptive thresholds
        
        Args:
            bin_width: Width of histogram bins in points
            min_gap_width: Minimum gap width to split columns (points)
            min_column_width: Minimum width for a column to be valid (points)
            adaptive_threshold: Use adaptive thresholds based on content
            verbose: Print debug information
        """
        self.bin_width = bin_width
        self.min_gap_width = min_gap_width
        self.min_column_width = min_column_width
        self.adaptive_threshold = adaptive_threshold
        self.verbose = verbose
        # NEW: defaults used by older helpers if called
        self.min_peak_height = 3
        self.min_peak_distance = max(1, int(40 / max(1, self.bin_width)))
        self.valley_threshold = 0.3
    
    def detect_layout(self, words: List[WordMetadata], page_width: float = None) -> LayoutType:
        """
        Detect layout type for a page
        
        Args:
            words: List of WordMetadata for the page
            page_width: Width of page (auto-detected if None)
            
        Returns:
            LayoutType with detection results
        """
        if not words:
            return LayoutType(
                type=1,
                type_name="single-column",
                num_columns=1,
                column_boundaries=[(0, 612)],  # Default letter size
                histogram={},
                peaks=[],
                valleys=[],
                confidence=0.0,
                page_width=612,
                metadata={'error': 'No words provided'}
            )
        
        # Determine page width
        if page_width is None:
            page_width = max(word.bbox[2] for word in words) + 10
        if self.verbose:
            print(f"[LayoutDetector] Analyzing {len(words)} words, page width: {page_width:.1f}")
        
        # NEW ADAPTIVE APPROACH: Detect gaps directly from word positions
        column_boundaries = self._detect_columns_by_gaps(words, page_width)
        
        # Compute histogram for metadata/validation
        histogram = self._compute_histogram(words, page_width)
        smoothed_histogram = self._smooth_histogram(histogram)
        peaks = self._find_peaks_adaptive(smoothed_histogram, len(column_boundaries))
        valleys = self._find_valleys_adaptive(smoothed_histogram, column_boundaries)
        
        # Determine layout type
        num_columns = len(column_boundaries)
        if num_columns == 1:
            layout_type = 1
            confidence = 0.9
        elif num_columns == 2:
            layout_type = 2
            confidence = 0.85
        else:
            layout_type = 3
            confidence = 0.7
        
        type_names = {
            1: "single-column",
            2: "multi-column",
            3: "hybrid/complex"
        }
        
        result = LayoutType(
            type=layout_type,
            type_name=type_names.get(layout_type, "unknown"),
            num_columns=num_columns,
            column_boundaries=column_boundaries,
            histogram=histogram,
            peaks=peaks,
            valleys=valleys,
            confidence=confidence,
            page_width=page_width,
            metadata={
                'total_words': len(words),
                'peak_count': len(peaks),
                'valley_count': len(valleys),
                'max_histogram_value': max(histogram.values()) if histogram else 0
            }
        )
        
        if self.verbose:
            print(f"  Layout Type: {result.type_name} (Type {result.type})")
            print(f"  Columns: {result.num_columns}")
            print(f"  Confidence: {result.confidence:.1%}")
            print(f"  Peaks: {len(peaks)}, Valleys: {len(valleys)}")
        
        return result
    
    def _compute_histogram(self, words: List[WordMetadata], page_width: float) -> Dict[int, int]:
        """
        Compute vertical projection histogram
        
        Args:
            words: List of words
            page_width: Page width
            
        Returns:
            Dictionary mapping x-position bin to word count
        """
        histogram = defaultdict(int)
        
        num_bins = int(page_width / self.bin_width) + 1
        
        for word in words:
            # Use center of word
            x_center = word.x_center
            bin_idx = int(x_center / self.bin_width)
            
            if 0 <= bin_idx < num_bins:
                histogram[bin_idx] += 1
        
        return dict(histogram)
    
    def _smooth_histogram(self, histogram: Dict[int, int], window: int = 3) -> Dict[int, float]:
        """
        Smooth histogram using moving average
        
        Args:
            histogram: Raw histogram
            window: Window size for smoothing
            
        Returns:
            Smoothed histogram
        """
        if not histogram:
            return {}
        
        min_bin = min(histogram.keys())
        max_bin = max(histogram.keys())
        
        smoothed = {}
        
        for bin_idx in range(min_bin, max_bin + 1):
            # Get values in window
            values = []
            for offset in range(-window // 2, window // 2 + 1):
                values.append(histogram.get(bin_idx + offset, 0))
            
            # Average
            smoothed[bin_idx] = sum(values) / len(values)
        
        return smoothed
      
    def _detect_columns_by_gaps(self, words: List[WordMetadata], page_width: float) -> List[Tuple[float, float]]:
        """
        Detect column boundaries by finding vertical gaps in word positions.
        Uses adaptive thresholds based on page statistics.
        
        Args:
            words: List of words
            page_width: Page width
            
        Returns:
            List of (x_start, x_end) tuples for each column
        """
        if not words:
            return [(0, page_width)]
        
        # Step 1: Collect all x-positions and sort
        x_positions = []
        for word in words:
            x_positions.append((word.bbox[0], word.bbox[2]))  # (left, right) edges
        
        # Sort by left edge
        x_positions.sort(key=lambda x: x[0])
        
        # Step 2: Calculate adaptive gap threshold
        # Use statistics to determine what constitutes a "gap"
        gaps = []
        for i in range(len(x_positions) - 1):
            right_edge = x_positions[i][1]
            next_left_edge = x_positions[i + 1][0]
            gap = next_left_edge - right_edge
            if gap > 0:
                gaps.append(gap)
        
        if not gaps:
            return [(0, page_width)]
        
        # Calculate adaptive threshold
        gaps_sorted = sorted(gaps)
        median_gap = gaps_sorted[len(gaps_sorted) // 2]
        mean_gap = sum(gaps) / len(gaps)
        max_gap = max(gaps)
        
        # Adaptive threshold: use percentile-based approach
        # If there's a large gap (>= 75th percentile), it's likely a column separator
        percentile_75 = gaps_sorted[int(len(gaps_sorted) * 0.75)]
        percentile_90 = gaps_sorted[int(len(gaps_sorted) * 0.90)]
        percentile_60 = gaps_sorted[int(len(gaps_sorted) * 0.60)]
        
        # Dynamic threshold with rewards/penalties
        if self.adaptive_threshold:
            # Reward: If max gap is significantly larger than median (3x+), lower threshold
            if max_gap > median_gap * 3:
                gap_threshold = max(self.min_gap_width * 0.6, percentile_60)  # More aggressive for narrow columns
            # Penalty: If gaps are very uniform, require larger threshold
            elif max_gap < median_gap * 2:
                gap_threshold = max(self.min_gap_width * 1.5, percentile_90)
            else:
                gap_threshold = max(self.min_gap_width, percentile_75)
        else:
            gap_threshold = self.min_gap_width
        
        if self.verbose:
            print(f"    Gap analysis: median={median_gap:.1f}, p60={percentile_60:.1f}, p75={percentile_75:.1f}, "
                  f"p90={percentile_90:.1f}, max={max_gap:.1f}, threshold={gap_threshold:.1f}")
        
        # Step 3: Find significant gaps that could be column separators
        column_separators = []  # x-positions where columns split
        
        for i in range(len(x_positions) - 1):
            right_edge = x_positions[i][1]
            next_left_edge = x_positions[i + 1][0]
            gap = next_left_edge - right_edge
            
            # Check if gap is significant
            if gap >= gap_threshold:
                # Mark the mid-point of the gap as separator
                separator_x = (right_edge + next_left_edge) / 2
                column_separators.append(separator_x)
        
        # Step 3.5: FALLBACK - If no columns detected but there are large gaps, retry with reduced threshold
        if not column_separators and max_gap > self.min_gap_width * 0.5:
            # Use a more aggressive threshold for narrow-column layouts
            fallback_threshold = max(self.min_gap_width * 0.5, percentile_60)
            if self.verbose:
                print(f"    No columns found, trying fallback threshold: {fallback_threshold:.1f}")
            
            for i in range(len(x_positions) - 1):
                right_edge = x_positions[i][1]
                next_left_edge = x_positions[i + 1][0]
                gap = next_left_edge - right_edge
                
                if gap >= fallback_threshold:
                    separator_x = (right_edge + next_left_edge) / 2
                    column_separators.append(separator_x)
        
        if not column_separators:
            return [(0, page_width)]
        
        # Step 4: Merge close separators and create column boundaries
        # Filter out separators that are too close together
        merged_separators = []
        for sep in column_separators:
            if not merged_separators or (sep - merged_separators[-1]) >= self.min_column_width:
                merged_separators.append(sep)
        
        # Step 5: Create column boundaries
        column_boundaries = []
        
        if not merged_separators:
            return [(0, page_width)]
        
        # First column: from 0 to first separator
        x_start = 0
        for sep in merged_separators:
            if sep - x_start >= self.min_column_width:
                column_boundaries.append((x_start, sep))
                x_start = sep
        
        # Last column: from last separator to page width
        if page_width - x_start >= self.min_column_width:
            column_boundaries.append((x_start, page_width))
        elif column_boundaries:
            # Extend last column to page width
            column_boundaries[-1] = (column_boundaries[-1][0], page_width)
        else:
            # Fallback: single column
            column_boundaries = [(0, page_width)]
        
        if self.verbose:
            print(f"    Found {len(column_boundaries)} column(s) using gap analysis")
            for i, (x0, x1) in enumerate(column_boundaries):
                print(f"      Col {i+1}: x={x0:.1f} to {x1:.1f} (width={x1-x0:.1f})")
        
        return column_boundaries
    
    def _find_peaks_adaptive(self, histogram: Dict[int, float], num_expected_columns: int) -> List[int]:
        """
        Find peaks adaptively based on expected number of columns
        
        Args:
            histogram: Smoothed histogram
            num_expected_columns: Expected number of columns from gap analysis
            
        Returns:
            List of bin indices that are peaks
        """
        if not histogram:
            return []
        
        bins = sorted(histogram.keys())
        values = [histogram[b] for b in bins]
        
        if not values:
            return []
        
        # Adaptive threshold based on statistics
        max_val = max(values)
        mean_val = sum(values) / len(values)
        
        # Lower threshold if we expect multiple columns
        if num_expected_columns > 1:
            threshold = mean_val * 0.5
        else:
            threshold = mean_val * 0.8
        
        peaks = []
        for i in range(1, len(bins) - 1):
            if values[i] > values[i-1] and values[i] > values[i+1] and values[i] >= threshold:
                peaks.append(bins[i])
        
        return peaks
    
    def _find_valleys_adaptive(self, histogram: Dict[int, float], column_boundaries: List[Tuple[float, float]]) -> List[int]:
        """
        Find valleys based on column boundaries
        
        Args:
            histogram: Smoothed histogram
            column_boundaries: Column boundaries from gap analysis
            
        Returns:
            List of bin indices that are valleys
        """
        if len(column_boundaries) < 2:
            return []
        
        valleys = []
        
        # Valley is at the boundary between columns
        for i in range(len(column_boundaries) - 1):
            boundary_x = column_boundaries[i][1]
            valley_bin = int(boundary_x / self.bin_width)
            valleys.append(valley_bin)
        
        return valleys
    
    # Keep old methods for backward compatibility but mark as deprecated
    def _find_peaks(self, histogram: Dict[int, float]) -> List[int]:
        """
        Find peaks in histogram with minimum distance constraint
        
        Args:
            histogram: Smoothed histogram
            
        Returns:
            List of bin indices that are peaks
        """
        if not histogram:
            return []
        
        peaks = []
        bins = sorted(histogram.keys())
        
        for i in range(1, len(bins) - 1):
            curr_bin = bins[i]
            prev_bin = bins[i - 1]
            next_bin = bins[i + 1]
            
            curr_val = histogram[curr_bin]
            prev_val = histogram[prev_bin]
            next_val = histogram[next_bin]
            
            # Peak: higher than neighbors and above minimum
            if curr_val > prev_val and curr_val > next_val and curr_val >= self.min_peak_height:
                # Check distance from last peak
                if not peaks or (curr_bin - peaks[-1]) >= self.min_peak_distance:
                    peaks.append(curr_bin)
        
        return peaks
    
    def _find_valleys(self, histogram: Dict[int, float], peaks: List[int]) -> List[int]:
        """
        Find valleys in histogram (between peaks)
        
        Args:
            histogram: Smoothed histogram
            peaks: List of peak positions
            
        Returns:
            List of bin indices that are valleys
        """
        if len(peaks) < 2:
            return []
        
        valleys = []
        
        for i in range(len(peaks) - 1):
            peak1 = peaks[i]
            peak2 = peaks[i + 1]
            
            # Find minimum between peaks
            min_val = float('inf')
            min_bin = peak1
            
            for bin_idx in range(peak1, peak2 + 1):
                val = histogram.get(bin_idx, 0)
                if val < min_val:
                    min_val = val
                    min_bin = bin_idx
            
            valleys.append(min_bin)
        
        return valleys
    
    def _classify_layout(
        self,
        histogram: Dict[int, float],
        peaks: List[int],
        valleys: List[int],
        page_width: float
    ) -> Tuple[int, int, List[Tuple[float, float]], float]:
        """
        Classify layout type based on histogram analysis
        
        Args:
            histogram: Smoothed histogram
            peaks: Peak positions
            valleys: Valley positions
            page_width: Page width
            
        Returns:
            Tuple of (layout_type, num_columns, column_boundaries, confidence)
        """
        max_val = max(histogram.values()) if histogram else 1
        
        # Type 1: Single column
        if len(peaks) <= 1:
            return (
                1,  # type
                1,  # num_columns
                [(0, page_width)],  # column_boundaries
                0.9  # confidence
            )
        
        # Check valleys
        deep_valleys = []
        for valley_bin in valleys:
            valley_val = histogram.get(valley_bin, 0)
            
            # Deep valley: value < threshold * max
            if valley_val < self.valley_threshold * max_val:
                deep_valleys.append(valley_bin)
        
        # Filter valleys by minimum column width
        valid_valleys = []
        if deep_valleys:
            # Add start and end
            valley_x = [0] + [v * self.bin_width for v in deep_valleys] + [page_width]
            
            # Check each segment for minimum width
            for i in range(len(valley_x) - 1):
                width = valley_x[i + 1] - valley_x[i]
                if width >= self.min_column_width:
                    if i < len(deep_valleys):
                        valid_valleys.append(deep_valleys[i])
        
        # Type 2: Multi-column (valleys reach near 0 and create wide enough columns)
        if len(valid_valleys) >= 1:
            # Split at valid deep valleys
            column_boundaries = []
            
            # Convert bin indices to x-coordinates
            valley_x = [v * self.bin_width for v in valid_valleys]
            
            # Add boundaries
            x_start = 0
            for valley_x_pos in valley_x:
                if valley_x_pos - x_start >= self.min_column_width:
                    column_boundaries.append((x_start, valley_x_pos))
                    x_start = valley_x_pos
            
            # Last column
            if page_width - x_start >= self.min_column_width:
                column_boundaries.append((x_start, page_width))
            
            # If we have valid columns, return Type 2
            if len(column_boundaries) >= 2:
                return (
                    2,  # type
                    len(column_boundaries),  # num_columns
                    column_boundaries,
                    0.85  # confidence
                )
        
        # Type 3: Hybrid - check if peaks suggest multiple columns
        # Only if we have 2 distinct peaks and they're far enough apart
        if len(peaks) == 2:
            peak1_x = peaks[0] * self.bin_width
            peak2_x = peaks[1] * self.bin_width
            
            if peak2_x - peak1_x >= self.min_column_width * 1.5:
                mid_x = page_width / 2
                column_boundaries = [(0, mid_x), (mid_x, page_width)]
                return (
                    3,  # type
                    2,  # num_columns
                    column_boundaries,
                    0.7  # confidence
                )
        
        # Otherwise, treat as single column
        return (
            1,  # type
            1,  # num_columns
            [(0, page_width)],  # column_boundaries
            0.8  # confidence
        )


if __name__ == "__main__":
    import sys
    from .document_detector import DocumentDetector
    from .word_extractor import WordExtractor
    
    if len(sys.argv) < 2:
        print("Usage: python layout_detector.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    # Step 1: Detect document type
    print("Step 1: Document Detection")
    print("="*60)
    doc_detector = DocumentDetector(verbose=True)
    doc_type = doc_detector.detect(file_path)
    
    # Step 2: Extract words
    print("\nStep 2: Word Extraction")
    print("="*60)
    word_extractor = WordExtractor(verbose=True)
    
    if doc_type.file_type == 'pdf':
        if doc_type.recommended_extraction == 'ocr':
            pages = word_extractor.extract_pdf_ocr(file_path)
        else:
            pages = word_extractor.extract_pdf_text_based(file_path)
    elif doc_type.file_type == 'docx':
        pages = word_extractor.extract_docx(file_path)
    else:
        print("Unsupported file type")
        sys.exit(1)
    
    # Step 3: Detect layout for first page
    if pages and pages[0]:
        print("\nStep 3: Layout Detection (Page 1)")
        print("="*60)
        layout_detector = LayoutDetector(verbose=True)
        layout = layout_detector.detect_layout(pages[0])
        
        print(f"\nColumn Boundaries:")
        for i, (x_start, x_end) in enumerate(layout.column_boundaries, 1):
            print(f"  Column {i}: x={x_start:.1f} to {x_end:.1f} (width: {x_end - x_start:.1f})")
