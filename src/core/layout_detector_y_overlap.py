from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
from collections import defaultdict
import numpy as np

from .word_extractor import WordMetadata
from .layout_detector_histogram import LayoutDetector as BaseLayoutDetector, LayoutType


@dataclass
class LayoutConfig:
    """Configuration for enhanced layout detection"""
    valley_threshold: float = 0.3
    y_tolerance: int = 5
    horizontal_lines_min: int = 3
    full_width_fraction: float = 0.75
    gutter_zero_max: float = 0.05
    band_count: int = 60
    verbose: bool = False


class EnhancedLayoutDetector(BaseLayoutDetector):
    """
    Enhanced layout detector: Type 1 / Type 2 / Type 3 classification
    using histogram valley depth, gutter coverage, Y-overlap, and horizontal sections.
    
    This detector combines multiple signals:
    - Bandwise gutter metrics (primary signal for column detection)
    - Y-overlap analysis (vertical alignment of text blocks)
    - Histogram valley depth (density distribution)
    - Horizontal section detection (full-width text lines)
    """

    def __init__(self, config: Optional[LayoutConfig] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config or LayoutConfig()

    def detect_layout(self, words: List[WordMetadata], page_width: float = None) -> LayoutType:
        """
        Main entry point for detecting layout type.
        
        Args:
            words: List of WordMetadata objects
            page_width: Optional page width (auto-detected if not provided)
            
        Returns:
            LayoutType object with detected layout information
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

        # Determine page dimensions
        page_width = page_width or (max(word.bbox[2] for word in words) + 10)
        page_height = max(word.bbox[3] for word in words) + 10

        if self.config.verbose:
            print(f"[EnhancedLayoutDetector] Analyzing {len(words)} words, page w×h: {page_width:.1f}×{page_height:.1f}")

        # Step 1: Bandwise gutter metrics (primary signal)
        gutter_metrics = self._bandwise_gutter_metrics(words, page_width, page_height)
        coverage = gutter_metrics["coverage"]
        header_frac = gutter_metrics["header_frac"]

        # Step 2: Column detection
        if coverage >= 0.7:
            # Strong gutter detected → split columns
            gutter_x = gutter_metrics["gutter_x"]
            column_boundaries = [(0, gutter_x), (gutter_x, page_width)]
            detection_method = "gutter"
        else:
            # Fallback to Y-overlap based detection
            column_boundaries, detection_method = self._detect_columns_by_y_overlap(words, page_width)

        num_columns = len(column_boundaries)

        # Step 3: Histogram and valley analysis
        histogram, peaks, valleys, valley_depth_ratio = self._compute_histogram(words, page_width, num_columns)

        # Step 4: Line grouping and horizontal sections
        lines = self._group_words_into_lines(words)
        full_width_count, has_horizontal_sections = self._detect_horizontal_sections(lines, page_width)

        # Step 5: Y-overlap score
        y_overlap_ratio = self._compute_y_overlap(words)

        # Step 6: Final layout classification
        layout_type, type_name, confidence = self._classify_layout(
            num_columns,
            coverage,
            header_frac,
            valley_depth_ratio,
            has_horizontal_sections,
            y_overlap_ratio
        )

        metadata = {
            "total_words": len(words),
            "column_boundaries": column_boundaries,
            "histogram": histogram,
            "peaks": peaks,
            "valleys": valleys,
            "gutter_metrics": gutter_metrics,
            "detection_method": detection_method,
            "full_width_lines": full_width_count,
            "y_overlap_ratio": y_overlap_ratio,
            "valley_depth_ratio": valley_depth_ratio
        }

        if self.config.verbose:
            print(f"[EnhancedLayoutDetector] Layout Type: {type_name} (Type {layout_type}), Confidence: {confidence:.2f}")
            print(f"  - Detection method: {detection_method}")
            print(f"  - Gutter coverage: {coverage:.2f}, Header fraction: {header_frac:.2f}")
            print(f"  - Y-overlap ratio: {y_overlap_ratio:.3f}, Valley depth: {valley_depth_ratio:.3f}")

        return LayoutType(
            type=layout_type,
            type_name=type_name,
            num_columns=num_columns,
            column_boundaries=column_boundaries,
            histogram=histogram,
            peaks=peaks,
            valleys=valleys,
            confidence=confidence,
            page_width=page_width,
            metadata=metadata
        )

    # =========================================
    # Classification Logic
    # =========================================    
    def _classify_layout(
        self,
        num_columns: int,
        coverage: float,
        header_frac: float,
        valley_depth_ratio: float,
        has_horizontal: bool,
        y_overlap_ratio: float
    ) -> Tuple[int, str, float]:
        """
        Classify layout type based on multiple signals.
        
        Type 1: Single column
        Type 2: Multi-column (clean separation)
        Type 3: Hybrid/complex (mixed layout with headers and full-width sections)
        """
        # Type 1: single column
        if num_columns == 1:
            return 1, "single-column", 0.9

        # Strong gutter logic (coverage >= 0.7 means clear column separation)
        if coverage >= 0.7:
            # Type 3 indicators:
            # 1. has_horizontal: presence of full-width lines (>= 3 lines)
            # 2. header_frac > 0.05: significant header section at top
            # 
            # Type 3 resumes have full-width lines throughout (headers, section titles)
            # Type 2 resumes are purely columnar with minimal full-width content
            
            if has_horizontal or header_frac > 0.05:
                # Hybrid layout with full-width sections
                return 3, "hybrid/complex", 0.92
            else:
                # Clean multi-column without significant full-width content
                return 2, "multi-column", 0.92

        # Fallback: weighted scoring based on multiple signals
        # Used when gutter is weak (coverage < 0.7)
        signals = {
            "valley_depth": min(valley_depth_ratio / self.config.valley_threshold, 1.0),
            "y_overlap": min(y_overlap_ratio * 5, 1.0),
            "horizontal": 1.0 if has_horizontal else 0.0
        }
        
        # Type 3 score: higher values suggest complex/hybrid layout
        type3_score = (
            0.4 * signals["valley_depth"] +
            0.35 * signals["y_overlap"] +
            0.25 * signals["horizontal"]
        )
        
        is_type3 = type3_score > 0.35
        confidence = 0.7 + min(abs(type3_score - 0.5) * 0.4, 0.25)
        
        if is_type3:
            return 3, "hybrid/complex", confidence
        else:
            return 2, "multi-column", confidence

    # =========================================
    # Core Helper Functions
    # =========================================

    def _compute_histogram(
        self,
        words: List[WordMetadata],
        page_width: float,
        expected_columns: int
    ) -> Tuple[np.ndarray, List[float], List[float], float]:
        """
        Compute X-density histogram and detect peaks/valleys.
        
        Returns:
            - histogram: Smoothed normalized histogram
            - peaks_x: X-positions of density peaks
            - valleys_x: X-positions of density valleys
            - valley_depth_ratio: Minimum normalized valley depth
        """
        bins = max(200, int(page_width / 2))
        x_centers = np.array([(w.bbox[0] + w.bbox[2]) / 2 for w in words])
        hist_values, bin_edges = np.histogram(x_centers, bins=bins, range=(0, page_width))

        # Smooth histogram with Gaussian filter
        try:
            from scipy.ndimage import gaussian_filter1d
            from scipy.signal import find_peaks
            hist_smooth = gaussian_filter1d(hist_values.astype(float), sigma=3)
        except ImportError:
            # Fallback to simple convolution if scipy not available
            kernel = np.ones(5) / 5
            hist_smooth = np.convolve(hist_values.astype(float), kernel, mode='same')
        
        hist_smooth /= max(hist_smooth.max(), 1.0)  # normalize 0-1

        # Find peaks and valleys
        try:
            from scipy.signal import find_peaks
            peaks_idx, _ = find_peaks(hist_smooth, distance=bins // max(1, expected_columns))
            valleys_idx = []
            valley_depth_ratio = 1.0
            
            if len(peaks_idx) >= 2:
                for i in range(len(peaks_idx) - 1):
                    valley_range = hist_smooth[peaks_idx[i]:peaks_idx[i+1]+1]
                    if len(valley_range) > 0:
                        min_val = valley_range.min()
                        valleys_idx.append(int(np.argmin(valley_range)) + peaks_idx[i])
                
                if valleys_idx:
                    valley_depth_ratio = min(hist_smooth[valleys_idx])
        except ImportError:
            # Fallback: simple peak detection
            peaks_idx = []
            valleys_idx = []
            valley_depth_ratio = 1.0
            
            for i in range(1, len(hist_smooth) - 1):
                if hist_smooth[i] > hist_smooth[i-1] and hist_smooth[i] > hist_smooth[i+1]:
                    peaks_idx.append(i)
                elif hist_smooth[i] < hist_smooth[i-1] and hist_smooth[i] < hist_smooth[i+1]:
                    valleys_idx.append(i)
            
            if len(peaks_idx) >= 2 and valleys_idx:
                valley_depth_ratio = min(hist_smooth[valleys_idx])

        # Convert bin indices to x positions
        peaks_x = [float(bin_edges[p]) for p in peaks_idx]
        valleys_x = [float(bin_edges[v]) for v in valleys_idx]

        return hist_smooth, peaks_x, valleys_x, valley_depth_ratio

    def _compute_y_overlap(self, words: List[WordMetadata]) -> float:
        """
        Compute mean Y-overlap ratio between words.
        Higher values suggest words at similar Y-positions (side-by-side).
        """
        if len(words) < 2:
            return 0.0

        y0 = np.array([w.bbox[1] for w in words])
        y1 = np.array([w.bbox[3] for w in words])
        heights = y1 - y0
        n = len(words)

        overlap_ratios = []
        for i in range(n - 1):
            yi0, yi1 = y0[i], y1[i]
            hi = heights[i]
            for j in range(i + 1, n):
                yj0, yj1 = y0[j], y1[j]
                hj = heights[j]
                h_min = min(hi, hj)
                if h_min > 0:
                    overlap = max(0, min(yi1, yj1) - max(yi0, yj0))
                    overlap_ratios.append(overlap / h_min)
        
        return float(np.mean(overlap_ratios)) if overlap_ratios else 0.0

    def _group_words_into_lines(self, words: List[WordMetadata]) -> List[Tuple[float, List[WordMetadata]]]:
        """
        Group words into horizontal lines based on Y-coordinate proximity.
        
        Returns:
            List of (y_center, words) tuples sorted by Y position
        """
        lines = defaultdict(list)
        for w in words:
            y_center = (w.bbox[1] + w.bbox[3]) / 2
            placed = False
            for line_y in list(lines.keys()):
                if abs(y_center - line_y) <= self.config.y_tolerance:
                    lines[line_y].append(w)
                    placed = True
                    break
            if not placed:
                lines[y_center].append(w)
        
        return sorted(lines.items(), key=lambda x: x[0])

    def _detect_horizontal_sections(
        self,
        lines: List[Tuple[float, List[WordMetadata]]],
        page_width: float
    ) -> Tuple[int, bool]:
        """
        Detect full-width horizontal sections (e.g., headers, section titles).
        
        Returns:
            - count: Number of full-width lines
            - has_horizontal: Boolean indicating if threshold is met
        """
        count = 0
        for y, line_words in lines:
            x_start = min(w.bbox[0] for w in line_words)
            x_end = max(w.bbox[2] for w in line_words)
            width = x_end - x_start
            if width >= page_width * self.config.full_width_fraction:
                count += 1
        
        return count, count >= self.config.horizontal_lines_min

    def _bandwise_gutter_metrics(
        self,
        words: List[WordMetadata],
        page_width: float,
        page_height: float
    ) -> Dict[str, Any]:
        """
        Compute gutter metrics by analyzing horizontal bands across the page.
        
        This is the primary signal for multi-column detection.
        Returns coverage (fraction of bands with near-zero gutter density)
        and header_frac (where stable gutter starts).
        """
        w, h = page_width, page_height
        bins = 400
        band_count = self.config.band_count

        # Extract word coordinates
        x0 = np.array([word.bbox[0] for word in words])
        x1 = np.array([word.bbox[2] for word in words])
        y0 = np.array([word.bbox[1] for word in words])
        y1 = np.array([word.bbox[3] for word in words])
        xc = (x0 + x1) * 0.5

        # Global X-density to find gutter center
        dens_global = np.zeros(bins, dtype=float)
        idx_all = np.clip((xc * bins / w).astype(int), 0, bins - 1)
        np.add.at(dens_global, idx_all, 1.0)
        
        # Smooth global density
        dens_global = np.convolve(dens_global, np.ones(7) / 7, mode='same')
        dens_global /= max(1.0, dens_global.max())
        
        # Find center gutter (minimum in middle region)
        center_bin = np.argmin(dens_global[bins // 2 - bins // 8: bins // 2 + bins // 8]) + bins // 2 - bins // 8

        # Analyze each horizontal band
        band_h = h / band_count
        zero_hits = 0
        start_stable = None
        run = 0
        K = max(4, band_count // 12)  # Minimum consecutive bands for stable gutter
        band_vals = []

        for bi in range(band_count):
            y_top = bi * band_h
            y_bot = min(h, y_top + band_h)
            
            # Select words in this band
            mask = np.logical_and(y1 > y_top, y0 < y_bot)
            if not np.any(mask):
                band_vals.append(1.0)
                run = 0
                continue
            
            # Compute X-density for this band
            idx = np.clip((xc[mask] * bins / w).astype(int), 0, bins - 1)
            dens = np.zeros(bins, dtype=float)
            np.add.at(dens, idx, 1.0)
            dens = np.convolve(dens, np.ones(7) / 7, mode='same')
            dens /= max(1.0, dens.max())

            # Check gutter density
            l, r = max(0, center_bin - 10), min(bins, center_bin + 11)
            val = float(dens[l:r].min())
            band_vals.append(val)

            if val <= self.config.gutter_zero_max:
                run += 1
                if start_stable is None and run >= K:
                    start_stable = bi - K + 1
                zero_hits += 1
            else:
                run = 0

        coverage = zero_hits / band_count
        header_frac = 0.0 if start_stable is None else (start_stable * band_h / h)
        gutter_x = center_bin * w / bins

        return {
            "coverage": coverage,
            "header_frac": header_frac,
            "gutter_x": gutter_x,
            "band_vals": band_vals
        }

    def _detect_columns_by_y_overlap(
        self,
        words: List[WordMetadata],
        page_width: float
    ) -> Tuple[List[Tuple[float, float]], str]:
        """
        Fallback column detection using Y-overlap analysis.
        
        Groups lines into left/right/full-width categories and determines
        if there's a clean column split.
        
        Returns:
            - column_boundaries: List of (left, right) tuples
            - detection_method: String describing the method used
        """
        lines = self._group_words_into_lines(words)
        mid_x = page_width / 2
        left_lines = []
        right_lines = []
        full_lines = []

        for y, line_words in lines:
            x_start = min(w.bbox[0] for w in line_words)
            x_end = max(w.bbox[2] for w in line_words)
            width = x_end - x_start
            
            if width >= page_width * self.config.full_width_fraction:
                full_lines.append(line_words)
            elif x_start < mid_x * 0.6:
                left_lines.append(line_words)
            elif x_start > mid_x * 0.4:
                right_lines.append(line_words)
            else:
                full_lines.append(line_words)

        # Require minimum lines in each column
        if len(left_lines) >= 3 and len(right_lines) >= 3:
            left_x_max = max(max(w.bbox[2] for w in line) for line in left_lines)
            right_x_min = min(min(w.bbox[0] for w in line) for line in right_lines)
            col_boundary = (left_x_max + right_x_min) / 2
            return [(0, col_boundary), (col_boundary, page_width)], "y_overlap"
        
        return [(0, page_width)], "single_column"
