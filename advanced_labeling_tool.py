"""
Advanced Resume Labeling Tool - Interactive PDF Labeler with Enhanced Features
===============================================================================
Fast, robust labeling interface with comprehensive feature extraction and validation.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import fitz  # PyMuPDF
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, asdict
import json
import logging
from collections import defaultdict
from datetime import datetime
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('labeling_tool.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class EnhancedFeatures:
    """Enhanced feature set for resume layout classification"""
    # Basic features
    num_columns: int
    mean_y_overlap: float
    coverage_gutter: float
    full_width_line_ratio: float
    valley_depth_ratio: float
    horizontal_lines_count: int
    header_fraction: float
    avg_word_width_ratio: float
    line_density_variance: float
    
    # Peak characteristics
    peak_count: int
    peak_widths: List[float]
    peak_heights: List[float]
    peak_separation: float
    
    # Valley characteristics
    valley_count: int
    valley_depths: List[float]
    valley_widths: List[float]
    valley_position: float  # normalized X position of primary valley
    
    # Additional discriminative features
    line_spacing_variance: float
    text_density: float  # words per page area
    max_line_width_ratio: float
    min_line_width_ratio: float
    width_bimodality: float  # measure of two distinct width distributions
    
    # Validation flags
    is_valid: bool = True
    validation_errors: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, handling list serialization"""
        d = asdict(self)
        # Convert lists to comma-separated strings for CSV
        d['peak_widths'] = ','.join(map(str, self.peak_widths)) if self.peak_widths else ''
        d['peak_heights'] = ','.join(map(str, self.peak_heights)) if self.peak_heights else ''
        d['valley_depths'] = ','.join(map(str, self.valley_depths)) if self.valley_depths else ''
        d['valley_widths'] = ','.join(map(str, self.valley_widths)) if self.valley_widths else ''
        d['validation_errors'] = ';'.join(self.validation_errors) if self.validation_errors else ''
        return d


class FeatureExtractor:
    """Fast, vectorized feature extraction from PDFs"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        
        # Configuration
        self.y_tolerance = 5
        self.full_width_fraction = 0.75
        self.gutter_zero_max = 0.05
        self.band_count = 60
        self.bins = 400
    
    def extract_all_features(self, pdf_path: str) -> Optional[EnhancedFeatures]:
        """Extract all features from PDF with error handling"""
        try:
            doc = fitz.open(pdf_path)
            page = doc[0]
            
            page_width = page.rect.width
            page_height = page.rect.height
            page_area = page_width * page_height
            
            # Extract words
            words = []
            word_dict = page.get_text("dict")
            
            for block in word_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue
                    
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if not text:
                            continue
                        
                        bbox = span.get("bbox", [0, 0, 0, 0])
                        words.append({
                            'text': text,
                            'bbox': bbox,
                            'font_size': span.get("size", 12.0)
                        })
            
            doc.close()
            
            if not words:
                logger.warning(f"No words extracted from {pdf_path}")
                return None
            
            # Extract coordinates
            x0 = np.array([w['bbox'][0] for w in words])
            x1 = np.array([w['bbox'][2] for w in words])
            y0 = np.array([w['bbox'][1] for w in words])
            y1 = np.array([w['bbox'][3] for w in words])
            xc = (x0 + x1) * 0.5
            yc = (y0 + y1) * 0.5
            
            # Compute all features
            features = self._compute_features(
                words, x0, x1, y0, y1, xc, yc,
                page_width, page_height, page_area
            )
            
            # Validate features
            features = self._validate_features(features)
            
            if self.verbose:
                logger.info(f"Extracted features from {Path(pdf_path).name}")
                if not features.is_valid:
                    logger.warning(f"Validation errors: {features.validation_errors}")
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features from {pdf_path}: {e}")
            logger.debug(traceback.format_exc())
            return None
    
    def _compute_features(
        self, words, x0, x1, y0, y1, xc, yc,
        page_width, page_height, page_area
    ) -> EnhancedFeatures:
        """Compute all features using vectorized operations"""
        
        n = len(words)
        
        # 1. Gutter metrics
        gutter_metrics = self._compute_gutter_metrics(
            x0, x1, y0, y1, xc, page_width, page_height
        )
        coverage_gutter = gutter_metrics['coverage']
        header_fraction = gutter_metrics['header_frac']
        num_columns = 2 if coverage_gutter >= 0.7 else 1
        
        # 2. Histogram analysis (peaks, valleys)
        hist_features = self._compute_histogram_features(xc, page_width)
        
        # 3. Y-overlap
        mean_y_overlap = self._compute_y_overlap(y0, y1)
        
        # 4. Line analysis
        lines = self._group_into_lines(words, y0, y1, yc)
        line_features = self._compute_line_features(
            lines, x0, x1, page_width
        )
        
        # 5. Text density
        text_density = n / page_area
        
        # 6. Width bimodality (measure of two column distributions)
        width_bimodality = self._compute_bimodality(xc, page_width)
        
        return EnhancedFeatures(
            num_columns=num_columns,
            mean_y_overlap=mean_y_overlap,
            coverage_gutter=coverage_gutter,
            full_width_line_ratio=line_features['full_width_ratio'],
            valley_depth_ratio=hist_features['valley_depth_ratio'],
            horizontal_lines_count=line_features['horizontal_count'],
            header_fraction=header_fraction,
            avg_word_width_ratio=float(np.mean(x1 - x0) / page_width),
            line_density_variance=line_features['density_variance'],
            peak_count=hist_features['peak_count'],
            peak_widths=hist_features['peak_widths'],
            peak_heights=hist_features['peak_heights'],
            peak_separation=hist_features['peak_separation'],
            valley_count=hist_features['valley_count'],
            valley_depths=hist_features['valley_depths'],
            valley_widths=hist_features['valley_widths'],
            valley_position=hist_features['valley_position'],
            line_spacing_variance=line_features['spacing_variance'],
            text_density=text_density,
            max_line_width_ratio=line_features['max_width_ratio'],
            min_line_width_ratio=line_features['min_width_ratio'],
            width_bimodality=width_bimodality
        )
    
    def _compute_gutter_metrics(self, x0, x1, y0, y1, xc, w, h):
        """Bandwise gutter analysis"""
        bins = self.bins
        band_count = self.band_count
        
        # Global density
        dens_global = np.zeros(bins, dtype=float)
        idx_all = np.clip((xc * bins / w).astype(int), 0, bins - 1)
        np.add.at(dens_global, idx_all, 1.0)
        dens_global = np.convolve(dens_global, np.ones(7) / 7, mode='same')
        dens_global /= max(1.0, dens_global.max())
        
        center_bin = np.argmin(dens_global[bins // 2 - bins // 8: bins // 2 + bins // 8]) + bins // 2 - bins // 8
        
        # Band analysis
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
        
        return {'coverage': coverage, 'header_frac': header_frac}
    
    def _compute_histogram_features(self, xc, page_width):
        """Detailed histogram analysis with peaks and valleys"""
        bins = max(200, int(page_width / 2))
        hist, bin_edges = np.histogram(xc, bins=bins, range=(0, page_width))
        
        # Smooth
        hist_smooth = np.convolve(hist.astype(float), np.ones(5) / 5, mode='same')
        hist_smooth /= max(hist_smooth.max(), 1.0)
        
        # Find peaks
        peaks = []
        for i in range(1, len(hist_smooth) - 1):
            if hist_smooth[i] > hist_smooth[i-1] and hist_smooth[i] > hist_smooth[i+1]:
                if hist_smooth[i] > 0.2:  # Significant peak
                    peaks.append(i)
        
        # Find valleys
        valleys = []
        for i in range(1, len(hist_smooth) - 1):
            if hist_smooth[i] < hist_smooth[i-1] and hist_smooth[i] < hist_smooth[i+1]:
                valleys.append(i)
        
        # Peak characteristics
        peak_count = len(peaks)
        peak_heights = [float(hist_smooth[p]) for p in peaks]
        peak_widths = self._compute_peak_widths(hist_smooth, peaks)
        peak_separation = 0.0
        if len(peaks) >= 2:
            peak_separation = abs(peaks[1] - peaks[0]) / bins
        
        # Valley characteristics
        valley_count = len(valleys)
        valley_depths = [float(hist_smooth[v]) for v in valleys]
        valley_widths = self._compute_valley_widths(hist_smooth, valleys)
        valley_position = 0.5
        if valleys:
            primary_valley = valleys[np.argmin([hist_smooth[v] for v in valleys])]
            valley_position = primary_valley / bins
        
        valley_depth_ratio = min(valley_depths) if valley_depths else 1.0
        
        return {
            'peak_count': peak_count,
            'peak_heights': peak_heights,
            'peak_widths': peak_widths,
            'peak_separation': peak_separation,
            'valley_count': valley_count,
            'valley_depths': valley_depths,
            'valley_widths': valley_widths,
            'valley_position': valley_position,
            'valley_depth_ratio': valley_depth_ratio
        }
    
    def _compute_peak_widths(self, hist, peaks):
        """Compute FWHM for each peak"""
        widths = []
        for peak_idx in peaks:
            height = hist[peak_idx]
            half_height = height / 2
            
            # Find left boundary
            left = peak_idx
            while left > 0 and hist[left] > half_height:
                left -= 1
            
            # Find right boundary
            right = peak_idx
            while right < len(hist) - 1 and hist[right] > half_height:
                right += 1
            
            width = (right - left) / len(hist)
            widths.append(float(width))
        
        return widths
    
    def _compute_valley_widths(self, hist, valleys):
        """Compute width of each valley at 50% depth"""
        widths = []
        for valley_idx in valleys:
            depth = hist[valley_idx]
            half_depth = (1.0 - depth) / 2 + depth
            
            # Find left boundary
            left = valley_idx
            while left > 0 and hist[left] < half_depth:
                left -= 1
            
            # Find right boundary
            right = valley_idx
            while right < len(hist) - 1 and hist[right] < half_depth:
                right += 1
            
            width = (right - left) / len(hist)
            widths.append(float(width))
        
        return widths
    
    def _compute_y_overlap(self, y0, y1):
        """Efficient Y-overlap computation with sampling for large documents"""
        n = len(y0)
        if n < 2:
            return 0.0
        
        heights = y1 - y0
        
        # Sample for efficiency
        max_pairs = 5000
        if n * (n - 1) // 2 > max_pairs:
            sample_size = min(n, 150)
            indices = np.random.choice(n, size=sample_size, replace=False)
            y0_sample = y0[indices]
            y1_sample = y1[indices]
            heights_sample = heights[indices]
        else:
            y0_sample, y1_sample, heights_sample = y0, y1, heights
        
        overlaps = []
        n_sample = len(y0_sample)
        for i in range(n_sample - 1):
            for j in range(i + 1, min(i + 20, n_sample)):  # Limit comparisons
                h_min = min(heights_sample[i], heights_sample[j])
                if h_min > 0:
                    overlap = max(0, min(y1_sample[i], y1_sample[j]) - max(y0_sample[i], y0_sample[j]))
                    overlaps.append(overlap / h_min)
        
        return float(np.mean(overlaps)) if overlaps else 0.0
    
    def _group_into_lines(self, words, y0, y1, yc):
        """Group words into lines"""
        lines = defaultdict(list)
        for idx, word in enumerate(words):
            y_center = yc[idx]
            placed = False
            for line_y in list(lines.keys()):
                if abs(y_center - line_y) <= self.y_tolerance:
                    lines[line_y].append(idx)
                    placed = True
                    break
            if not placed:
                lines[y_center].append(idx)
        
        return sorted(lines.items(), key=lambda x: x[0])
    
    def _compute_line_features(self, lines, x0, x1, page_width):
        """Compute line-based features"""
        full_width_count = 0
        line_widths = []
        line_densities = []
        line_spacings = []
        
        prev_y = None
        for y, indices in lines:
            if indices:
                x_start = min(x0[indices])
                x_end = max(x1[indices])
                width = x_end - x_start
                line_widths.append(width)
                line_densities.append(len(indices))
                
                if width >= page_width * self.full_width_fraction:
                    full_width_count += 1
                
                if prev_y is not None:
                    line_spacings.append(abs(y - prev_y))
                prev_y = y
        
        n_lines = len(lines)
        full_width_ratio = full_width_count / max(n_lines, 1)
        density_variance = float(np.var(line_densities)) if line_densities else 0.0
        spacing_variance = float(np.var(line_spacings)) if line_spacings else 0.0
        
        max_width_ratio = float(max(line_widths) / page_width) if line_widths else 0.0
        min_width_ratio = float(min(line_widths) / page_width) if line_widths else 0.0
        
        return {
            'full_width_ratio': full_width_ratio,
            'horizontal_count': full_width_count,
            'density_variance': density_variance,
            'spacing_variance': spacing_variance,
            'max_width_ratio': max_width_ratio,
            'min_width_ratio': min_width_ratio
        }
    
    def _compute_bimodality(self, xc, page_width):
        """Measure bimodality in X distribution (indicates two columns)"""
        # Fit two Gaussians and measure separation
        left_mask = xc < page_width / 2
        right_mask = xc >= page_width / 2
        
        if not np.any(left_mask) or not np.any(right_mask):
            return 0.0
        
        left_mean = np.mean(xc[left_mask])
        right_mean = np.mean(xc[right_mask])
        left_std = np.std(xc[left_mask])
        right_std = np.std(xc[right_mask])
        
        # Bimodality coefficient
        separation = abs(right_mean - left_mean) / page_width
        overlap = (left_std + right_std) / page_width
        
        bimodality = separation / max(overlap, 0.01)
        return float(bimodality)
    
    def _validate_features(self, features: EnhancedFeatures) -> EnhancedFeatures:
        """Validate feature values and flag errors"""
        errors = []
        
        # Check ranges
        if not (0 <= features.coverage_gutter <= 1):
            errors.append(f"coverage_gutter out of range: {features.coverage_gutter}")
        
        if not (0 <= features.valley_depth_ratio <= 1):
            errors.append(f"valley_depth_ratio out of range: {features.valley_depth_ratio}")
        
        if not (0 <= features.full_width_line_ratio <= 1):
            errors.append(f"full_width_line_ratio out of range: {features.full_width_line_ratio}")
        
        if features.num_columns < 1 or features.num_columns > 3:
            errors.append(f"Suspicious num_columns: {features.num_columns}")
        
        if features.peak_count > 5:
            errors.append(f"Too many peaks: {features.peak_count}")
        
        if any(h < 0 or h > 1 for h in features.peak_heights):
            errors.append("Peak heights out of range")
        
        if any(d < 0 or d > 1 for d in features.valley_depths):
            errors.append("Valley depths out of range")
        
        if features.text_density < 0:
            errors.append(f"Negative text density: {features.text_density}")
        
        # Update validation status
        features.is_valid = len(errors) == 0
        features.validation_errors = errors if errors else None
        
        return features


class PDFLabelingTool:
    """Interactive PDF labeling tool with Tkinter GUI"""
    
    def __init__(self, pdf_directory: str, dataset_path: str = "labeled_dataset.csv"):
        self.pdf_directory = Path(pdf_directory)
        self.dataset_path = Path(dataset_path)
        self.extractor = FeatureExtractor(verbose=True)
        
        # Load PDFs
        self.pdf_files = sorted(self.pdf_directory.glob("**/*.pdf"))
        logger.info(f"Found {len(self.pdf_files)} PDF files")
        
        # Load existing labels
        self.labeled_data = self._load_existing_labels()
        self.labeled_files = set(self.labeled_data['filename']) if not self.labeled_data.empty else set()
        
        # Precompute features
        self.features_cache = {}
        self.current_index = 0
        self.current_pdf_img = None
        
        # Find first unlabeled
        self._find_next_unlabeled()
        
        # Create GUI
        self.root = tk.Tk()
        self.root.title("Advanced Resume Labeling Tool")
        self.root.geometry("1600x900")
        
        self._create_gui()
        self._preload_features()
    
    def _load_existing_labels(self) -> pd.DataFrame:
        """Load existing labeled data"""
        if self.dataset_path.exists():
            try:
                return pd.read_csv(self.dataset_path)
            except Exception as e:
                logger.error(f"Error loading dataset: {e}")
                return pd.DataFrame()
        return pd.DataFrame()
    
    def _find_next_unlabeled(self):
        """Jump to next unlabeled PDF"""
        while self.current_index < len(self.pdf_files):
            if self.pdf_files[self.current_index].name not in self.labeled_files:
                return
            self.current_index += 1
    
    def _create_gui(self):
        """Create the Tkinter interface"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - PDF viewer
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # PDF display
        self.pdf_label = ttk.Label(left_frame, text="PDF Preview", relief=tk.SUNKEN)
        self.pdf_label.pack(fill=tk.BOTH, expand=True)
        
        # Right panel - Controls
        right_frame = ttk.Frame(main_frame, width=500)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        right_frame.pack_propagate(False)
        
        # Progress info
        progress_frame = ttk.LabelFrame(right_frame, text="Progress", padding=10)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_label = ttk.Label(progress_frame, text="", font=('Arial', 10))
        self.progress_label.pack()
        
        self.progressbar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progressbar.pack(fill=tk.X, pady=5)
        
        # Current file info
        file_frame = ttk.LabelFrame(right_frame, text="Current File", padding=10)
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.file_label = ttk.Label(file_frame, text="", wraplength=450, font=('Arial', 9, 'bold'))
        self.file_label.pack()
        
        # Labeling buttons
        label_frame = ttk.LabelFrame(right_frame, text="Assign Label", padding=10)
        label_frame.pack(fill=tk.X, pady=(0, 10))
        
        button_frame = ttk.Frame(label_frame)
        button_frame.pack(fill=tk.X)
        
        self.type1_btn = tk.Button(
            button_frame, text="Type 1\nSingle Column", 
            command=lambda: self.save_label(1),
            bg='#4CAF50', fg='white', font=('Arial', 10, 'bold'),
            height=3
        )
        self.type1_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        self.type2_btn = tk.Button(
            button_frame, text="Type 2\nMulti-Column", 
            command=lambda: self.save_label(2),
            bg='#2196F3', fg='white', font=('Arial', 10, 'bold'),
            height=3
        )
        self.type2_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        self.type3_btn = tk.Button(
            button_frame, text="Type 3\nHybrid", 
            command=lambda: self.save_label(3),
            bg='#FF9800', fg='white', font=('Arial', 10, 'bold'),
            height=3
        )
        self.type3_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # Navigation buttons
        nav_frame = ttk.LabelFrame(right_frame, text="Navigation", padding=10)
        nav_frame.pack(fill=tk.X, pady=(0, 10))
        
        nav_button_frame = ttk.Frame(nav_frame)
        nav_button_frame.pack(fill=tk.X)
        
        self.prev_btn = ttk.Button(nav_button_frame, text="◀ Previous", command=self.previous_pdf)
        self.prev_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        self.skip_btn = ttk.Button(nav_button_frame, text="Skip ⏭", command=self.skip_pdf)
        self.skip_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        self.next_btn = ttk.Button(nav_button_frame, text="Next ▶", command=self.next_pdf)
        self.next_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # Features table with scrollbar
        features_frame = ttk.LabelFrame(right_frame, text="Computed Features", padding=10)
        features_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview with scrollbar
        tree_scroll = ttk.Scrollbar(features_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.features_tree = ttk.Treeview(
            features_frame,
            columns=('Feature', 'Value', 'Status'),
            show='headings',
            height=20,
            yscrollcommand=tree_scroll.set
        )
        tree_scroll.config(command=self.features_tree.yview)
        
        self.features_tree.heading('Feature', text='Feature')
        self.features_tree.heading('Value', text='Value')
        self.features_tree.heading('Status', text='Status')
        
        self.features_tree.column('Feature', width=200)
        self.features_tree.column('Value', width=150)
        self.features_tree.column('Status', width=80)
        
        self.features_tree.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for validation
        self.features_tree.tag_configure('error', foreground='red')
        self.features_tree.tag_configure('warning', foreground='orange')
        self.features_tree.tag_configure('ok', foreground='green')
        
        # Keyboard shortcuts
        self.root.bind('1', lambda e: self.save_label(1))
        self.root.bind('2', lambda e: self.save_label(2))
        self.root.bind('3', lambda e: self.save_label(3))
        self.root.bind('<Left>', lambda e: self.previous_pdf())
        self.root.bind('<Right>', lambda e: self.next_pdf())
        self.root.bind('<space>', lambda e: self.skip_pdf())
    
    def _preload_features(self):
        """Precompute features for all PDFs"""
        logger.info("Preloading features for all PDFs...")
        
        for idx, pdf_path in enumerate(self.pdf_files):
            if pdf_path.name not in self.features_cache:
                features = self.extractor.extract_all_features(str(pdf_path))
                self.features_cache[pdf_path.name] = features
            
            # Update progress
            if (idx + 1) % 10 == 0:
                logger.info(f"Preloaded {idx + 1}/{len(self.pdf_files)} PDFs")
        
        logger.info("Preloading complete!")
        self.display_current_pdf()
    
    def display_current_pdf(self):
        """Display current PDF and features"""
        if self.current_index >= len(self.pdf_files):
            self.show_completion()
            return
        
        pdf_path = self.pdf_files[self.current_index]
        
        # Update progress
        labeled_count = len(self.labeled_files)
        total = len(self.pdf_files)
        self.progress_label.config(
            text=f"Labeled: {labeled_count}/{total} ({labeled_count/total*100:.1f}%)"
        )
        self.progressbar['value'] = (labeled_count / total) * 100
        
        # Update file label
        self.file_label.config(text=f"{pdf_path.name}\n[{self.current_index + 1}/{total}]")
        
        # Render PDF
        try:
            doc = fitz.open(str(pdf_path))
            page = doc[0]
            
            # Render at good quality
            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Resize to fit display
            display_height = 800
            aspect = img.width / img.height
            display_width = int(display_height * aspect)
            img = img.resize((display_width, display_height), Image.Resampling.LANCZOS)
            
            self.current_pdf_img = ImageTk.PhotoImage(img)
            self.pdf_label.config(image=self.current_pdf_img)
            
            doc.close()
        except Exception as e:
            logger.error(f"Error rendering PDF: {e}")
            self.pdf_label.config(text=f"Error rendering PDF:\n{e}")
        
        # Display features
        self.display_features(pdf_path.name)
    
    def display_features(self, filename: str):
        """Display features in tree view with validation"""
        # Clear existing
        for item in self.features_tree.get_children():
            self.features_tree.delete(item)
        
        features = self.features_cache.get(filename)
        
        if features is None:
            self.features_tree.insert('', 'end', values=('ERROR', 'Failed to extract', 'ERROR'), tags=('error',))
            return
        
        # Display features with validation
        feature_dict = features.to_dict()
        
        for key, value in feature_dict.items():
            if key in ['validation_errors', 'is_valid']:
                continue
            
            # Format value
            if isinstance(value, float):
                value_str = f"{value:.4f}"
            elif isinstance(value, str) and ',' in value:
                # List values
                value_str = value[:50] + '...' if len(value) > 50 else value
            else:
                value_str = str(value)
            
            # Determine status
            status = '✓'
            tag = 'ok'
            
            # Check for issues
            if key == 'num_columns' and value == 2 and features.coverage_gutter < 0.5:
                status = '⚠'
                tag = 'warning'
            
            if key == 'valley_depth_ratio' and (value < 0 or value > 1):
                status = '✗'
                tag = 'error'
            
            if key == 'coverage_gutter' and (value < 0 or value > 1):
                status = '✗'
                tag = 'error'
            
            self.features_tree.insert('', 'end', values=(key, value_str, status), tags=(tag,))
        
        # Show validation errors if any
        if features.validation_errors:
            for error in features.validation_errors:
                self.features_tree.insert('', 'end', values=('VALIDATION ERROR', error, '✗'), tags=('error',))
    
    def save_label(self, label: int):
        """Save current label and move to next"""
        if self.current_index >= len(self.pdf_files):
            return
        
        pdf_path = self.pdf_files[self.current_index]
        features = self.features_cache.get(pdf_path.name)
        
        if features is None:
            messagebox.showerror("Error", "Cannot label PDF with failed feature extraction")
            return
        
        # Prepare data
        row_data = {
            'filename': pdf_path.name,
            **features.to_dict(),
            'label': label,
            'labeled_at': datetime.now().isoformat()
        }
        
        # Append to dataset
        df_new = pd.DataFrame([row_data])
        
        if self.dataset_path.exists():
            df_existing = pd.read_csv(self.dataset_path)
            # Remove old entry if re-labeling
            df_existing = df_existing[df_existing['filename'] != pdf_path.name]
            df = pd.concat([df_existing, df_new], ignore_index=True)
        else:
            df = df_new
        
        df.to_csv(self.dataset_path, index=False)
        
        # Save JSON version
        json_path = self.dataset_path.with_suffix('.json')
        df.to_json(json_path, orient='records', indent=2)
        
        # Update state
        self.labeled_files.add(pdf_path.name)
        self.labeled_data = df
        
        logger.info(f"Labeled {pdf_path.name} as Type {label}")
        
        # Move to next unlabeled
        self.current_index += 1
        self._find_next_unlabeled()
        self.display_current_pdf()
    
    def next_pdf(self):
        """Move to next PDF"""
        if self.current_index < len(self.pdf_files) - 1:
            self.current_index += 1
            self.display_current_pdf()
    
    def previous_pdf(self):
        """Move to previous PDF"""
        if self.current_index > 0:
            self.current_index -= 1
            self.display_current_pdf()
    
    def skip_pdf(self):
        """Skip current PDF without labeling"""
        self.current_index += 1
        self._find_next_unlabeled()
        self.display_current_pdf()
    
    def show_completion(self):
        """Show completion message"""
        messagebox.showinfo(
            "Complete!",
            f"All PDFs have been processed!\n\n"
            f"Total labeled: {len(self.labeled_files)}/{len(self.pdf_files)}\n"
            f"Dataset saved to: {self.dataset_path}"
        )
        
        # Show summary
        if not self.labeled_data.empty:
            summary = self.labeled_data['label'].value_counts().sort_index()
            summary_text = "\n".join([f"Type {k}: {v}" for k, v in summary.items()])
            messagebox.showinfo("Label Distribution", summary_text)
    
    def run(self):
        """Start the application"""
        self.root.mainloop()


def main():
    """Entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Advanced PDF Resume Labeling Tool")
    parser.add_argument(
        '--pdf-dir',
        type=str,
        default='Resumes',
        help='Directory containing PDF files'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='labeled_dataset.csv',
        help='Output dataset path'
    )
    
    args = parser.parse_args()
    
    logger.info("Starting Advanced PDF Labeling Tool")
    logger.info(f"PDF Directory: {args.pdf_dir}")
    logger.info(f"Output: {args.output}")
    
    app = PDFLabelingTool(args.pdf_dir, args.output)
    app.run()


if __name__ == "__main__":
    main()
