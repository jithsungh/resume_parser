"""
Robust OCR-First Resume Parser Pipeline
Simplified approach: Use OCR on full-page images for maximum compatibility.
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple
from pathlib import Path
import re

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    import easyocr
    HAS_EASYOCR = True
except ImportError:
    HAS_EASYOCR = False

from src.PDF_pipeline.segment_sections import (
    guess_section_name,
    clean_for_heading,
    uppercase_ratio,
    simple_json,
)


def pdf_page_to_image(pdf_path: str, page_num: int, dpi: int = 300) -> np.ndarray:
    """Convert PDF page to image."""
    if not HAS_PYMUPDF:
        raise ImportError("PyMuPDF required")
    
    doc = fitz.open(str(pdf_path))
    page = doc[page_num]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    
    # Convert to numpy array
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    
    # Convert to RGB
    if pix.n == 4:  # RGBA
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
    elif pix.n == 1:  # Grayscale
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    
    doc.close()
    return img


def extract_text_ocr(img: np.ndarray, reader, min_confidence: float = 0.2) -> List[Dict[str, Any]]:
    """Extract text from image using EasyOCR."""
    if not HAS_EASYOCR:
        raise ImportError("EasyOCR required")
    
    try:
        results = reader.readtext(img, paragraph=False)
    except Exception as e:
        print(f"OCR error: {e}")
        return []
    
    lines = []
    for bbox, text, confidence in results:
        if confidence < min_confidence:
            continue
        
        text = text.strip()
        if not text:
            continue
        
        # Extract coordinates
        xs = [pt[0] for pt in bbox]
        ys = [pt[1] for pt in bbox]
        
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        
        lines.append({
            'text': text,
            'x0': float(x0),
            'y0': float(y0),
            'x1': float(x1),
            'y1': float(y1),
            'height': float(y1 - y0),
            'width': float(x1 - x0),
            'confidence': float(confidence),
        })
    
    # Sort by reading order
    lines.sort(key=lambda l: (l['y0'], l['x0']))
    return lines


def is_likely_heading(text: str, line_idx: int, total_lines: int, 
                     height: float, avg_height: float,
                     space_above: float, avg_spacing: float) -> Tuple[bool, float]:
    """
    Determine if a line is likely a heading.
    Returns (is_heading, score).
    """
    if not text:
        return False, 0.0
    
    score = 0.0
    
    # 1. Keyword match (strongest signal)
    cleaned = clean_for_heading(text)
    has_keyword = guess_section_name(cleaned) is not None
    if has_keyword:
        score += 0.4
    
    # 2. Short length
    word_count = len(text.split())
    char_count = len(text)
    if word_count <= 8 and char_count <= 60:
        score += 0.15
    
    # 3. Capitalization
    upper_ratio = uppercase_ratio(text)
    words = text.split()
    title_case_ratio = sum(1 for w in words if w and w[0].isupper()) / max(1, len(words))
    
    if upper_ratio > 0.7:
        score += 0.2
    elif title_case_ratio > 0.8:
        score += 0.15
    
    # 4. Trailing colon
    if text.strip().endswith(':'):
        score += 0.1
    
    # 5. Larger font
    if height > 1.15 * avg_height:
        score += 0.1
    
    # 6. Extra spacing above
    if space_above > 1.3 * avg_spacing:
        score += 0.15
    
    # 7. Position bonus (early in document)
    if line_idx < min(5, total_lines * 0.1):
        score += 0.05
    
    # Threshold
    is_heading = score >= 0.25  # Lowered for better recall
    
    return is_heading, score


def detect_headings(lines: List[Dict[str, Any]], verbose: bool = False) -> List[Dict[str, Any]]:
    """Detect headings in extracted text lines."""
    if not lines:
        return []
    
    # Calculate statistics
    heights = [l['height'] for l in lines]
    avg_height = np.mean(heights) if heights else 10.0
    
    spacings = []
    for i in range(len(lines) - 1):
        space = lines[i+1]['y0'] - lines[i]['y1']
        spacings.append(max(0, space))
    avg_spacing = np.mean(spacings) if spacings else 5.0
    
    # Detect headings
    headings = []
    for i, line in enumerate(lines):
        text = line['text']
        height = line.get('height', 10)
        
        # Calculate space above
        if i > 0:
            space_above = line['y0'] - lines[i-1]['y1']
        else:
            space_above = 0
        
        is_heading, score = is_likely_heading(
            text, i, len(lines),
            height, avg_height,
            space_above, avg_spacing
        )
        
        if is_heading:
            canon = guess_section_name(clean_for_heading(text))
            headings.append({
                'line_index': i,
                'text': text,
                'canon': canon or 'Unknown',
                'score': score,
            })
            
            if verbose:
                print(f"  Heading: '{text[:60]}' → {canon or 'Unknown'} (score: {score:.2f})")
    
    return headings


def split_into_sections(lines: List[Dict[str, Any]], headings: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Split lines into sections based on headings."""
    if not headings:
        return {'Unknown': lines}
    
    sections = {}
    heading_indices = {h['line_index'] for h in headings}
    
    # Start with first heading
    current_section = headings[0]['canon']
    current_lines = []
    
    for i, line in enumerate(lines):
        if i in heading_indices:
            # Save previous section
            if current_lines:
                if current_section not in sections:
                    sections[current_section] = []
                sections[current_section].extend(current_lines)
            
            # Start new section (skip heading line itself)
            current_section = next(h['canon'] for h in headings if h['line_index'] == i)
            current_lines = []
        else:
            current_lines.append(line)
    
    # Save last section
    if current_lines:
        if current_section not in sections:
            sections[current_section] = []
        sections[current_section].extend(current_lines)
    
    return sections


def robust_pipeline_ocr(path: str, use_gpu: bool = False, dpi: int = 300, 
                       verbose: bool = True, min_confidence: float = 0.2) -> Tuple[Dict[str, Any], str]:
    """
    OCR-first robust pipeline for maximum compatibility.
    
    Args:
        path: Path to PDF file
        use_gpu: Use GPU for OCR
        dpi: Resolution for PDF rendering
        verbose: Print progress
        min_confidence: Minimum OCR confidence threshold
        
    Returns:
        (result_dict, simplified_json)
    """
    if verbose:
        print(f"[Robust OCR Pipeline] Processing: {path}")
    
    path_obj = Path(path)
    
    # Initialize OCR
    if not HAS_EASYOCR:
        raise ImportError("EasyOCR is required. Install with: pip install easyocr")
    
    if verbose:
        print("[Robust OCR Pipeline] Initializing EasyOCR...")
    reader = easyocr.Reader(['en'], gpu=use_gpu)
    
    # Get number of pages
    if path_obj.suffix.lower() == '.pdf':
        if not HAS_PYMUPDF:
            raise ImportError("PyMuPDF required for PDFs")
        doc = fitz.open(str(path))
        num_pages = len(doc)
        doc.close()
    else:
        num_pages = 1
    
    all_sections = {}
    total_lines_extracted = 0
    
    # Process each page
    for page_num in range(num_pages):
        if verbose:
            print(f"[Robust OCR Pipeline] Processing page {page_num + 1}/{num_pages}")
        
        # Convert to image
        if path_obj.suffix.lower() == '.pdf':
            img = pdf_page_to_image(path, page_num, dpi)
        else:
            img = cv2.imread(str(path))
            if img is not None:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        if img is None:
            if verbose:
                print(f"[Robust OCR Pipeline] Warning: Could not load page {page_num + 1}")
            continue
        
        # Extract text with OCR
        lines = extract_text_ocr(img, reader, min_confidence)
        
        if not lines:
            if verbose:
                print(f"[Robust OCR Pipeline] Warning: No text found on page {page_num + 1}")
            continue
        
        if verbose:
            print(f"[Robust OCR Pipeline] Extracted {len(lines)} lines")
        
        total_lines_extracted += len(lines)
        
        # Detect headings
        headings = detect_headings(lines, verbose)
        
        if verbose:
            print(f"[Robust OCR Pipeline] Found {len(headings)} headings")
        
        # Split into sections
        page_sections = split_into_sections(lines, headings)
        
        # Merge with global sections
        for section_name, section_lines in page_sections.items():
            if section_name not in all_sections:
                all_sections[section_name] = []
            all_sections[section_name].extend(section_lines)
    
    # Format output
    sections_list = []
    for section_name, lines in all_sections.items():
        sections_list.append({
            'section': section_name,
            'lines': [{'text': l['text']} for l in lines],
            'line_count': len(lines),
        })
    
    result = {
        'meta': {
            'pages': num_pages,
            'sections': len(sections_list),
            'total_lines': sum(s['line_count'] for s in sections_list),
        },
        'sections': sections_list,
        'contact': {},
    }
    
    # Generate simplified JSON
    sim = simple_json(result)
    
    if verbose:
        print(f"[Robust OCR Pipeline] Complete: {len(sections_list)} sections, {total_lines_extracted} lines extracted")
    
    return result, sim


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Robust OCR-first resume parsing")
    parser.add_argument("--pdf", required=True, help="Path to PDF")
    parser.add_argument("--dpi", type=int, default=300, help="DPI for rendering")
    parser.add_argument("--gpu", action="store_true", help="Use GPU for OCR")
    parser.add_argument("--confidence", type=float, default=0.2, help="Min OCR confidence")
    parser.add_argument("--quiet", action="store_true", help="Suppress output")
    parser.add_argument("--save", help="Save simplified JSON")
    
    args = parser.parse_args()
    
    result, simplified = robust_pipeline_ocr(
        args.pdf,
        use_gpu=args.gpu,
        dpi=args.dpi,
        verbose=not args.quiet,
        min_confidence=args.confidence,
    )
    
    print("\n" + "="*60)
    print("SIMPLIFIED OUTPUT")
    print("="*60)
    print(simplified)
    
    if args.save:
        with open(args.save, 'w', encoding='utf-8') as f:
            f.write(simplified)
        print(f"\nSaved to: {args.save}")
