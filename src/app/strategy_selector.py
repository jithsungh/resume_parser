"""
Strategy Selector
=================

Selects the best parsing strategy based on file and layout analysis.
"""

from typing import Dict, Any


class StrategySelector:
    """
    Selects optimal parsing strategy based on file characteristics.
    """
    
    def __init__(self):
        """Initialize the strategy selector."""
        pass
    
    def select(
        self, 
        file_info: Dict[str, Any], 
        layout_info: Dict[str, Any]
    ) -> str:
        """
        Select best parsing strategy.
        
        Args:
            file_info: File type and characteristics from FileDetector
            layout_info: Layout analysis from LayoutAnalyzer
            
        Returns:
            Strategy name: 'pdf', 'ocr', 'region', or 'docx'
        """
        file_type = file_info.get('type', 'unknown')
        
        # Handle different file types
        if file_type == 'unknown':
            return 'pdf'  # Default fallback
        
        if file_type == 'docx':
            return 'docx'
        
        if file_type == 'image':
            return 'ocr'
        
        if file_type == 'pdf':
            # Check if scanned
            is_scanned = layout_info.get('is_scanned', False)
            if is_scanned:
                return 'ocr'
            
            # Check if multi-column
            num_columns = layout_info.get('num_columns', 1)
            if num_columns > 1:
                return 'region'
            
            # Default to standard PDF parsing
            return 'pdf'
        
        return 'pdf'  # Default fallback
