"""
Adaptive threshold adjustment for robust resume parsing.
Dynamically adjusts detection thresholds based on document characteristics.
"""

import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from collections import Counter


class AdaptiveThresholds:
    """
    Manages adaptive thresholds for heading detection, block splitting, etc.
    Adjusts thresholds based on document statistics and characteristics.
    """
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset all thresholds to defaults."""
        # Heading detection thresholds
        self.heading_score_threshold = 0.3
        self.min_heading_spacing = 1.5
        self.min_heading_font_ratio = 1.15
        
        # Block detection thresholds
        self.column_tolerance = 0.05
        self.band_tolerance = 0.02
        self.min_block_area = 100
        
        # Layout analysis thresholds
        self.multi_column_threshold = 2
        self.vertical_layout_bands = 3
        
        # Statistics
        self.stats = {}
    
    def analyze_document(self, pages_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze document characteristics to set appropriate thresholds.
        
        Args:
            pages_data: List of page data with text and layout info
            
        Returns:
            Document statistics dictionary
        """
        stats = {
            'num_pages': len(pages_data),
            'avg_lines_per_page': 0,
            'font_sizes': [],
            'spacings': [],
            'line_widths': [],
            'uppercase_ratios': [],
            'detected_layouts': [],
        }
        
        total_lines = 0
        
        for page in pages_data:
            lines = page.get('lines', [])
            total_lines += len(lines)
            
            for line in lines:
                # Collect font sizes
                if 'height' in line:
                    stats['font_sizes'].append(line['height'])
                
                # Collect spacings
                if 'spacing' in line:
                    stats['spacings'].append(line['spacing'])
                
                # Collect line widths
                if 'width' in line:
                    stats['line_widths'].append(line['width'])
                
                # Analyze text characteristics
                text = line.get('text', '')
                if text:
                    upper_count = sum(1 for c in text if c.isupper())
                    total_alpha = sum(1 for c in text if c.isalpha())
                    if total_alpha > 0:
                        stats['uppercase_ratios'].append(upper_count / total_alpha)
            
            # Detect layout type for this page
            layout = page.get('layout', {})
            if layout:
                stats['detected_layouts'].append(layout.get('type', 'unknown'))
        
        if stats['num_pages'] > 0:
            stats['avg_lines_per_page'] = total_lines / stats['num_pages']
        
        # Compute statistics
        if stats['font_sizes']:
            stats['font_size_mean'] = np.mean(stats['font_sizes'])
            stats['font_size_std'] = np.std(stats['font_sizes'])
            stats['font_size_median'] = np.median(stats['font_sizes'])
            stats['font_size_q75'] = np.percentile(stats['font_sizes'], 75)
            stats['font_size_q25'] = np.percentile(stats['font_sizes'], 25)
        
        if stats['spacings']:
            stats['spacing_mean'] = np.mean(stats['spacings'])
            stats['spacing_std'] = np.std(stats['spacings'])
            stats['spacing_median'] = np.median(stats['spacings'])
            stats['spacing_q75'] = np.percentile(stats['spacings'], 75)
        
        if stats['uppercase_ratios']:
            stats['uppercase_mean'] = np.mean(stats['uppercase_ratios'])
            stats['uppercase_median'] = np.median(stats['uppercase_ratios'])
        
        # Layout distribution
        if stats['detected_layouts']:
            layout_counts = Counter(stats['detected_layouts'])
            stats['primary_layout'] = layout_counts.most_common(1)[0][0]
            stats['layout_distribution'] = dict(layout_counts)
        
        self.stats = stats
        return stats
    
    def adjust_thresholds(self, stats: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """
        Adjust thresholds based on document statistics.
        
        Args:
            stats: Document statistics (uses self.stats if None)
            
        Returns:
            Dictionary of adjusted thresholds
        """
        if stats is None:
            stats = self.stats
        
        if not stats:
            return self.get_current_thresholds()
        
        # Adjust heading score threshold based on document characteristics
        # Complex documents with many varied fonts/sizes need lower threshold
        if 'font_size_std' in stats:
            font_variance = stats['font_size_std'] / max(1.0, stats.get('font_size_mean', 1.0))
            
            if font_variance > 0.5:
                # High variance = more distinct heading styles
                self.heading_score_threshold = 0.25
            elif font_variance > 0.3:
                self.heading_score_threshold = 0.3
            else:
                # Low variance = need stricter matching
                self.heading_score_threshold = 0.35
        
        # Adjust font ratio based on document font distribution
        if 'font_size_q75' in stats and 'font_size_median' in stats:
            ratio = stats['font_size_q75'] / max(1.0, stats['font_size_median'])
            
            if ratio > 1.5:
                # Large variation in font sizes
                self.min_heading_font_ratio = 1.1
            elif ratio > 1.2:
                self.min_heading_font_ratio = 1.15
            else:
                # Similar font sizes throughout
                self.min_heading_font_ratio = 1.05
        
        # Adjust spacing threshold based on document density
        if 'spacing_median' in stats and 'spacing_q75' in stats:
            spacing_ratio = stats['spacing_q75'] / max(1.0, stats['spacing_median'])
            
            if spacing_ratio > 2.0:
                # High spacing variance
                self.min_heading_spacing = 1.3
            elif spacing_ratio > 1.5:
                self.min_heading_spacing = 1.5
            else:
                # Uniform spacing
                self.min_heading_spacing = 1.8
        
        # Adjust layout detection based on detected layouts
        primary_layout = stats.get('primary_layout', 'unknown')
        
        if primary_layout == 'horizontal':
            # Multi-column resumes need tighter column tolerance
            self.column_tolerance = 0.03
            self.band_tolerance = 0.03
        elif primary_layout == 'vertical':
            # Single column resumes can use looser tolerance
            self.column_tolerance = 0.08
            self.band_tolerance = 0.015
        elif primary_layout == 'hybrid':
            # Mixed layouts need balanced thresholds
            self.column_tolerance = 0.05
            self.band_tolerance = 0.02
        
        # Adjust block area based on document size
        if 'avg_lines_per_page' in stats:
            lines_per_page = stats['avg_lines_per_page']
            
            if lines_per_page > 50:
                # Dense documents
                self.min_block_area = 50
            elif lines_per_page > 30:
                self.min_block_area = 100
            else:
                # Sparse documents
                self.min_block_area = 150
        
        return self.get_current_thresholds()
    
    def get_current_thresholds(self) -> Dict[str, float]:
        """Get current threshold values."""
        return {
            'heading_score_threshold': self.heading_score_threshold,
            'min_heading_spacing': self.min_heading_spacing,
            'min_heading_font_ratio': self.min_heading_font_ratio,
            'column_tolerance': self.column_tolerance,
            'band_tolerance': self.band_tolerance,
            'min_block_area': self.min_block_area,
            'multi_column_threshold': self.multi_column_threshold,
            'vertical_layout_bands': self.vertical_layout_bands,
        }
    
    def adjust_for_page(self, page_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Adjust thresholds for a specific page.
        Useful for multi-page documents where pages may have different characteristics.
        
        Args:
            page_data: Page data with layout and text info
            
        Returns:
            Page-specific thresholds
        """
        # Create temporary stats for this page
        page_stats = self.analyze_document([page_data])
        
        # Adjust and return
        return self.adjust_thresholds(page_stats)
    
    def get_heading_score_components(self, features: Dict[str, float]) -> Dict[str, float]:
        """
        Compute individual components of heading score with adaptive weights.
        
        Args:
            features: Feature dictionary from compute_text_features
            
        Returns:
            Dictionary of score components
        """
        components = {}
        
        # Keyword match (most important)
        if features.get('has_keyword', 0) > 0:
            components['keyword'] = 0.4
        else:
            components['keyword'] = 0.0
        
        # Length (short is better)
        if features.get('short_enough', 0) > 0:
            components['length'] = 0.15
        else:
            components['length'] = 0.0
        
        # Uppercase/title case
        upper_ratio = features.get('upper_ratio', 0)
        title_case = features.get('title_case', 0)
        
        if upper_ratio > 0.7:
            components['case'] = 0.2
        elif title_case > 0.8:
            components['case'] = 0.15
        else:
            components['case'] = 0.0
        
        # Trailing colon
        if features.get('has_colon', 0) > 0:
            components['colon'] = 0.1
        else:
            components['colon'] = 0.0
        
        # Font size (if available)
        if 'font_ratio' in features:
            if features['font_ratio'] > self.min_heading_font_ratio:
                components['font'] = 0.1
            else:
                components['font'] = 0.0
        else:
            components['font'] = 0.0
        
        # Spacing (if available)
        if 'spacing_ratio' in features:
            if features['spacing_ratio'] > self.min_heading_spacing:
                components['spacing'] = 0.15
            else:
                components['spacing'] = 0.0
        else:
            components['spacing'] = 0.0
        
        # Position bonus
        if features.get('position_index', 100) < 3:
            components['position'] = 0.05
        else:
            components['position'] = 0.0
        
        return components
    
    def compute_adaptive_score(self, features: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
        """
        Compute heading score using adaptive thresholds.
        
        Args:
            features: Feature dictionary
            
        Returns:
            Tuple of (total_score, score_components)
        """
        components = self.get_heading_score_components(features)
        total_score = sum(components.values())
        
        return total_score, components
    
    def is_likely_heading(self, score: float, components: Optional[Dict[str, float]] = None) -> bool:
        """
        Determine if a line is likely a heading based on score and components.
        
        Args:
            score: Total heading score
            components: Optional score components for detailed analysis
            
        Returns:
            True if likely a heading
        """
        # Primary check: score threshold
        if score >= self.heading_score_threshold:
            return True
        
        # Secondary check: strong individual signals
        if components:
            # Keyword match alone is very strong
            if components.get('keyword', 0) >= 0.4:
                return True
            
            # Combination of uppercase + colon + short
            if (components.get('case', 0) >= 0.15 and 
                components.get('colon', 0) > 0 and 
                components.get('length', 0) > 0):
                return True
        
        return False


def create_adaptive_pipeline_wrapper(base_pipeline_func):
    """
    Wrapper to add adaptive threshold adjustment to any pipeline function.
    
    Args:
        base_pipeline_func: Base pipeline function to wrap
        
    Returns:
        Wrapped function with adaptive thresholds
    """
    def wrapped_pipeline(*args, **kwargs):
        # Extract or create adaptive thresholds
        adaptive = kwargs.pop('adaptive_thresholds', None)
        if adaptive is None:
            adaptive = AdaptiveThresholds()
        
        # Run base pipeline
        result, simplified = base_pipeline_func(*args, **kwargs)
        
        # Analyze results and adjust thresholds for next run
        pages_data = result.get('pages', [])
        if pages_data:
            stats = adaptive.analyze_document(pages_data)
            adaptive.adjust_thresholds(stats)
            
            # Add statistics to result
            result['adaptive_stats'] = stats
            result['adaptive_thresholds'] = adaptive.get_current_thresholds()
        
        return result, simplified
    
    return wrapped_pipeline


if __name__ == "__main__":
    # Test adaptive thresholds
    adaptive = AdaptiveThresholds()
    
    # Simulate document with high font variance
    mock_stats = {
        'num_pages': 2,
        'avg_lines_per_page': 45,
        'font_size_mean': 12.0,
        'font_size_std': 6.0,
        'font_size_median': 11.0,
        'font_size_q75': 14.0,
        'font_size_q25': 10.0,
        'spacing_mean': 3.0,
        'spacing_median': 2.5,
        'spacing_q75': 5.0,
        'uppercase_mean': 0.15,
        'primary_layout': 'hybrid',
    }
    
    print("Default thresholds:")
    print(adaptive.get_current_thresholds())
    
    print("\nAdjusting based on document stats...")
    adjusted = adaptive.adjust_thresholds(mock_stats)
    
    print("\nAdjusted thresholds:")
    for key, value in adjusted.items():
        print(f"  {key}: {value}")
    
    # Test heading score computation
    test_features = {
        'has_keyword': 1.0,
        'short_enough': 1.0,
        'upper_ratio': 0.9,
        'title_case': 0.5,
        'has_colon': 0.0,
        'font_ratio': 1.3,
        'spacing_ratio': 2.0,
        'position_index': 1,
    }
    
    score, components = adaptive.compute_adaptive_score(test_features)
    print(f"\nTest heading score: {score:.2f}")
    print("Components:")
    for key, value in components.items():
        print(f"  {key}: {value:.2f}")
    
    print(f"\nIs likely heading: {adaptive.is_likely_heading(score, components)}")
