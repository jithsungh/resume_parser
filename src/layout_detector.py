"""
Simple Layout Detector for Resume Routing
Determines which pipeline to use based on PDF characteristics.
"""

import fitz  # PyMuPDF
from typing import Dict, Any, Tuple
from pathlib import Path


def detect_resume_layout(pdf_path: str) -> Dict[str, Any]:
    """
    Analyze PDF layout to determine best parsing pipeline.
    
    Returns:
        Dictionary with:
        - recommended_pipeline: 'pdf' or 'ocr'
        - is_scanned: bool
        - num_columns: int (estimated)
        - num_pages: int
        - has_text_layer: bool
        - confidence: float (0-1)
        - reasons: list of strings explaining the recommendation
    """
    
    result = {
        'recommended_pipeline': 'pdf',
        'is_scanned': False,
        'num_columns': 1,
        'num_pages': 0,
        'has_text_layer': True,
        'confidence': 0.5,
        'reasons': []
    }
    
    try:
        doc = fitz.open(pdf_path)
        result['num_pages'] = len(doc)
        
        if len(doc) == 0:
            result['recommended_pipeline'] = 'ocr'
            result['reasons'].append("Empty PDF")
            result['confidence'] = 1.0
            doc.close()
            return result
        
        # Analyze first page (representative)
        page = doc[0]
        
        # Check for text layer
        text = page.get_text()
        word_count = len(text.split())
        
        if word_count < 10:
            result['is_scanned'] = True
            result['has_text_layer'] = False
            result['recommended_pipeline'] = 'ocr'
            result['reasons'].append(f"Very few words extracted ({word_count}), likely scanned")
            result['confidence'] = 0.9
            doc.close()
            return result
        
        # Check text quality (detect garbled text from images)
        words = text.split()[:50]  # First 50 words
        alpha_ratio = sum(1 for w in words if any(c.isalpha() for c in w)) / max(1, len(words))
        
        if alpha_ratio < 0.5:
            result['is_scanned'] = True
            result['has_text_layer'] = False
            result['recommended_pipeline'] = 'ocr'
            result['reasons'].append(f"Low alpha ratio ({alpha_ratio:.2f}), garbled text")
            result['confidence'] = 0.85
            doc.close()
            return result
        
        # Get text blocks to estimate columns
        blocks = page.get_text("dict")["blocks"]
        text_blocks = [b for b in blocks if b.get("type") == 0]  # text blocks
        
        if not text_blocks:
            result['is_scanned'] = True
            result['has_text_layer'] = False
            result['recommended_pipeline'] = 'ocr'
            result['reasons'].append("No text blocks found")
            result['confidence'] = 0.95
            doc.close()
            return result
        
        # Estimate number of columns by x-position clustering
        page_width = page.rect.width
        x_positions = []
        
        for block in text_blocks:
            bbox = block.get("bbox", [0, 0, 0, 0])
            x_center = (bbox[0] + bbox[2]) / 2
            x_positions.append(x_center)
        
        # Simple column detection: check if positions cluster
        if x_positions:
            x_positions.sort()
            gaps = []
            for i in range(len(x_positions) - 1):
                gap = x_positions[i+1] - x_positions[i]
                if gap > page_width * 0.15:  # significant gap
                    gaps.append(gap)
            
            estimated_columns = len(gaps) + 1
            result['num_columns'] = min(estimated_columns, 3)  # cap at 3
        
        # Decision logic
        if result['num_columns'] >= 2:
            result['recommended_pipeline'] = 'ocr'
            result['reasons'].append(f"Multi-column layout detected ({result['num_columns']} columns)")
            result['confidence'] = 0.75
        else:
            result['recommended_pipeline'] = 'pdf'
            result['reasons'].append("Single column layout, good text layer")
            result['confidence'] = 0.85
        
        doc.close()
        
    except Exception as e:
        result['recommended_pipeline'] = 'pdf'
        result['reasons'].append(f"Error during analysis: {str(e)}")
        result['confidence'] = 0.3
    
    return result


def should_use_ocr(pdf_path: str, threshold: float = 0.6) -> Tuple[bool, str]:
    """
    Simple yes/no: should we use OCR pipeline?
    
    Args:
        pdf_path: Path to PDF
        threshold: Confidence threshold for OCR recommendation
        
    Returns:
        (use_ocr, reason)
    """
    analysis = detect_resume_layout(pdf_path)
    
    use_ocr = (
        analysis['recommended_pipeline'] == 'ocr' and 
        analysis['confidence'] >= threshold
    )
    
    reason = "; ".join(analysis['reasons'])
    
    return use_ocr, reason


def print_layout_analysis(pdf_path: str):
    """
    Print detailed layout analysis for debugging.
    """
    analysis = detect_resume_layout(pdf_path)
    
    print("="*60)
    print(f"Layout Analysis: {Path(pdf_path).name}")
    print("="*60)
    print(f"Pages: {analysis['num_pages']}")
    print(f"Has text layer: {analysis['has_text_layer']}")
    print(f"Is scanned: {analysis['is_scanned']}")
    print(f"Estimated columns: {analysis['num_columns']}")
    print(f"\nRecommended pipeline: {analysis['recommended_pipeline'].upper()}")
    print(f"Confidence: {analysis['confidence']:.2%}")
    print(f"\nReasons:")
    for reason in analysis['reasons']:
        print(f"  - {reason}")
    print("="*60)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python layout_detector.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    print_layout_analysis(pdf_path)
    
    use_ocr, reason = should_use_ocr(pdf_path)
    print(f"\n➜ Use OCR: {use_ocr}")
    print(f"   Reason: {reason}")
