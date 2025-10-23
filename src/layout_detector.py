"""
Layout Detector - Analyze PDF structure to recommend the best parsing pipeline.

This module analyzes PDF characteristics to determine:
1. Is it native PDF with extractable text or scanned/image-based?
2. Single column or multi-column layout?
3. Text density and complexity
4. Recommended pipeline (PDF or OCR)
"""

import fitz  # PyMuPDF
from typing import Dict, Any
from pathlib import Path


def detect_resume_layout(pdf_path: str) -> Dict[str, Any]:
    """
    Analyze PDF layout characteristics to recommend parsing pipeline.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Dictionary with:
        - recommended_pipeline: 'pdf' or 'ocr'
        - confidence: float (0-1)
        - is_scanned: bool
        - num_columns: int (1, 2, or 3+)
        - layout_complexity: 'simple', 'moderate', or 'complex'
        - text_extractable: bool
        - total_chars: int
        - page_count: int
        - analysis_details: dict with metrics
    """
    
    try:
        doc = fitz.open(pdf_path)
        
        # Initialize metrics
        total_chars = 0
        total_words = 0
        total_images = 0
        has_extractable_text = False
        
        # Analyze first page (usually sufficient for layout detection)
        page = doc[0]
        text = page.get_text()
        total_chars = len(text.strip())
        total_words = len(text.split())
        
        # Check for images
        image_list = page.get_images()
        total_images = len(image_list)
        
        # Detect if text is extractable
        has_extractable_text = total_chars > 50
        
        # Detect columns by analyzing text blocks
        blocks = page.get_text("blocks")
        num_columns = _detect_columns(blocks, page.rect.width)
        
        # Determine if scanned
        is_scanned = _is_scanned_pdf(total_chars, total_images, page)
        
        # Calculate layout complexity
        layout_complexity = _calculate_complexity(num_columns, len(blocks), total_images)
        
        # Recommend pipeline
        if is_scanned:
            recommended_pipeline = 'ocr'
            confidence = 0.9
        elif not has_extractable_text:
            recommended_pipeline = 'ocr'
            confidence = 0.95
        else:
            recommended_pipeline = 'pdf'
            confidence = 0.85 if num_columns <= 2 else 0.7
        
        doc.close()
        
        return {
            'recommended_pipeline': recommended_pipeline,
            'confidence': confidence,
            'is_scanned': is_scanned,
            'num_columns': num_columns,
            'layout_complexity': layout_complexity,
            'text_extractable': has_extractable_text,
            'total_chars': total_chars,
            'total_words': total_words,
            'page_count': len(doc),
            'total_images': total_images,
            'file_name': Path(pdf_path).name,
            'analysis_details': {
                'blocks_count': len(blocks),
                'avg_chars_per_block': total_chars / len(blocks) if blocks else 0,
                'image_to_text_ratio': total_images / max(1, total_words / 100)
            }
        }
        
    except Exception as e:
        # Fallback to PDF pipeline on error
        return {
            'recommended_pipeline': 'pdf',
            'confidence': 0.5,
            'is_scanned': False,
            'num_columns': 1,
            'layout_complexity': 'unknown',
            'text_extractable': True,
            'total_chars': 0,
            'total_words': 0,
            'page_count': 1,
            'total_images': 0,
            'file_name': Path(pdf_path).name,
            'error': str(e),
            'analysis_details': {}
        }


def _detect_columns(blocks: list, page_width: float) -> int:
    """
    Detect number of columns based on text block positions.
    
    Args:
        blocks: List of text blocks from PyMuPDF
        page_width: Width of the page
        
    Returns:
        Number of columns (1, 2, or 3)
    """
    if not blocks:
        return 1
    
    # Get x-coordinates of block centers
    x_positions = []
    for block in blocks:
        if len(block) >= 4:  # block is (x0, y0, x1, y1, text, ...)
            x0, y0, x1, y1 = block[:4]
            center_x = (x0 + x1) / 2
            x_positions.append(center_x)
    
    if not x_positions:
        return 1
    
    # Divide page into thirds
    left_third = page_width / 3
    right_third = 2 * page_width / 3
    
    # Count blocks in each region
    left_blocks = sum(1 for x in x_positions if x < left_third)
    middle_blocks = sum(1 for x in x_positions if left_third <= x < right_third)
    right_blocks = sum(1 for x in x_positions if x >= right_third)
    
    # Determine columns
    active_regions = sum([
        left_blocks > 2,
        middle_blocks > 2,
        right_blocks > 2
    ])
    
    if active_regions >= 3:
        return 3
    elif active_regions == 2:
        return 2
    else:
        return 1


def _is_scanned_pdf(total_chars: int, total_images: int, page) -> bool:
    """
    Determine if PDF is scanned/image-based.
    
    Args:
        total_chars: Number of extractable characters
        total_images: Number of images on page
        page: PyMuPDF page object
        
    Returns:
        True if likely scanned, False otherwise
    """
    # Very few extractable characters suggests scanned
    if total_chars < 50:
        return True
    
    # High image-to-text ratio suggests scanned
    if total_images > 0 and total_chars < 200:
        return True
    
    # Check if page is mostly images
    try:
        drawings = page.get_drawings()
        if len(drawings) > 50 and total_chars < 500:
            return True
    except:
        pass
    
    return False


def _calculate_complexity(num_columns: int, num_blocks: int, num_images: int) -> str:
    """
    Calculate layout complexity score.
    
    Args:
        num_columns: Number of detected columns
        num_blocks: Number of text blocks
        num_images: Number of images
        
    Returns:
        'simple', 'moderate', or 'complex'
    """
    complexity_score = 0
    
    # Column complexity
    if num_columns == 1:
        complexity_score += 0
    elif num_columns == 2:
        complexity_score += 2
    else:
        complexity_score += 4
    
    # Block complexity
    if num_blocks < 10:
        complexity_score += 0
    elif num_blocks < 30:
        complexity_score += 1
    else:
        complexity_score += 2
    
    # Image complexity
    if num_images == 0:
        complexity_score += 0
    elif num_images < 3:
        complexity_score += 1
    else:
        complexity_score += 2
    
    # Classify
    if complexity_score <= 2:
        return 'simple'
    elif complexity_score <= 5:
        return 'moderate'
    else:
        return 'complex'


def print_layout_analysis(analysis: Dict[str, Any]):
    """Pretty print layout analysis results."""
    print("\n" + "="*60)
    print("PDF Layout Analysis")
    print("="*60)
    print(f"File: {analysis['file_name']}")
    print(f"Recommended Pipeline: {analysis['recommended_pipeline'].upper()}")
    print(f"Confidence: {analysis['confidence']:.1%}")
    print(f"\nLayout Characteristics:")
    print(f"  Columns: {analysis['num_columns']}")
    print(f"  Complexity: {analysis['layout_complexity']}")
    print(f"  Scanned: {'Yes' if analysis['is_scanned'] else 'No'}")
    print(f"  Text Extractable: {'Yes' if analysis['text_extractable'] else 'No'}")
    print(f"\nMetrics:")
    print(f"  Pages: {analysis['page_count']}")
    print(f"  Characters: {analysis['total_chars']:,}")
    print(f"  Words: {analysis['total_words']:,}")
    print(f"  Images: {analysis['total_images']}")
    
    if 'analysis_details' in analysis:
        details = analysis['analysis_details']
        print(f"\nDetails:")
        print(f"  Text Blocks: {details.get('blocks_count', 0)}")
        print(f"  Avg Chars/Block: {details.get('avg_chars_per_block', 0):.1f}")
        print(f"  Image/Text Ratio: {details.get('image_to_text_ratio', 0):.2f}")
    
    if 'error' in analysis:
        print(f"\n⚠️  Warning: {analysis['error']}")
    
    print("="*60 + "\n")


# CLI for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python layout_detector.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    analysis = detect_resume_layout(pdf_path)
    print_layout_analysis(analysis)
