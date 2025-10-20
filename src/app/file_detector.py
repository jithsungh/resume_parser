"""
File Type Detection
===================

Detect resume file types (PDF, DOCX, images) and their characteristics.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import fitz  # PyMuPDF


class FileDetector:
    """
    Detects file types and analyzes their characteristics.
    """
    
    def __init__(self):
        """Initialize the file detector."""
        pass
    
    def detect(self, file_path: str) -> Dict[str, Any]:
        """
        Detect file type and analyze characteristics.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with:
            - type: File type ('pdf', 'docx', 'image', 'unknown')
            - characteristics: File characteristics (for PDFs)
            - should_use_ocr: Whether OCR is recommended
            - recommended_strategy: Recommended parsing strategy
        """
        file_type = detect_file_type(file_path)
        
        result = {
            'type': file_type,
            'should_use_ocr': should_use_ocr(file_path),
            'recommended_strategy': get_recommended_strategy(file_path)
        }
        
        # Add PDF characteristics if it's a PDF
        if file_type == 'pdf':
            result['characteristics'] = analyze_pdf_characteristics(file_path)
        
        return result


def detect_file_type(file_path: str) -> str:
    """
    Detect file type from extension.
    
    Args:
        file_path: Path to file
        
    Returns:
        File type: 'pdf', 'docx', 'image', or 'unknown'
    """
    suffix = Path(file_path).suffix.lower()
    
    if suffix == '.pdf':
        return 'pdf'
    elif suffix in ['.docx', '.doc']:
        return 'docx'
    elif suffix in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
        return 'image'
    else:
        return 'unknown'


def analyze_pdf_characteristics(pdf_path: str) -> Dict[str, Any]:
    """
    Analyze PDF characteristics to guide parsing strategy.
    
    Returns:
        Dictionary with:
        - is_scanned: bool
        - has_text_layer: bool
        - num_pages: int
        - is_multi_column: bool
        - estimated_columns: int
        - page_dimensions: tuple
    """
    pdf_path = str(Path(pdf_path).resolve())
    
    result = {
        'is_scanned': False,
        'has_text_layer': True,
        'num_pages': 0,
        'is_multi_column': False,
        'estimated_columns': 1,
        'page_dimensions': (0, 0),
        'confidence': 0.5
    }
    
    try:
        doc = fitz.open(pdf_path)
        result['num_pages'] = len(doc)
        
        if len(doc) == 0:
            doc.close()
            return result
        
        # Analyze first page
        page = doc[0]
        result['page_dimensions'] = (page.rect.width, page.rect.height)
        
        # Check for text layer
        text = page.get_text().strip()
        
        if len(text) < 50:
            result['is_scanned'] = True
            result['has_text_layer'] = False
            doc.close()
            return result
        
        result['has_text_layer'] = True
        
        # Check for multi-column layout
        words = page.get_text("words")
        
        if len(words) > 20:
            page_width = page.rect.width
            mid_x = page_width / 2
            
            # Count words in left vs right half
            left_count = sum(1 for w in words if w[0] < mid_x)
            right_count = sum(1 for w in words if w[0] >= mid_x)
            
            # If both halves have substantial content, likely 2-column
            if left_count > 10 and right_count > 10:
                ratio = min(left_count, right_count) / max(left_count, right_count)
                if ratio > 0.3:  # At least 30% balance
                    result['is_multi_column'] = True
                    result['estimated_columns'] = 2
                    result['confidence'] = 0.7
        
        doc.close()
        
    except Exception as e:
        result['error'] = str(e)
    
    return result


def should_use_ocr(file_path: str) -> bool:
    """
    Determine if OCR should be used for this file.
    
    Args:
        file_path: Path to file
        
    Returns:
        True if OCR recommended
    """
    file_type = detect_file_type(file_path)
    
    # Always use OCR for images
    if file_type == 'image':
        return True
    
    # Check if PDF is scanned
    if file_type == 'pdf':
        chars = analyze_pdf_characteristics(file_path)
        return chars.get('is_scanned', False)
    
    # DOCX files don't need OCR
    return False


def get_recommended_strategy(file_path: str) -> str:
    """
    Get recommended parsing strategy based on file analysis.
    
    Args:
        file_path: Path to file
        
    Returns:
        Strategy name: 'pdf', 'ocr', 'docx', 'region', or 'unknown'
    """
    file_type = detect_file_type(file_path)
    
    if file_type == 'unknown':
        return 'unknown'
    
    if file_type == 'docx':
        return 'docx'
    
    if file_type == 'image':
        return 'ocr'
    
    if file_type == 'pdf':
        chars = analyze_pdf_characteristics(file_path)
        
        # Scanned PDFs need OCR
        if chars.get('is_scanned', False):
            return 'ocr'
        
        # Multi-column PDFs need region-based parsing
        if chars.get('is_multi_column', False):
            return 'region'
        
        # Simple PDFs use standard pipeline
        return 'pdf'
    
    return 'unknown'
