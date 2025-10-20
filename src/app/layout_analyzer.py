"""
Layout Analyzer
===============

Analyzes PDF layout characteristics for intelligent parsing.
"""

from pathlib import Path
from typing import Dict, Any
import fitz  # PyMuPDF


class LayoutAnalyzer:
    """
    Analyzes PDF layout to determine parsing strategy.
    """
    
    def __init__(self):
        """Initialize the layout analyzer."""
        pass
    
    def analyze(self, pdf_path: str) -> Dict[str, Any]:
        """
        Analyze PDF layout characteristics.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with:
            - type: Layout type ('single', 'multi', 'complex')
            - num_columns: Estimated number of columns
            - num_regions: Number of distinct regions
            - is_scanned: Whether PDF is scanned
            - has_text_layer: Whether PDF has text layer
            - num_pages: Number of pages
            - confidence: Confidence score (0-1)
        """
        result = {
            'type': 'single',
            'num_columns': 1,
            'num_regions': 1,
            'is_scanned': False,
            'has_text_layer': True,
            'num_pages': 0,
            'confidence': 0.5
        }
        
        try:
            doc = fitz.open(str(Path(pdf_path).resolve()))
            result['num_pages'] = len(doc)
            
            if len(doc) == 0:
                doc.close()
                return result
            
            # Analyze first page
            page = doc[0]
            
            # Check for text layer
            text = page.get_text().strip()
            
            if len(text) < 50:
                result['is_scanned'] = True
                result['has_text_layer'] = False
                result['confidence'] = 0.9
                doc.close()
                return result
            
            result['has_text_layer'] = True
            
            # Analyze column layout
            words = page.get_text("words")
            
            if len(words) > 20:
                page_width = page.rect.width
                mid_x = page_width / 2
                
                # Count words in left vs right half
                left_count = sum(1 for w in words if w[0] < mid_x)
                right_count = sum(1 for w in words if w[0] >= mid_x)
                
                # Check for multi-column layout
                if left_count > 10 and right_count > 10:
                    ratio = min(left_count, right_count) / max(left_count, right_count)
                    if ratio > 0.3:  # At least 30% balance
                        result['num_columns'] = 2
                        result['num_regions'] = 2
                        result['type'] = 'multi'
                        result['confidence'] = 0.8
                    else:
                        result['type'] = 'single'
                        result['confidence'] = 0.7
                else:
                    result['type'] = 'single'
                    result['confidence'] = 0.9
            
            doc.close()
            
        except Exception as e:
            result['error'] = str(e)
            result['confidence'] = 0.0
        
        return result
