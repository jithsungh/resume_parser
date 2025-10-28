"""
Enhanced Layout Detection with Y-Overlap Analysis
==================================================
Detects Type 3 (hybrid/complex) layouts where columns have overlapping Y-ranges
but are separated vertically (side-by-side content at same Y-level).

This solves the problem where gap-based detection fails because:
1. PDF extraction reads left-to-right, linearizing columns
2. No horizontal gaps exist between consecutive words
3. But columns are actually side-by-side visually
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict

from .word_extractor import WordMetadata
from .layout_detector_histogram import LayoutDetector as BaseLayoutDetector, LayoutType


class EnhancedLayoutDetector(BaseLayoutDetector):
    """
    Enhanced layout detector that uses Y-overlap analysis for Type 3 detection
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.y_tolerance = 5  # Points tolerance for same line
    
    def detect_layout(self, words: List[WordMetadata], page_width: float = None) -> LayoutType:
        """
        Enhanced layout detection with proper Type 1/2/3 classification
        
        Type 1: Single column (horizontal flow)
        Type 2: Clean vertical columns with clear gaps (valleys reach ~0)
        Type 3: Complex - vertical columns PLUS horizontal sections (valleys don't reach 0)
        
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
                column_boundaries=[(0, 612)],
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
            print(f"[EnhancedLayoutDetector] Analyzing {len(words)} words, page width: {page_width:.1f}")
        
        # Step 1: Try Y-overlap analysis for column detection
        column_boundaries, detection_method = self._detect_columns_by_y_overlap(words, page_width)
        
        # Step 2: FALLBACK - Try gap-based detection
        if len(column_boundaries) == 1:
            gap_boundaries = self._detect_columns_by_gaps(words, page_width)
            if len(gap_boundaries) > 1:
                column_boundaries = gap_boundaries
                detection_method = 'gap'
                if self.verbose:
                    print(f"  Using gap-based detection: {len(column_boundaries)} columns")
        else:
            if self.verbose:
                print(f"  Using Y-overlap detection: {len(column_boundaries)} columns")
        
        # Step 3: Compute histogram for ALL words
        histogram = self._compute_histogram(words, page_width)
        smoothed_histogram = self._smooth_histogram(histogram)
        peaks = self._find_peaks_adaptive(smoothed_histogram, len(column_boundaries))
        valleys = self._find_valleys_adaptive(smoothed_histogram, column_boundaries)
        
        # Step 4: Classify as Type 1, 2, or 3 based on histogram analysis
        num_columns = len(column_boundaries)
        layout_type, type_name, confidence = self._classify_layout_type(
            words, column_boundaries, histogram, smoothed_histogram, 
            peaks, valleys, page_width, detection_method
        )
        
        result = LayoutType(
            type=layout_type,
            type_name=type_name,
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
                'max_histogram_value': max(histogram.values()) if histogram else 0,
                'detection_method': detection_method
            }
        )
        
        if self.verbose:
            print(f"  Layout Type: {result.type_name} (Type {result.type})")
            print(f"  Columns: {result.num_columns}")
            print(f"  Confidence: {result.confidence:.1%}")
        
        return result
    
    def _classify_layout_type(
        self,
        words: List[WordMetadata],
        column_boundaries: List[Tuple[float, float]],
        histogram: Dict[int, int],
        smoothed_histogram: Dict[int, float],
        peaks: List[int],
        valleys: List[int],
        page_width: float,
        detection_method: str
    ) -> Tuple[int, str, float]:
        """
        Classify layout as Type 1, 2, or 3 using multiple signals
        
        Type 1: Single column (horizontal flow)
        Type 2: Clean vertical columns - balanced, newspaper-style
        Type 3: Complex/hybrid - unbalanced columns (sidebar + main), mixed with horizontal sections
        
        Key differences between Type 2 and Type 3:
        - Type 2: Balanced columns (similar widths/content), clean gaps
        - Type 3: Unbalanced (sidebar + main content), often with horizontal headers
        
        Returns:
            Tuple of (layout_type, type_name, confidence)
        """
        num_columns = len(column_boundaries)
        
        # Type 1: Single column
        if num_columns == 1:
            return 1, "single-column", 0.9
        
        # For multi-column layouts, use multiple signals to distinguish Type 2 vs Type 3
        
        # Signal 1: Column balance (width ratio)
        col_widths = [end - start for start, end in column_boundaries]
        width_ratio = min(col_widths) / max(col_widths) if max(col_widths) > 0 else 0
        is_balanced = width_ratio > 0.6  # Balanced if columns within 60% of each other
        
        # Signal 2: Check for horizontal sections by analyzing line distribution
        lines = self._group_words_into_lines(words)
        full_width_lines = 0
        for y_pos, line_words in lines:
            line_words.sort(key=lambda w: w.bbox[0])
            x_start = line_words[0].bbox[0]
            x_end = line_words[-1].bbox[2]
            width = x_end - x_start
            if width > page_width * 0.75:  # Spans >75% of page
                full_width_lines += 1
        
        has_horizontal_sections = full_width_lines >= 3  # At least 3 full-width lines
        
        # Signal 3: Valley depth analysis
        valley_depth_ratio = 1.0  # Default: no clear valley
        if smoothed_histogram and len(peaks) >= 2:
            max_val = max(smoothed_histogram.values())
            
            # Find deepest valley between peaks
            valley_values = []
            for i in range(len(peaks) - 1):
                peak1 = peaks[i]
                peak2 = peaks[i + 1]
                
                # Find minimum between peaks
                min_val = float('inf')
                for bin_idx in range(peak1, peak2 + 1):
                    val = smoothed_histogram.get(bin_idx, 0)
                    if val < min_val:
                        min_val = val
                
                valley_values.append(min_val)
            
            if valley_values:
                deepest_valley = min(valley_values)
                valley_depth_ratio = deepest_valley / max_val if max_val > 0 else 1.0
        
        if self.verbose:
            print(f"    Type 2/3 signals:")
            print(f"      - Width ratio: {width_ratio:.2f} (balanced={is_balanced})")
            print(f"      - Full-width lines: {full_width_lines} (has_horizontal={has_horizontal_sections})")
            print(f"      - Valley ratio: {valley_depth_ratio:.2%}")
            print(f"      - Detection method: {detection_method}")
        
        # Decision logic:
        # Type 3 if ANY of:
        #   1. Detected via Y-overlap method (indicates side-by-side at same Y-level)
        #   2. Unbalanced columns (sidebar + main content pattern)
        #   3. Has horizontal sections mixed with columns
        #   4. Valley doesn't reach near 0 (ratio >= 0.20)
        
        is_type3 = (
            detection_method == 'y_overlap' or
            not is_balanced or
            has_horizontal_sections or
            valley_depth_ratio >= 0.20
        )
        
        if is_type3:
            return 3, "hybrid/complex", 0.80
        else:
            return 2, "multi-column", 0.85
    
    def _detect_columns_by_y_overlap(self, words: List[WordMetadata], page_width: float) -> Tuple[List[Tuple[float, float]], str]:
        """
        Detect columns by analyzing Y-overlap patterns.
        
        Type 3 layouts have:
        1. Left column: Lines starting on left side
        2. Right column: Lines starting on right side
        3. Overlapping Y-ranges (side-by-side content)
        
        Args:
            words: List of words
            page_width: Page width
            
        Returns:
            Tuple of (column_boundaries, detection_method)
        """
        if not words or len(words) < 10:
            return [(0, page_width)], 'single_column'
        
        # Group words into lines by Y-position
        lines = self._group_words_into_lines(words)
        
        if len(lines) < 3:
            return [(0, page_width)], 'single_column'
        
        # Analyze line structure
        mid_x = page_width / 2
        left_lines = []  # Lines starting on left
        right_lines = []  # Lines starting on right
        full_width_lines = []  # Lines spanning full width
        
        for y_pos, line_words in lines:
            line_words.sort(key=lambda w: w.bbox[0])
            x_start = line_words[0].bbox[0]
            x_end = line_words[-1].bbox[2]
            width = x_end - x_start
            
            # Classify line based on position and width
            if width > page_width * 0.75:  # Spans >75% of page
                full_width_lines.append((y_pos, x_start, x_end, line_words))
            elif x_start < mid_x * 0.6:  # Starts on left side
                if x_end < mid_x * 1.3:  # Doesn't extend too far right
                    left_lines.append((y_pos, x_start, x_end, line_words))
                else:
                    full_width_lines.append((y_pos, x_start, x_end, line_words))
            elif x_start > mid_x * 0.7:  # Starts on right side
                right_lines.append((y_pos, x_start, x_end, line_words))
            else:
                full_width_lines.append((y_pos, x_start, x_end, line_words))
        
        if self.verbose:
            print(f"    Line classification: {len(left_lines)} left, {len(right_lines)} right, {len(full_width_lines)} full-width")          # Check for Type 3 pattern: left and right columns with overlapping Y-ranges
        if len(left_lines) >= 3 and len(right_lines) >= 3:
            left_y_min = min(y for y, _, _, _ in left_lines)
            left_y_max = max(y for y, _, _, _ in left_lines)
            right_y_min = min(y for y, _, _, _ in right_lines)
            right_y_max = max(y for y, _, _, _ in right_lines)
            
            # Check for Y-overlap
            y_overlap = not (left_y_max < right_y_min or right_y_max < left_y_min)
            
            if y_overlap:
                # Calculate overlap percentage
                overlap_range = min(left_y_max, right_y_max) - max(left_y_min, right_y_min)
                total_range = max(left_y_max, right_y_max) - min(left_y_min, right_y_min)
                overlap_pct = (overlap_range / total_range) * 100 if total_range > 0 else 0
                
                # Calculate balance between left and right columns
                left_count = len(left_lines)
                right_count = len(right_lines)
                total_count = left_count + right_count
                balance_ratio = min(left_count, right_count) / max(left_count, right_count)
                
                # Type 3 criteria (RELAXED for better detection):
                # 1. At least 20% overlap (further relaxed from 25%)
                # 2. At least 3 lines in each column (already checked above)
                # 3. Column boundary near middle of page
                # NOTE: Balance ratio check removed - even 5L/43R can be valid Type 3
                has_overlap = overlap_pct > 20  # More relaxed threshold
                
                if has_overlap:
                    # Find column boundary
                    left_x_max = max(x_end for _, _, x_end, _ in left_lines)
                    right_x_min = min(x_start for _, x_start, _, _ in right_lines)
                    col_boundary = (left_x_max + right_x_min) / 2
                    
                    # Validate: boundary should be somewhere reasonable (10%-90% range)
                    if 0.1 * page_width < col_boundary < 0.9 * page_width:
                        if self.verbose:
                            print(f"    ✓ Type 3 detected: Y-overlap={overlap_pct:.1f}%, balance={balance_ratio:.2f}, boundary at x={col_boundary:.1f}")
                        
                        return [(0, col_boundary), (col_boundary, page_width)], 'y_overlap'
                    elif self.verbose:
                        print(f"    ✗ Boundary too far from reasonable range: x={col_boundary:.1f} ({col_boundary/page_width*100:.1f}%)")
                elif self.verbose:
                    print(f"    ✗ Insufficient overlap: {overlap_pct:.1f}% < 20%")
        
        # No Type 3 pattern found
        return [(0, page_width)], 'single_column'
    
    def _group_words_into_lines(self, words: List[WordMetadata]) -> List[Tuple[float, List[WordMetadata]]]:
        """
        Group words into lines based on Y-position
        
        Args:
            words: List of words
            
        Returns:
            List of (y_center, words) tuples, sorted by Y position
        """
        lines = defaultdict(list)
        
        for word in words:
            y_center = (word.bbox[1] + word.bbox[3]) / 2
            
            # Find existing line or create new one
            found_line = False
            for line_y in list(lines.keys()):
                if abs(y_center - line_y) <= self.y_tolerance:
                    lines[line_y].append(word)
                    found_line = True
                    break
            
            if not found_line:
                lines[y_center] = [word]
        
        # Sort by Y position
        return sorted(lines.items(), key=lambda x: x[0])


# Make it easy to import
__all__ = ['EnhancedLayoutDetector', 'LayoutType']
