"""
Resume Feature Extractor for Dataset Labeling
Extracts numeric features from PDF resumes for layout classification.
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import numpy as np
from collections import defaultdict
import fitz  # PyMuPDF

from src.core.word_extractor import WordMetadata


@dataclass
class ResumeFeatures:
    """Container for extracted resume features"""
    num_columns: int
    mean_y_overlap: float
    coverage_gutter: float
    full_width_line_ratio: float
    valley_depth_ratio: float
    horizontal_lines_count: int
    header_fraction: float
    avg_word_width_ratio: float
    line_density_variance: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV/JSON export"""
        return {
            'num_columns': self.num_columns,
            'mean_y_overlap': round(self.mean_y_overlap, 4),
            'coverage_gutter': round(self.coverage_gutter, 4),
            'full_width_line_ratio': round(self.full_width_line_ratio, 4),
            'valley_depth_ratio': round(self.valley_depth_ratio, 4),
            'horizontal_lines_count': self.horizontal_lines_count,
            'header_fraction': round(self.header_fraction, 4),
            'avg_word_width_ratio': round(self.avg_word_width_ratio, 4),
            'line_density_variance': round(self.line_density_variance, 4)
        }


class ResumeFeatureExtractor:
    """
    Extracts layout features from PDF resumes for building labeled datasets.
    Computes 9 numeric features that characterize single-column vs multi-column layouts.
    """
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        
        # Configuration parameters
        self.y_tolerance = 5  # pixels for line grouping
        self.full_width_fraction = 0.75  # threshold for full-width lines
        self.gutter_zero_max = 0.05  # max density to consider as gutter
        self.band_count = 60  # horizontal bands for gutter analysis
        
    def extract_words_and_bbox(self, pdf_path: str) -> Tuple[List[WordMetadata], float, float]:
        """
        Extract words with bounding boxes from first page of PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (words, page_width, page_height)
        """
        doc = fitz.open(pdf_path)
        page = doc[0]  # First page only
        
        page_width = page.rect.width
        page_height = page.rect.height
        
        words = []
        word_dict = page.get_text("dict")
        
        for block in word_dict.get("blocks", []):
            if block.get("type") != 0:  # Skip non-text blocks
                continue
                
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue
                    
                    bbox = span.get("bbox", [0, 0, 0, 0])
                    words.append(WordMetadata(
                        text=text,
                        bbox=bbox,
                        page_num=0,
                        font_size=span.get("size", 12.0),
                        font_name=span.get("font", "unknown")
                    ))
        
        doc.close()
        
        if self.verbose:
            print(f"[FeatureExtractor] Extracted {len(words)} words from {pdf_path}")
            print(f"[FeatureExtractor] Page dimensions: {page_width:.1f} x {page_height:.1f}")
        
        return words, page_width, page_height
    
    def compute_features(
        self,
        words: List[WordMetadata],
        page_width: float,
        page_height: float
    ) -> ResumeFeatures:
        """
        Compute all 9 numeric features from extracted words.
        
        Args:
            words: List of WordMetadata objects
            page_width: Width of PDF page
            page_height: Height of PDF page
            
        Returns:
            ResumeFeatures object with all computed features
        """
        if not words:
            return ResumeFeatures(
                num_columns=1,
                mean_y_overlap=0.0,
                coverage_gutter=0.0,
                full_width_line_ratio=0.0,
                valley_depth_ratio=1.0,
                horizontal_lines_count=0,
                header_fraction=0.0,
                avg_word_width_ratio=0.0,
                line_density_variance=0.0
            )
        
        # Extract numpy arrays for efficient computation
        x0 = np.array([w.bbox[0] for w in words])
        x1 = np.array([w.bbox[2] for w in words])
        y0 = np.array([w.bbox[1] for w in words])
        y1 = np.array([w.bbox[3] for w in words])
        xc = (x0 + x1) * 0.5
        
        # Feature 1: num_columns (from gutter detection)
        gutter_metrics = self._compute_gutter_metrics(words, page_width, page_height)
        coverage_gutter = gutter_metrics['coverage']
        num_columns = 2 if coverage_gutter >= 0.7 else 1
        
        # Feature 2: mean_y_overlap
        mean_y_overlap = self._compute_y_overlap(words)
        
        # Feature 3: coverage_gutter (already computed)
        
        # Feature 4 & 6: full_width_line_ratio and horizontal_lines_count
        lines = self._group_words_into_lines(words)
        full_width_count = 0
        for y, line_words in lines:
            x_start = min(w.bbox[0] for w in line_words)
            x_end = max(w.bbox[2] for w in line_words)
            width = x_end - x_start
            if width >= page_width * self.full_width_fraction:
                full_width_count += 1
        
        full_width_line_ratio = full_width_count / max(len(lines), 1)
        horizontal_lines_count = full_width_count
        
        # Feature 5: valley_depth_ratio
        valley_depth_ratio = self._compute_valley_depth(words, page_width)
        
        # Feature 7: header_fraction
        header_fraction = gutter_metrics['header_frac']
        
        # Feature 8: avg_word_width_ratio
        word_widths = x1 - x0
        avg_word_width_ratio = float(np.mean(word_widths) / page_width)
        
        # Feature 9: line_density_variance
        line_densities = [len(line_words) for _, line_words in lines]
        line_density_variance = float(np.var(line_densities)) if line_densities else 0.0
        
        features = ResumeFeatures(
            num_columns=num_columns,
            mean_y_overlap=mean_y_overlap,
            coverage_gutter=coverage_gutter,
            full_width_line_ratio=full_width_line_ratio,
            valley_depth_ratio=valley_depth_ratio,
            horizontal_lines_count=horizontal_lines_count,
            header_fraction=header_fraction,
            avg_word_width_ratio=avg_word_width_ratio,
            line_density_variance=line_density_variance
        )
        
        if self.verbose:
            print("[FeatureExtractor] Computed features:")
            for key, val in features.to_dict().items():
                print(f"  {key}: {val}")
        
        return features
    
    def _compute_y_overlap(self, words: List[WordMetadata]) -> float:
        """Compute mean Y-overlap ratio between words"""
        if len(words) < 2:
            return 0.0
        
        y0 = np.array([w.bbox[1] for w in words])
        y1 = np.array([w.bbox[3] for w in words])
        heights = y1 - y0
        n = len(words)
        
        # Sample pairs to avoid O(n^2) for large documents
        max_pairs = 10000
        if n * (n - 1) // 2 > max_pairs:
            # Random sampling
            indices = np.random.choice(n, size=min(n, 200), replace=False)
            overlap_ratios = []
            for i in range(len(indices) - 1):
                idx_i = indices[i]
                for j in range(i + 1, len(indices)):
                    idx_j = indices[j]
                    yi0, yi1, hi = y0[idx_i], y1[idx_i], heights[idx_i]
                    yj0, yj1, hj = y0[idx_j], y1[idx_j], heights[idx_j]
                    h_min = min(hi, hj)
                    if h_min > 0:
                        overlap = max(0, min(yi1, yj1) - max(yi0, yj0))
                        overlap_ratios.append(overlap / h_min)
        else:
            # Full computation
            overlap_ratios = []
            for i in range(n - 1):
                yi0, yi1, hi = y0[i], y1[i], heights[i]
                for j in range(i + 1, n):
                    yj0, yj1, hj = y0[j], y1[j], heights[j]
                    h_min = min(hi, hj)
                    if h_min > 0:
                        overlap = max(0, min(yi1, yj1) - max(yi0, yj0))
                        overlap_ratios.append(overlap / h_min)
        
        return float(np.mean(overlap_ratios)) if overlap_ratios else 0.0
    
    def _group_words_into_lines(self, words: List[WordMetadata]) -> List[Tuple[float, List[WordMetadata]]]:
        """Group words into horizontal lines based on Y-coordinate proximity"""
        lines = defaultdict(list)
        for w in words:
            y_center = (w.bbox[1] + w.bbox[3]) / 2
            placed = False
            for line_y in list(lines.keys()):
                if abs(y_center - line_y) <= self.y_tolerance:
                    lines[line_y].append(w)
                    placed = True
                    break
            if not placed:
                lines[y_center].append(w)
        
        return sorted(lines.items(), key=lambda x: x[0])
    
    def _compute_gutter_metrics(
        self,
        words: List[WordMetadata],
        page_width: float,
        page_height: float
    ) -> Dict[str, Any]:
        """Compute gutter coverage and header fraction using bandwise analysis"""
        w, h = page_width, page_height
        bins = 400
        band_count = self.band_count
        
        x0 = np.array([word.bbox[0] for word in words])
        x1 = np.array([word.bbox[2] for word in words])
        y0 = np.array([word.bbox[1] for word in words])
        y1 = np.array([word.bbox[3] for word in words])
        xc = (x0 + x1) * 0.5
        
        # Global X-density to find gutter center
        dens_global = np.zeros(bins, dtype=float)
        idx_all = np.clip((xc * bins / w).astype(int), 0, bins - 1)
        np.add.at(dens_global, idx_all, 1.0)
        
        dens_global = np.convolve(dens_global, np.ones(7) / 7, mode='same')
        dens_global /= max(1.0, dens_global.max())
        
        center_bin = np.argmin(dens_global[bins // 2 - bins // 8: bins // 2 + bins // 8]) + bins // 2 - bins // 8
        
        # Analyze each horizontal band
        band_h = h / band_count
        zero_hits = 0
        start_stable = None
        run = 0
        K = max(4, band_count // 12)
        
        for bi in range(band_count):
            y_top = bi * band_h
            y_bot = min(h, y_top + band_h)
            
            mask = np.logical_and(y1 > y_top, y0 < y_bot)
            if not np.any(mask):
                run = 0
                continue
            
            idx = np.clip((xc[mask] * bins / w).astype(int), 0, bins - 1)
            dens = np.zeros(bins, dtype=float)
            np.add.at(dens, idx, 1.0)
            dens = np.convolve(dens, np.ones(7) / 7, mode='same')
            dens /= max(1.0, dens.max())
            
            l, r = max(0, center_bin - 10), min(bins, center_bin + 11)
            val = float(dens[l:r].min())
            
            if val <= self.gutter_zero_max:
                run += 1
                if start_stable is None and run >= K:
                    start_stable = bi - K + 1
                zero_hits += 1
            else:
                run = 0
        
        coverage = zero_hits / band_count
        header_frac = 0.0 if start_stable is None else (start_stable * band_h / h)
        
        return {
            'coverage': coverage,
            'header_frac': header_frac
        }
    
    def _compute_valley_depth(self, words: List[WordMetadata], page_width: float) -> float:
        """Compute minimum valley depth in X-density histogram"""
        bins = max(200, int(page_width / 2))
        x_centers = np.array([(w.bbox[0] + w.bbox[2]) / 2 for w in words])
        hist_values, _ = np.histogram(x_centers, bins=bins, range=(0, page_width))
        
        # Smooth histogram
        hist_smooth = np.convolve(hist_values.astype(float), np.ones(5) / 5, mode='same')
        hist_smooth /= max(hist_smooth.max(), 1.0)
        
        # Find valleys (local minima)
        valleys = []
        for i in range(1, len(hist_smooth) - 1):
            if hist_smooth[i] < hist_smooth[i-1] and hist_smooth[i] < hist_smooth[i+1]:
                valleys.append(hist_smooth[i])
        
        return float(min(valleys)) if valleys else 1.0
