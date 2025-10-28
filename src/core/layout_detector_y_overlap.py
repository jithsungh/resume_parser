"""
Enhanced Layout Detection with Histogram Valley Analysis
=========================================================
Detects Type 2 vs Type 3 layouts using quantitative histogram analysis.

Key Innovation: X-Density Histogram Valley Depth Analysis
- Type 2: Deep valley (≈0) between column peaks → clean separation
- Type 3: Shallow valley (>20% of peak) → content crosses columns

Additional Signals:
1. Y-overlap consistency check
2. Horizontal section detection
3. Column balance analysis

Reference: Histogram-based layout classification algorithm
"""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import numpy as np

from .word_extractor import WordMetadata
from .layout_detector_histogram import LayoutDetector as BaseLayoutDetector, LayoutType


class EnhancedLayoutDetector(BaseLayoutDetector):
    """
    Enhanced layout detector with histogram valley depth analysis
    
    Combines multiple signals for robust Type 2/3 classification:
    1. X-density histogram valley depth (primary signal)
    2. Y-overlap ratio (secondary validation)
    3. Horizontal section detection
    4. Column balance analysis
    """
      
    def __init__(self, *args, valley_threshold: float = 0.3, **kwargs):
        """
        Args:
            valley_threshold: Valley depth threshold for Type 2 (default 0.3)
                            Valley depth < threshold → Type 2 (clean columns)
                            Valley depth ≥ threshold → Type 3 (hybrid)
        """
        super().__init__(*args, **kwargs)
        self.y_tolerance = 5  # Points tolerance for same line
        self.valley_threshold = valley_threshold  # 0.3 means valley must drop to <30% of peak (more sensitive)
    
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
                    print(f"  Fallback: Using gap-based detection: {len(column_boundaries)} columns")
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
            page_width=page_width,            metadata={
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
        Classify layout as Type 1, 2, or 3 using HISTOGRAM VALLEY DEPTH as primary signal
        
        Algorithm:
        1. Compute normalized X-density histogram
        2. Find peaks (column centers)
        3. Measure valley depth between peaks
        4. Validate with Y-overlap and horizontal sections
        
        Type 1: Single column (horizontal flow)
        Type 2: Clean vertical columns → deep valley (< 40% of peak)
        Type 3: Complex/hybrid → shallow valley (≥ 40% of peak) OR high Y-overlap
        
        Returns:
            Tuple of (layout_type, type_name, confidence)
        """
        num_columns = len(column_boundaries)
        
        # Type 1: Single column
        if num_columns == 1:
            return 1, "single-column", 0.9
        
        # ============================================================
        # PRIMARY SIGNAL: Histogram Valley Depth Analysis
        # ============================================================
        valley_depth_ratio, valley_depth_score = self._compute_valley_depth(
            words, page_width, smoothed_histogram, peaks
        )
        
        # ============================================================
        # SECONDARY SIGNAL: Y-Overlap Consistency Check
        # ============================================================
        mean_y_overlap = self._compute_y_overlap_ratio(words)
        
        # ============================================================
        # TERTIARY SIGNAL: Horizontal Sections
        # ============================================================
        full_width_lines, has_horizontal_sections = self._detect_horizontal_sections(
            words, page_width
        )
        
        # ============================================================
        # ADDITIONAL SIGNAL: Column Balance
        # ============================================================
        col_widths = [end - start for start, end in column_boundaries]
        width_ratio = min(col_widths) / max(col_widths) if max(col_widths) > 0 else 0
        is_balanced = width_ratio > 0.6
          # ============================================================
        # DECISION LOGIC (Weighted Multi-Signal Classification)
        # ============================================================
        
        # CRITICAL: If Y-overlap detection found columns, it means Type 3 pattern exists
        # We should give strong weight to this signal
        if detection_method == 'y_overlap':
            # Y-overlap already confirmed side-by-side columns with overlapping Y-ranges
            # This is the STRONGEST signal for Type 3
            is_type3 = True
            confidence = 0.85 + (0.10 if has_horizontal_sections else 0.0)
            
            if self.verbose:
                print(f"    ════════════════════════════════════════")
                print(f"    Type 2/3 Classification Signals:")
                print(f"    ════════════════════════════════════════")
                print(f"    DETECTION METHOD: {detection_method}")
                print(f"      → Y-overlap detection CONFIRMS Type 3")
                print(f"    SUPPORTING SIGNALS:")
                print(f"      • Valley depth ratio: {valley_depth_ratio:.3f}")
                print(f"      • Y-overlap ratio: {mean_y_overlap:.3f}")
                print(f"      • Horizontal sections: {full_width_lines} lines")
                print(f"      • Column balance: {width_ratio:.2f}")
                print(f"    ────────────────────────────────────────")
                print(f"    FINAL: Detection method = y_overlap → Type 3 (FORCED)")
                print(f"    ════════════════════════════════════════")
            
            return 3, "hybrid/complex", confidence
        
        # Otherwise, use multi-signal weighted classification
        # Score each signal (0-1 scale, higher = more Type 3)
        signals = {
            'valley_depth': valley_depth_score,  # Primary (weight: 0.4)
            'y_overlap': min(mean_y_overlap * 4, 1.0),  # Secondary (weight: 0.35) - more sensitive
            'horizontal': 1.0 if has_horizontal_sections else 0.0,  # Tertiary (weight: 0.25)
        }
        
        # Weighted combination (rebalanced for better Type 3 detection)
        type3_score = (
            signals['valley_depth'] * 0.40 +
            signals['y_overlap'] * 0.35 +
            signals['horizontal'] * 0.25
        )
        
        # Classification threshold (lowered for better Type 3 detection)
        is_type3 = type3_score > 0.35  # Lowered from 0.45 for better sensitivity
        
        # Confidence calculation
        confidence = 0.70 + min(abs(type3_score - 0.5) * 0.4, 0.25)
        
        if self.verbose:
            print(f"    ════════════════════════════════════════")
            print(f"    Type 2/3 Classification Signals:")
            print(f"    ════════════════════════════════════════")
            print(f"    PRIMARY:")
            print(f"      • Valley depth ratio: {valley_depth_ratio:.3f} (score: {signals['valley_depth']:.2f})")
            print(f"        → {'SHALLOW (Type 3)' if valley_depth_ratio >= self.valley_threshold else 'DEEP (Type 2)'}")
            print(f"    SECONDARY:")
            print(f"      • Y-overlap ratio: {mean_y_overlap:.3f} (score: {signals['y_overlap']:.2f})")
            print(f"        → {'HIGH (Type 3)' if mean_y_overlap > 0.20 else 'LOW (Type 2)'}")
            print(f"    TERTIARY:")
            print(f"      • Horizontal sections: {full_width_lines} lines (score: {signals['horizontal']:.2f})")
            print(f"        → {'YES (Type 3)' if has_horizontal_sections else 'NO'}")
            print(f"    ADDITIONAL:")
            print(f"      • Column balance: {width_ratio:.2f} ({'balanced' if is_balanced else 'unbalanced'})")
            print(f"      • Detection method: {detection_method}")
            print(f"    ────────────────────────────────────────")
            print(f"    FINAL: Type 3 score = {type3_score:.3f} → {'Type 3' if is_type3 else 'Type 2'}")
            print(f"    ════════════════════════════════════════")
        
        if is_type3:
            return 3, "hybrid/complex", confidence
        else:
            return 2, "multi-column", confidence
    
    def _compute_valley_depth(
        self,
        words: List[WordMetadata],
        page_width: float,
        smoothed_histogram: Dict[int, float],
        peaks: List[int]
    ) -> Tuple[float, float]:
        """
        Compute valley depth ratio using normalized X-density histogram
        
        Returns:
            Tuple of (valley_depth_ratio, type3_score)
            - valley_depth_ratio: deepest_valley / max_peak (0-1)
            - type3_score: 0-1 score (higher = more Type 3)
        """
        if not smoothed_histogram or len(peaks) < 2:
            # No clear peaks → assume shallow valley
            return 1.0, 1.0
        
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
        
        if not valley_values:
            return 1.0, 1.0
        
        deepest_valley = min(valley_values)
        valley_depth_ratio = deepest_valley / max_val if max_val > 0 else 1.0
        
        # Convert to Type 3 score (0-1)
        # valley_depth < 0.2 → Type 2 (score 0)
        # valley_depth > 0.6 → Type 3 (score 1)
        if valley_depth_ratio < 0.2:
            type3_score = 0.0
        elif valley_depth_ratio > 0.6:
            type3_score = 1.0
        else:
            # Linear interpolation
            type3_score = (valley_depth_ratio - 0.2) / 0.4
        
        return valley_depth_ratio, type3_score
    
    def _compute_y_overlap_ratio(self, words: List[WordMetadata]) -> float:
        """
        Compute mean Y-overlap ratio across all word pairs
        
        High overlap (>0.2) → likely Type 3
        Low overlap (<0.15) → likely Type 2
        
        Returns:
            Mean Y-overlap ratio (0-1)
        """
        if len(words) < 2:
            return 0.0
        
        # Sample pairs to avoid O(n²) complexity
        import random
        max_pairs = min(1000, len(words) * (len(words) - 1) // 2)
        
        overlap_ratios = []
        pairs_checked = 0
        
        for i in range(len(words)):
            if pairs_checked >= max_pairs:
                break
            
            # Sample a few pairs per word
            sample_size = min(10, len(words) - i - 1)
            if sample_size <= 0:
                continue
            
            indices = random.sample(range(i + 1, len(words)), sample_size)
            
            for j in indices:
                word_a = words[i]
                word_b = words[j]
                
                # Y overlap
                y_overlap = max(0, min(word_a.bbox[3], word_b.bbox[3]) - max(word_a.bbox[1], word_b.bbox[1]))
                h_min = min(word_a.bbox[3] - word_a.bbox[1], word_b.bbox[3] - word_b.bbox[1])
                
                if h_min > 0:
                    overlap_ratios.append(y_overlap / h_min)
                
                pairs_checked += 1
                if pairs_checked >= max_pairs:
                    break
        
        return np.mean(overlap_ratios) if overlap_ratios else 0.0
    
    def _detect_horizontal_sections(
        self,
        words: List[WordMetadata],
        page_width: float
    ) -> Tuple[int, bool]:
        """
        Detect horizontal sections (full-width lines)
        
        Returns:
            Tuple of (full_width_lines_count, has_horizontal_sections)
        """
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
        
        return full_width_lines, has_horizontal_sections
    
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
            print(f"    Line classification: {len(left_lines)} left, {len(right_lines)} right, {len(full_width_lines)} full-width")
        
        # Check for Type 3 pattern: left and right columns with overlapping Y-ranges
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
                column_lines = left_count + right_count
                total_lines = column_lines + len(full_width_lines)
                balance_ratio = min(left_count, right_count) / max(left_count, right_count)
                  # CRITICAL: Calculate column-to-fullwidth ratio
                # Type 3: Most lines are in columns (column_lines > full_width_lines)
                # Type 2 with sidebar: Most lines are full-width (full_width_lines > column_lines)
                column_ratio = column_lines / total_lines if total_lines > 0 else 0
                
                # Type 3 criteria (ADAPTIVE thresholds based on overlap strength):
                # 1. At least 20% Y-overlap
                # 2. At least 3 lines in each column (already checked)
                # 3. Column lines should be significant:
                #    - If strong overlap (>60%): column_ratio > 35% (relaxed)
                #    - If moderate overlap (20-60%): column_ratio > 45%
                #    - Otherwise: column_ratio > 50%
                # 4. Column boundary near middle of page
                has_overlap = overlap_pct > 20
                
                # Adaptive column ratio threshold based on overlap strength
                if overlap_pct > 60:
                    column_ratio_threshold = 0.35  # Relaxed for strong overlap
                elif overlap_pct > 40:
                    column_ratio_threshold = 0.40  # Moderate threshold
                else:
                    column_ratio_threshold = 0.45  # Stricter for weak overlap
                
                has_dominant_columns = column_ratio > column_ratio_threshold
                
                if has_overlap and has_dominant_columns:
                    # Find column boundary
                    left_x_max = max(x_end for _, _, x_end, _ in left_lines)
                    right_x_min = min(x_start for _, x_start, _, _ in right_lines)
                    col_boundary = (left_x_max + right_x_min) / 2
                      # Validate: boundary should be somewhere reasonable (10%-90% range)
                    if 0.1 * page_width < col_boundary < 0.9 * page_width:
                        if self.verbose:
                            print(f"    ✓ Type 3 detected: Y-overlap={overlap_pct:.1f}%, column_ratio={column_ratio:.2f}, balance={balance_ratio:.2f}, boundary at x={col_boundary:.1f}")
                        
                        return [(0, col_boundary), (col_boundary, page_width)], 'y_overlap'
                    elif self.verbose:
                        print(f"    ✗ Boundary too far from reasonable range: x={col_boundary:.1f} ({col_boundary/page_width*100:.1f}%)")
                elif self.verbose:
                    if not has_overlap:
                        print(f"    ✗ Insufficient overlap: {overlap_pct:.1f}% < 20%")
                    if not has_dominant_columns:
                        print(f"    ✗ Column lines not dominant: {column_ratio:.1%} (need >{column_ratio_threshold:.0%})")
                        print(f"      → Overlap: {overlap_pct:.1f}%, threshold adjusted to {column_ratio_threshold:.0%}")
                        print(f"      → This looks like Type 2 with sidebar (full-width dominant)")
        
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


# ============================================================
# Visualization Utility
# ============================================================

def visualize_histogram(
    layout_result: LayoutType,
    words: List[WordMetadata],
    save_path: Optional[str] = None,
    show: bool = True
):
    """
    Visualize X-density histogram for layout debugging
    
    Shows:
    - Smoothed histogram
    - Detected peaks (column centers)
    - Valley depth
    - Layout type classification
    
    Args:
        layout_result: LayoutType result from detector
        words: Original words
        save_path: Optional path to save figure
        show: Whether to display figure
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Warning: matplotlib not installed. Install with: pip install matplotlib")
        return
    
    histogram = layout_result.histogram
    peaks = layout_result.peaks
    
    if not histogram:
        print("No histogram data to visualize")
        return
    
    # Compute smoothed histogram
    from scipy.ndimage import gaussian_filter1d
    
    bins = sorted(histogram.keys())
    values = [histogram[b] for b in bins]
    
    # Normalize
    max_val = max(values) if values else 1
    values_norm = [v / max_val for v in values]
    
    # Smooth
    smoothed = gaussian_filter1d(values_norm, sigma=5)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot histogram
    ax.plot(bins, smoothed, linewidth=2, label='X-Density Histogram')
    ax.fill_between(bins, 0, smoothed, alpha=0.3)
    
    # Mark peaks
    for peak in peaks:
        if peak in bins:
            peak_idx = bins.index(peak)
            ax.axvline(peak, color='green', linestyle='--', alpha=0.7, label=f'Peak at x={peak}')
            ax.plot(peak, smoothed[peak_idx], 'go', markersize=10)
    
    # Mark valleys
    if len(peaks) >= 2:
        for i in range(len(peaks) - 1):
            valley_start = peaks[i]
            valley_end = peaks[i + 1]
            
            # Find minimum
            min_val = 1.0
            min_pos = valley_start
            for j, b in enumerate(bins):
                if valley_start <= b <= valley_end:
                    if smoothed[j] < min_val:
                        min_val = smoothed[j]
                        min_pos = b
            
            ax.axvline(min_pos, color='red', linestyle=':', alpha=0.7, label=f'Valley (depth={min_val:.2f})')
            ax.plot(min_pos, min_val, 'ro', markersize=8)
    
    # Labels
    ax.set_xlabel('X Position (normalized)', fontsize=12)
    ax.set_ylabel('Normalized Density', fontsize=12)
    ax.set_title(
        f'Layout Type: {layout_result.type_name} (Type {layout_result.type})\n'
        f'Columns: {layout_result.num_columns}, Confidence: {layout_result.confidence:.1%}',
        fontsize=14,
        fontweight='bold'
    )
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1.1)
    
    # Legend (remove duplicates)
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc='upper right')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved histogram visualization to: {save_path}")
    
    if show:
        plt.show()
    else:
        plt.close()


# Make it easy to import
__all__ = ['EnhancedLayoutDetector', 'LayoutType', 'visualize_histogram']
