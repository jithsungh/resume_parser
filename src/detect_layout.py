"""
Layout Detector - Analyzes PDF structure to determine optimal parsing strategy.

This module detects:
- Number of columns
- Whether text is native or scanned
- Text density and quality
- Layout complexity

Based on analysis, recommends:
- PDF pipeline (for native, well-structured PDFs)
- OCR pipeline (for scanned/image-based PDFs)
"""

import fitz  # PyMuPDF
from typing import Dict, Any, List, Tuple
from pathlib import Path
import numpy as np



def detect_resume_layout(pdf_path: str, sample_pages: int = 2) -> Dict[str, Any]:
    """
    Analyze PDF layout to determine optimal parsing strategy.
    
    Args:
        pdf_path: Path to PDF file
        sample_pages: Number of pages to sample for analysis
        
    Returns:
        Dictionary with analysis results:
        {
            'recommended_pipeline': 'pdf' or 'ocr',
            'confidence': float (0-1),
            'num_columns': int,
            'is_scanned': bool,
            'text_density': float,
            'has_native_text': bool,
            'layout_complexity': 'simple', 'moderate', or 'complex',
            'reasons': List[str] - explanations for recommendation
        }
    """
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        pages_to_analyze = min(sample_pages, total_pages)
        
        analysis = {
            'total_pages': total_pages,
            'native_text_ratio': 0.0,
            'text_density': 0.0,
            'num_columns': 1,
            'column_variance': 0.0,
            'image_count': 0,
            'has_native_text': False,
            'is_scanned': False,
            'layout_complexity': 'simple',
            'reasons': []
        }
        
        native_text_chars = 0
        total_page_area = 0
        column_counts = []
        
        for page_num in range(pages_to_analyze):
            page = doc[page_num]
            page_rect = page.rect
            page_area = page_rect.width * page_rect.height
            total_page_area += page_area
            
            # Extract native text
            text = page.get_text()
            native_text_chars += len(text.strip())
            
            # Get text blocks to analyze columns
            blocks = page.get_text("dict")["blocks"]
            text_blocks = [b for b in blocks if b.get("type") == 0]  # Text blocks only
            
            # Detect columns by analyzing X-coordinates
            if text_blocks:
                x_coords = []
                for block in text_blocks:
                    bbox = block.get("bbox", [0, 0, 0, 0])
                    x_coords.append(bbox[0])  # Left edge
                
                if x_coords:
                    # Cluster X-coordinates to find columns
                    num_cols = _detect_columns_from_coords(x_coords, page_rect.width)
                    column_counts.append(num_cols)
            
            # Count images
            image_list = page.get_images()
            analysis['image_count'] += len(image_list)
        
        doc.close()
        
        # Calculate metrics
        analysis['has_native_text'] = native_text_chars > 100
        analysis['native_text_ratio'] = native_text_chars / max(1, total_page_area / 1000)
        analysis['text_density'] = native_text_chars / max(1, total_pages)
        
        # Determine column count (mode of detected columns)
        if column_counts:
            analysis['num_columns'] = int(np.median(column_counts))
            analysis['column_variance'] = np.std(column_counts) if len(column_counts) > 1 else 0
        
        # Determine if scanned
        # Scanned PDFs typically have very little native text and many images
        is_scanned = (
            (not analysis['has_native_text']) or 
            (analysis['native_text_ratio'] < 5.0 and analysis['image_count'] > 0)
        )
        analysis['is_scanned'] = is_scanned
        
        # Determine layout complexity
        if analysis['num_columns'] >= 3:
            analysis['layout_complexity'] = 'complex'
        elif analysis['num_columns'] == 2 or analysis['column_variance'] > 0.5:
            analysis['layout_complexity'] = 'moderate'
        else:
            analysis['layout_complexity'] = 'simple'
        
        # Recommend pipeline
        reasons = []
        
        if is_scanned:
            recommended = 'ocr'
            reasons.append("PDF appears to be scanned/image-based")
            confidence = 0.9
        elif not analysis['has_native_text']:
            recommended = 'ocr'
            reasons.append("No native text found")
            confidence = 0.95
        elif analysis['native_text_ratio'] < 10.0:
            recommended = 'ocr'
            reasons.append("Low text density suggests scanned content")
            confidence = 0.8
        else:
            recommended = 'pdf'
            reasons.append("Native text extraction available")
            confidence = 0.85
            
            if analysis['num_columns'] <= 2:
                reasons.append("Simple/moderate column layout")
                confidence += 0.05
            else:
                reasons.append("Complex multi-column layout detected")
                confidence -= 0.1
        
        analysis['recommended_pipeline'] = recommended
        analysis['confidence'] = min(1.0, max(0.0, confidence))
        analysis['reasons'] = reasons
        
        return analysis
        
    except Exception as e:
        # Fallback to PDF pipeline on error
        return {
            'recommended_pipeline': 'pdf',
            'confidence': 0.5,
            'num_columns': 1,
            'is_scanned': False,
            'has_native_text': True,
            'text_density': 0.0,
            'layout_complexity': 'simple',
            'reasons': [f"Analysis failed: {str(e)}. Defaulting to PDF pipeline."],
            'error': str(e)
        }


def _detect_columns_from_coords(x_coords: List[float], page_width: float, 
                                 cluster_threshold: float = 50.0) -> int:
    """
    Detect number of columns by clustering X-coordinates.
    
    Args:
        x_coords: List of X-coordinates (left edges of text blocks)
        page_width: Width of the page
        cluster_threshold: Distance threshold for clustering
        
    Returns:
        Estimated number of columns
    """
    if not x_coords:
        return 1
    
    # Sort coordinates
    sorted_x = sorted(x_coords)
    
    # Find clusters (groups of X-coords that are close together)
    clusters = []
    current_cluster = [sorted_x[0]]
    
    for x in sorted_x[1:]:
        if x - current_cluster[-1] <= cluster_threshold:
            current_cluster.append(x)
        else:
            # New cluster
            clusters.append(current_cluster)
            current_cluster = [x]
    
    if current_cluster:
        clusters.append(current_cluster)
    
    # Filter out small clusters (likely noise)
    significant_clusters = [c for c in clusters if len(c) >= 2]
    
    if not significant_clusters:
        return 1
    
    # Number of columns = number of significant clusters
    num_columns = len(significant_clusters)
    
    # Sanity check: most resumes have 1-3 columns
    return min(num_columns, 3)


def quick_check_is_scanned(pdf_path: str) -> bool:
    """
    Quick check if PDF is scanned (image-based).
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        True if likely scanned, False otherwise
    """
    try:
        doc = fitz.open(pdf_path)
        
        # Check first page only for speed
        if len(doc) == 0:
            doc.close()
            return False
        
        page = doc[0]
        
        # Get native text
        text = page.get_text().strip()
        
        # Get images
        images = page.get_images()
        
        doc.close()
        
        # Heuristic: if very little text and has images, likely scanned
        has_little_text = len(text) < 50
        has_images = len(images) > 0
        
        return has_little_text and has_images
        
    except Exception:
        return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python layout_detector.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    print(f"Analyzing: {pdf_path}")
    print("=" * 60)
    
    analysis = detect_resume_layout(pdf_path)
    
    print(f"\nRecommended Pipeline: {analysis['recommended_pipeline'].upper()}")
    print(f"Confidence: {analysis['confidence']:.1%}")
    print(f"\nLayout Analysis:")
    print(f"  Columns: {analysis['num_columns']}")
    print(f"  Complexity: {analysis['layout_complexity']}")
    print(f"  Scanned: {analysis['is_scanned']}")
    print(f"  Native Text: {analysis['has_native_text']}")
    print(f"  Text Density: {analysis['text_density']:.1f}")
    
    print(f"\nReasons:")
    for reason in analysis['reasons']:
        print(f"  - {reason}")
