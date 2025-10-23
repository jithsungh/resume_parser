"""
Robust Resume Parser Pipeline
Layout-aware, recursive, hybrid approach for complex resume layouts.

Key Features:
- Block-level detection (horizontal bands + vertical columns)
- Recursive splitting for hybrid layouts
- Dynamic threshold adjustment
- Context-aware heading detection
- Multi-column support with global coordinate tracking
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
import re
from collections import defaultdict

# Optional imports
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

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

from src.PDF_pipeline.segment_sections import (
    SECTION_MAP,
    guess_section_name,
    clean_for_heading,
    uppercase_ratio,
    simple_json,
)


def load_and_preprocess(path: str, page_num: int = 0, dpi: int = 300) -> np.ndarray:
    """
    Load PDF/image and convert to binary (black & white) for processing.
    
    Args:
        path: Path to PDF or image file
        page_num: Page number (for PDFs)
        dpi: Resolution for PDF rendering
        
    Returns:
        Binary image (numpy array)
    """
    path_obj = Path(path)
    
    if path_obj.suffix.lower() == '.pdf':
        if not HAS_PYMUPDF:
            raise ImportError("PyMuPDF (fitz) required for PDF processing")
        
        doc = fitz.open(str(path))
        page = doc[page_num]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        
        if pix.n == 4:  # RGBA
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        elif pix.n == 3:  # RGB
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            
        doc.close()
    else:
        img = cv2.imread(str(path))
        
    if img is None:
        raise ValueError(f"Could not load image from {path}")
    
    # Convert to grayscale
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    
    # Adaptive thresholding for better text extraction
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    return binary


def remove_lines(img: np.ndarray, min_line_length: int = 50) -> np.ndarray:
    """
    Remove horizontal and vertical lines (table borders, separators).
    
    Args:
        img: Binary image
        min_line_length: Minimum line length to remove
        
    Returns:
        Image with lines removed
    """
    result = img.copy()
    
    # Remove horizontal lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (min_line_length, 1))
    detect_horizontal = cv2.morphologyEx(result, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
    cnts = cv2.findContours(detect_horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]
    for c in cnts:
        cv2.drawContours(result, [c], -1, 255, -1)
    
    # Remove vertical lines
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, min_line_length))
    detect_vertical = cv2.morphologyEx(result, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
    cnts = cv2.findContours(detect_vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]
    for c in cnts:
        cv2.drawContours(result, [c], -1, 255, -1)
    
    return result


def detect_text_blocks(img: np.ndarray, min_area: int = 100) -> List[Dict[str, Any]]:
    """
    Detect text blocks using contour detection.
    
    Args:
        img: Binary image
        min_area: Minimum area for valid text block
        
    Returns:
        List of text blocks with bounding boxes
    """
    # Invert for contour detection (text should be white on black)
    inverted = cv2.bitwise_not(img)
    
    # Dilate to connect nearby text
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 5))
    dilated = cv2.dilate(inverted, kernel, iterations=2)
    
    # Find contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    blocks = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        
        if area < min_area:
            continue
            
        blocks.append({
            'x': x,
            'y': y,
            'width': w,
            'height': h,
            'area': area,
            'center_x': x + w / 2,
            'center_y': y + h / 2,
        })
    
    return blocks


def cluster_blocks_into_columns(blocks: List[Dict[str, Any]], img_width: int, 
                                 tolerance: float = 0.05) -> List[List[Dict[str, Any]]]:
    """
    Cluster blocks by x-coordinate to detect columns.
    
    Args:
        blocks: List of text blocks
        img_width: Image width for tolerance calculation
        tolerance: Clustering tolerance as fraction of image width
        
    Returns:
        List of column groups (each group is a list of blocks)
    """
    if not blocks:
        return []
    
    # Sort by x-coordinate
    sorted_blocks = sorted(blocks, key=lambda b: b['x'])
    
    columns = []
    current_column = [sorted_blocks[0]]
    threshold = img_width * tolerance
    
    for block in sorted_blocks[1:]:
        # Check if block belongs to current column
        prev_block = current_column[-1]
        
        # Use center_x for better column detection
        if abs(block['center_x'] - prev_block['center_x']) < threshold:
            current_column.append(block)
        else:
            columns.append(current_column)
            current_column = [block]
    
    if current_column:
        columns.append(current_column)
    
    return columns


def cluster_blocks_into_bands(blocks: List[Dict[str, Any]], img_height: int,
                               tolerance: float = 0.02) -> List[List[Dict[str, Any]]]:
    """
    Cluster blocks by y-coordinate to detect horizontal bands.
    
    Args:
        blocks: List of text blocks
        img_height: Image height for tolerance calculation
        tolerance: Clustering tolerance as fraction of image height
        
    Returns:
        List of band groups (each group is a list of blocks)
    """
    if not blocks:
        return []
    
    # Sort by y-coordinate
    sorted_blocks = sorted(blocks, key=lambda b: b['y'])
    
    bands = []
    current_band = [sorted_blocks[0]]
    threshold = img_height * tolerance
    
    for block in sorted_blocks[1:]:
        prev_block = current_band[-1]
        
        # Check if block belongs to current band
        if abs(block['y'] - prev_block['y']) < threshold:
            current_band.append(block)
        else:
            bands.append(current_band)
            current_band = [block]
    
    if current_band:
        bands.append(current_band)
    
    return bands


def analyze_block_layout(blocks: List[Dict[str, Any]], img_width: int, 
                         img_height: int) -> Dict[str, Any]:
    """
    Analyze if a block is primarily horizontal, vertical, or mixed layout.
    
    Args:
        blocks: List of text blocks
        img_width: Image width
        img_height: Image height
        
    Returns:
        Layout analysis dictionary
    """
    if not blocks:
        return {'type': 'empty', 'columns': 0, 'bands': 0}
    
    # Detect columns and bands
    columns = cluster_blocks_into_columns(blocks, img_width)
    bands = cluster_blocks_into_bands(blocks, img_height)
    
    num_cols = len(columns)
    num_bands = len(bands)
    
    # Determine layout type
    if num_cols == 1 and num_bands >= 3:
        layout_type = 'vertical'
    elif num_cols >= 2 and num_bands <= 2:
        layout_type = 'horizontal'
    elif num_cols >= 2 and num_bands >= 3:
        layout_type = 'hybrid'
    else:
        layout_type = 'simple'
    
    return {
        'type': layout_type,
        'columns': num_cols,
        'bands': num_bands,
        'column_groups': columns,
        'band_groups': bands,
    }


def recursive_block_split(img: np.ndarray, x: int, y: int, width: int, height: int,
                          depth: int = 0, max_depth: int = 3) -> List[Dict[str, Any]]:
    """
    Recursively split image blocks until each is simple (horizontal or vertical).
    
    Args:
        img: Binary image
        x, y, width, height: Current block boundaries
        depth: Current recursion depth
        max_depth: Maximum recursion depth
        
    Returns:
        List of simple blocks with their properties
    """
    if depth >= max_depth or width < 50 or height < 50:
        return [{
            'x': x, 'y': y, 'width': width, 'height': height,
            'img': img[y:y+height, x:x+width]
        }]
    
    # Extract block
    block_img = img[y:y+height, x:x+width]
    
    # Detect text blocks in this region
    blocks = detect_text_blocks(block_img, min_area=50)
    
    if not blocks:
        return [{
            'x': x, 'y': y, 'width': width, 'height': height,
            'img': block_img
        }]
    
    # Analyze layout
    layout = analyze_block_layout(blocks, width, height)
    
    # If simple or vertical, return as-is
    if layout['type'] in ['simple', 'vertical', 'empty']:
        return [{
            'x': x, 'y': y, 'width': width, 'height': height,
            'img': block_img, 'layout': layout
        }]
    
    # If horizontal or hybrid, split into columns
    if layout['type'] in ['horizontal', 'hybrid'] and layout['columns'] >= 2:
        results = []
        for col_blocks in layout['column_groups']:
            # Find column boundaries
            col_x = min(b['x'] for b in col_blocks)
            col_y = min(b['y'] for b in col_blocks)
            col_x2 = max(b['x'] + b['width'] for b in col_blocks)
            col_y2 = max(b['y'] + b['height'] for b in col_blocks)
            
            col_width = col_x2 - col_x
            col_height = col_y2 - col_y
            
            # Recursively process column
            sub_blocks = recursive_block_split(
                img, x + col_x, y + col_y, col_width, col_height, 
                depth + 1, max_depth
            )
            results.extend(sub_blocks)
        
        return results
    
    # Default: return as single block
    return [{
        'x': x, 'y': y, 'width': width, 'height': height,
        'img': block_img, 'layout': layout
    }]


def detect_columns(lines: List[Dict[str, Any]], page_width: float) -> List[List[Dict[str, Any]]]:
    """
    Detect columns in a page by clustering lines based on their x-coordinates.
    
    Args:
        lines: List of text lines with coordinates
        page_width: Width of the page
        
    Returns:
        List of columns, each containing lines in that column
    """
    if not lines:
        return []
    
    # Calculate center x-coordinate for each line
    for line in lines:
        line['center_x'] = (line['x0'] + line['x1']) / 2
    
    # Use k-means-like clustering to detect columns
    # Start by checking if there are distinct x-coordinate groups
    center_xs = sorted([line['center_x'] for line in lines])
    
    # Check for gaps in x-coordinates that indicate column boundaries
    gaps = []
    for i in range(len(center_xs) - 1):
        gap = center_xs[i + 1] - center_xs[i]
        if gap > page_width * 0.05:  # Gap > 5% of page width
            gaps.append((gap, (center_xs[i] + center_xs[i + 1]) / 2))
    
    if not gaps:
        # Single column - return all lines
        return [lines]
    
    # Find the largest gap (most likely column boundary)
    gaps.sort(reverse=True)
    column_boundaries = [gap[1] for gap in gaps[:2]]  # Take up to 2 largest gaps (max 3 columns)
    column_boundaries.sort()
    
    # Assign lines to columns
    columns = [[] for _ in range(len(column_boundaries) + 1)]
    
    for line in lines:
        center_x = line['center_x']
        
        # Find which column this line belongs to
        col_idx = 0
        for boundary in column_boundaries:
            if center_x < boundary:
                break
            col_idx += 1
        
        columns[col_idx].append(line)
    
    # Filter out empty columns
    columns = [col for col in columns if col]
    
    return columns


def extract_text_from_pdf_page(pdf_path: str, page_num: int) -> List[Dict[str, Any]]:
    """
    Extract text from PDF using PyMuPDF (native text extraction) with column detection.
    
    Args:
        pdf_path: Path to PDF file
        page_num: Page number (0-indexed)
        
    Returns:
        List of text lines with coordinates
    """
    if not HAS_PYMUPDF:
        return []
    
    try:
        doc = fitz.open(str(pdf_path))
        page = doc[page_num]
        page_width = page.rect.width
        page_height = page.rect.height
        
        # Extract text with coordinates - use "blocks" instead of "dict" for better grouping
        blocks = page.get_text("dict")["blocks"]
        
        lines = []
        for block in blocks:
            if block.get("type") != 0:  # Skip non-text blocks
                continue
            
            for line in block.get("lines", []):
                text_parts = []
                for span in line.get("spans", []):
                    text_parts.append(span.get("text", ""))
                
                text = "".join(text_parts).strip()  # Changed from " ".join to "".join to avoid extra spaces
                if not text:
                    continue
                
                bbox = line.get("bbox", [0, 0, 0, 0])
                x0, y0, x1, y1 = bbox
                
                lines.append({
                    'text': text,
                    'x0': float(x0),
                    'y0': float(y0),
                    'x1': float(x1),
                    'y1': float(y1),
                    'height': float(y1 - y0),
                    'confidence': 1.0,  # Native text has high confidence
                })
        
        doc.close()
        
        if not lines:
            return []
        
        # Detect columns by clustering x-coordinates
        columns = detect_columns(lines, page_width)
        
        # Sort lines within each column, then concatenate columns left-to-right
        sorted_lines = []
        for column in columns:
            # Sort by y-coordinate within column
            column.sort(key=lambda l: l['y0'])
            sorted_lines.extend(column)
        
        # Merge lines that are on the same horizontal level (same y-coordinate within tolerance)
        merged_lines = []
        if lines:
            current_line = lines[0].copy()
            
            for i in range(1, len(lines)):
                next_line = lines[i]
                
                # Check if lines are on the same horizontal level (within 2 pixels)
                if abs(next_line['y0'] - current_line['y0']) < 2:
                    # Same line - merge text
                    # Add space if there's a gap between words
                    gap = next_line['x0'] - current_line['x1']
                    if gap > 5:  # Significant gap - add space
                        current_line['text'] += ' ' + next_line['text']
                    else:  # Small gap - just concatenate
                        current_line['text'] += next_line['text']
                    
                    # Update bounding box
                    current_line['x1'] = max(current_line['x1'], next_line['x1'])
                    current_line['y1'] = max(current_line['y1'], next_line['y1'])
                else:
                    # Different line - save current and start new
                    merged_lines.append(current_line)
                    current_line = next_line.copy()
            
            # Don't forget the last line
            merged_lines.append(current_line)
        
        return merged_lines
    except Exception as e:
        print(f"Warning: PyMuPDF text extraction failed: {e}")
        return []


def extract_text_from_docx(docx_path: str) -> List[Dict[str, Any]]:
    """
    Extract text from DOCX file using python-docx.
    
    Args:
        docx_path: Path to DOCX file
        
    Returns:
        List of text lines with simulated coordinates
    """
    if not HAS_DOCX:
        return []
    
    try:
        doc = Document(str(docx_path))
        
        lines = []
        y_position = 0.0
        line_height = 12.0  # Simulated line height
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                y_position += line_height * 0.5  # Small gap for empty lines
                continue
            
            # Simulated coordinates (DOCX doesn't have actual coordinates)
            lines.append({
                'text': text,
                'x0': 0.0,
                'y0': y_position,
                'x1': 600.0,  # Simulated page width
                'y1': y_position + line_height,
                'height': line_height,
                'confidence': 1.0,  # Native text has high confidence
            })
            
            y_position += line_height + 2.0  # Add spacing between paragraphs
        
        return lines
    except Exception as e:
        print(f"Warning: DOCX text extraction failed: {e}")
        return []


def extract_text_with_ocr(img: np.ndarray, reader=None, use_gpu: bool = False) -> List[Dict[str, Any]]:
    """
    Extract text from image using OCR.
    
    Args:
        img: Binary image
        reader: EasyOCR reader instance (will create if None)
        use_gpu: Whether to use GPU for OCR
        
    Returns:
        List of text lines with coordinates
    """
    if not HAS_EASYOCR:
        return []
    
    if reader is None:
        reader = easyocr.Reader(['en'], gpu=use_gpu)
    
    # EasyOCR expects RGB - convert binary to RGB
    if len(img.shape) == 2:
        # Binary image - invert it first (EasyOCR expects black text on white)
        img_inv = cv2.bitwise_not(img)
        img_rgb = cv2.cvtColor(img_inv, cv2.COLOR_GRAY2RGB)
    else:
        img_rgb = img
    
    try:
        results = reader.readtext(img_rgb)
    except Exception as e:
        print(f"Warning: OCR failed: {e}")
        return []
    
    lines = []
    for bbox, text, confidence in results:
        if confidence < 0.2:  # Lower threshold for better recall
            continue
        
        # bbox is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        xs = [pt[0] for pt in bbox]
        ys = [pt[1] for pt in bbox]
        
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        
        text_clean = text.strip()
        if not text_clean:
            continue
        
        lines.append({
            'text': text_clean,
            'x0': float(x0),
            'y0': float(y0),
            'x1': float(x1),
            'y1': float(y1),
            'confidence': float(confidence),
            'height': float(y1 - y0),
        })
    
    # Sort by y-coordinate (reading order)
    lines.sort(key=lambda l: (l['y0'], l['x0']))
    
    return lines


def compute_text_features(text: str, lines: List[Dict[str, Any]], 
                          block_stats: Dict[str, float]) -> Dict[str, float]:
    """
    Compute features for heading detection.
    
    Args:
        text: Line text
        lines: All lines in block for context
        block_stats: Block-level statistics
        
    Returns:
        Feature dictionary
    """
    if not text:
        return {}
    
    # Text features
    char_count = len(text)
    word_count = len(text.split())
    upper_ratio = uppercase_ratio(text)
    
    # Capitalization pattern
    words = text.split()
    title_case = sum(1 for w in words if w and w[0].isupper()) / max(1, len(words))
    
    # Check for common heading keywords
    cleaned = clean_for_heading(text).lower()
    has_keyword = guess_section_name(cleaned) is not None
    
    # Trailing colon (common in headings)
    has_colon = text.strip().endswith(':')
    
    # Length features
    short_enough = word_count <= 8 and char_count <= 50
    
    return {
        'char_count': char_count,
        'word_count': word_count,
        'upper_ratio': upper_ratio,
        'title_case': title_case,
        'has_keyword': 1.0 if has_keyword else 0.0,
        'has_colon': 1.0 if has_colon else 0.0,
        'short_enough': 1.0 if short_enough else 0.0,
    }


def detect_headings_in_block(block: Dict[str, Any], lines: List[Dict[str, Any]],
                             use_ocr: bool = True, reader=None) -> List[Dict[str, Any]]:
    """
    Detect headings within a block using localized analysis.
    
    Args:
        block: Block dictionary with image and coordinates
        lines: Pre-extracted lines (if available)
        use_ocr: Whether to use OCR for text extraction
        reader: EasyOCR reader instance
        
    Returns:
        List of heading candidates with scores
    """
    if not lines and use_ocr:
        # Extract text if not provided
        lines = extract_text_with_ocr(block['img'], reader)
    
    if not lines:
        return []
    
    # Compute block-level statistics
    heights = [l['height'] for l in lines if 'height' in l]
    avg_height = np.mean(heights) if heights else 10
    med_height = np.median(heights) if heights else 10
    
    # Spacing analysis (localized to this block)
    spacings = []
    for i in range(len(lines) - 1):
        spacing = lines[i+1]['y0'] - lines[i]['y1']
        spacings.append(spacing)
    
    avg_spacing = np.mean(spacings) if spacings else 5
    med_spacing = np.median(spacings) if spacings else 5
    
    block_stats = {
        'avg_height': avg_height,
        'med_height': med_height,
        'avg_spacing': avg_spacing,
        'med_spacing': med_spacing,
    }
    
    # Score each line as potential heading
    headings = []
    
    for i, line in enumerate(lines):
        text = line.get('text', '').strip()
        if not text:
            continue
        
        # Skip very long lines (likely content, not headings)
        word_count = len(text.split())
        char_count = len(text)
        if word_count > 10 or char_count > 60:
            continue
        
        # Skip lines that look like bullet points or list items
        if text.startswith('•') or text.startswith('-') or text.startswith('*'):
            continue
        
        # Skip lines with URLs, emails, or phone numbers
        if any(pattern in text.lower() for pattern in ['http', '@', 'www.', '.com', '.in']):
            continue
        if re.search(r'\d{10}', text):  # Phone number
            continue
        
        # Check for section keywords first (most important)
        cleaned = clean_for_heading(text).lower()
        canon = guess_section_name(cleaned)
        
        # Compute features
        features = compute_text_features(text, lines, block_stats)
        
        # Heading score (0-1) - much more conservative
        score = 0.0
        
        # STRONG indicators (required)
        has_keyword = canon is not None
        is_all_caps = features.get('upper_ratio', 0) >= 0.9
        has_colon = text.strip().endswith(':')
        
        # If it has a known section keyword, boost significantly
        if has_keyword:
            score += 0.5
            
            # Additional boost if it's JUST the keyword (like "SUMMARY", "EXPERIENCE")
            if word_count <= 3 and (is_all_caps or has_colon):
                score += 0.3
        
        # All caps AND short (strong heading indicator)
        if is_all_caps and word_count <= 5:
            score += 0.25
        
        # Trailing colon (common in headings)
        if has_colon and word_count <= 5:
            score += 0.2
        
        # Title case with short length
        if features.get('title_case', 0) >= 0.8 and word_count <= 4:
            score += 0.15
        
        # Height significantly larger than average
        if 'height' in line and line['height'] > 1.3 * avg_height:
            score += 0.15
        
        # Large spacing above (separated from previous content)
        if i > 0:
            space_above = line['y0'] - lines[i-1]['y1']
            if space_above > 2.0 * avg_spacing:
                score += 0.15
        
        # PENALTIES for non-heading characteristics
        
        # Penalize if it starts with lowercase (unlikely heading)
        if text and text[0].islower():
            score -= 0.2
        
        # Penalize if it contains too many numbers
        num_digits = sum(c.isdigit() for c in text)
        if num_digits > len(text) * 0.3:
            score -= 0.15
        
        # Penalize if it's too long
        if word_count > 5:
            score -= 0.15
        
        # Accept only if score is high enough (much stricter threshold)
        if score >= 0.6:  # Raised from 0.3 to 0.6
            headings.append({
                'text': text,
                'canon': canon or 'Unknown',
                'score': score,
                'line_index': i,
                'bbox': {
                    'x0': line['x0'],
                    'y0': line['y0'],
                    'x1': line['x1'],
                    'y1': line['y1'],
                },
                'features': features,
            })
    
    return headings


def split_sections_in_block(block: Dict[str, Any], headings: List[Dict[str, Any]],
                            lines: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Split block into sections based on detected headings.
    
    Args:
        block: Block dictionary
        headings: Detected headings
        lines: All text lines in block
        
    Returns:
        Dictionary mapping section names to lines
    """
    if not headings:
        # No headings found, treat entire block as content
        return {'Unknown': lines}
    
    # Sort headings by line index
    headings_sorted = sorted(headings, key=lambda h: h['line_index'])
    
    sections = {}
    
    for idx, heading in enumerate(headings_sorted):
        section_name = heading['canon']
        start_idx = heading['line_index'] + 1  # Start after the heading
        
        # Find end index (next heading or end of lines)
        if idx < len(headings_sorted) - 1:
            end_idx = headings_sorted[idx + 1]['line_index']
        else:
            end_idx = len(lines)
        
        # Extract section lines (excluding the heading itself)
        section_lines = []
        for i in range(start_idx, end_idx):
            # Skip if this line is also a heading
            if any(h['line_index'] == i for h in headings):
                continue
            section_lines.append(lines[i])
        
        # Add to sections
        if section_lines:
            if section_name not in sections:
                sections[section_name] = []
            sections[section_name].extend(section_lines)
    
    return sections if sections else {'Unknown': lines}


def merge_sections(all_sections: List[Dict[str, List[Dict[str, Any]]]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Merge sections from multiple blocks, preserving global order.
    
    Args:
        all_sections: List of section dictionaries from each block
        
    Returns:
        Merged sections dictionary
    """
    merged = defaultdict(list)
    
    for block_sections in all_sections:
        for section_name, lines in block_sections.items():
            # Normalize section name
            canon = guess_section_name(section_name) or section_name
            merged[canon].extend(lines)
    
    return dict(merged)


def robust_pipeline(path: str, use_ocr: bool = True, use_gpu: bool = False,
                   dpi: int = 300, max_depth: int = 3, verbose: bool = True,
                   prefer_native_text: bool = True) -> Tuple[Dict[str, Any], str]:
    """
    Robust resume parsing pipeline with layout-aware, recursive processing.
    
    Args:
        path: Path to PDF or image file
        use_ocr: Whether to use OCR for text extraction (fallback if native fails)
        use_gpu: Whether to use GPU for OCR
        dpi: Resolution for PDF rendering
        max_depth: Maximum recursion depth for block splitting
        verbose: Print progress information
        prefer_native_text: Try PyMuPDF native text extraction before OCR
        
    Returns:
        Tuple of (full result dict, simplified JSON string)
    """
    if verbose:
        print(f"[Robust Pipeline] Processing: {path}")
    
    path_obj = Path(path)
    
    # Initialize OCR reader if needed
    reader = None
    if use_ocr and HAS_EASYOCR:
        if verbose:
            print("[Robust Pipeline] Initializing EasyOCR...")
        reader = easyocr.Reader(['en'], gpu=use_gpu)
      # Determine number of pages
    if path_obj.suffix.lower() == '.pdf' and HAS_PYMUPDF:
        doc = fitz.open(str(path))
        num_pages = len(doc)
        doc.close()
    elif path_obj.suffix.lower() in ['.docx', '.doc']:
        num_pages = 1  # DOCX files are treated as single page
    else:
        num_pages = 1
    
    all_sections_by_page = []
    
    # Process each page
    for page_num in range(num_pages):
        if verbose:
            print(f"[Robust Pipeline] Processing page {page_num + 1}/{num_pages}")
        
        # Try native text extraction based on file type
        page_lines = []
        
        # DOCX files - use python-docx
        if prefer_native_text and path_obj.suffix.lower() in ['.docx', '.doc'] and HAS_DOCX:
            page_lines = extract_text_from_docx(path)
            if verbose and page_lines:
                print(f"[Robust Pipeline] Extracted {len(page_lines)} lines using python-docx")
        
        # PDF files - use PyMuPDF
        elif prefer_native_text and path_obj.suffix.lower() == '.pdf' and HAS_PYMUPDF:
            page_lines = extract_text_from_pdf_page(path, page_num)
            if verbose and page_lines:
                print(f"[Robust Pipeline] Extracted {len(page_lines)} lines using PyMuPDF")
        
        # Fallback to OCR if native extraction failed or disabled
        if not page_lines and use_ocr:
            if verbose:
                print(f"[Robust Pipeline] Falling back to OCR...")
            
            # Load and preprocess image
            img = load_and_preprocess(path, page_num, dpi)
            img = remove_lines(img)
            
            img_height, img_width = img.shape
            
            # Recursive block detection and splitting
            blocks = recursive_block_split(img, 0, 0, img_width, img_height, max_depth=max_depth)
            
            if verbose:
                print(f"[Robust Pipeline] Detected {len(blocks)} blocks")
            
            # Process each block
            for block_idx, block in enumerate(blocks):
                # Extract text from block using OCR
                lines = extract_text_with_ocr(block['img'], reader, use_gpu)
                
                if lines:
                    page_lines.extend(lines)
        
        # If we have lines (from either method), process them
        if page_lines:
            if verbose:
                print(f"[Robust Pipeline] Processing {len(page_lines)} text lines")
            
            # Detect headings
            block_stats = {
                'avg_height': np.mean([l['height'] for l in page_lines if 'height' in l]) if page_lines else 10,
                'med_height': np.median([l['height'] for l in page_lines if 'height' in l]) if page_lines else 10,
                'avg_spacing': 5,
                'med_spacing': 5,
            }
            
            headings = detect_headings_in_block({'img': None}, page_lines, use_ocr=False, reader=None)
            
            if verbose and headings:
                print(f"[Robust Pipeline] Found {len(headings)} headings")
                for h in headings[:5]:  # Show first 5
                    print(f"  - {h['text'][:50]} → {h['canon']}")
            
            # Split into sections
            sections = split_sections_in_block({}, headings, page_lines)
            all_sections_by_page.append(sections)
        else:
            if verbose:
                print(f"[Robust Pipeline] Warning: No text extracted from page {page_num + 1}")
    
    # Merge sections across all pages
    if all_sections_by_page:
        final_sections = merge_sections(all_sections_by_page)
    else:
        final_sections = {}
    
    # Format output
    sections_list = []
    for section_name, lines in final_sections.items():
        sections_list.append({
            'section': section_name,
            'lines': [{'text': l.get('text', '')} for l in lines],
            'line_count': len(lines),
        })
    
    result = {
        'meta': {
            'pages': num_pages,
            'sections': len(sections_list),
            'total_lines': sum(s['line_count'] for s in sections_list),
        },
        'sections': sections_list,
        'contact': {},  # TODO: Extract contact info
    }
    
    # Generate simplified JSON
    sim = simple_json(result)
    
    if verbose:
        print(f"[Robust Pipeline] Complete: {len(sections_list)} sections, {result['meta']['total_lines']} lines")
    
    return result, sim


# Debugging / quick test
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Robust resume parsing pipeline")
    parser.add_argument("--pdf", required=True, help="Path to PDF or image")
    parser.add_argument("--dpi", type=int, default=300, help="DPI for PDF rendering")
    parser.add_argument("--max_depth", type=int, default=3, help="Max recursion depth")
    parser.add_argument("--no_ocr", action="store_true", help="Disable OCR fallback")
    parser.add_argument("--force_ocr", action="store_true", help="Force OCR (skip native text)")
    parser.add_argument("--gpu", action="store_true", help="Use GPU for OCR")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")
    parser.add_argument("--save", help="Path to save simplified JSON")
    
    args = parser.parse_args()
    
    result, simplified = robust_pipeline(
        args.pdf,
        use_ocr=not args.no_ocr,
        use_gpu=args.gpu,
        dpi=args.dpi,
        max_depth=args.max_depth,
        verbose=not args.quiet,
        prefer_native_text=not args.force_ocr,
    )
    
    print("\n" + "="*60)
    print("SIMPLIFIED OUTPUT")
    print("="*60)
    print(simplified)
    
    if args.save:
        with open(args.save, 'w', encoding='utf-8') as f:
            f.write(simplified)
        print(f"\nSaved to: {args.save}")
