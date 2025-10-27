"""
Step 2: Word Extraction with Metadata
======================================
Extracts all words from document with rich metadata.

For each word, captures:
- Text content
- Page number
- Bounding box (x0, y0, x1, y1)
- Font size
- Font family
- Font color (RGB)
- Bold/italic attributes
- Position in reading order

Supports both text-based and OCR-based extraction.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import fitz  # PyMuPDF

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


@dataclass
class WordMetadata:
    """Metadata for a single word"""
    text: str
    page: int
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    font_size: Optional[float] = None
    font_name: Optional[str] = None
    font_color: Optional[Tuple[int, int, int]] = None  # (R, G, B)
    is_bold: bool = False
    is_italic: bool = False
    is_uppercase: bool = False
    confidence: float = 1.0  # For OCR
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @property
    def x_center(self) -> float:
        """Get x-coordinate of center"""
        return (self.bbox[0] + self.bbox[2]) / 2
    
    @property
    def y_center(self) -> float:
        """Get y-coordinate of center"""
        return (self.bbox[1] + self.bbox[3]) / 2
    
    @property
    def width(self) -> float:
        """Get width of bounding box"""
        return self.bbox[2] - self.bbox[0]
    
    @property
    def height(self) -> float:
        """Get height of bounding box"""
        return self.bbox[3] - self.bbox[1]


class WordExtractor:
    """Extracts words with metadata from documents"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._ocr_reader = None
    
    def extract_pdf_text_based(self, pdf_path: str) -> List[List[WordMetadata]]:
        """
        Extract words from PDF using text layer (PyMuPDF)
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of pages, each containing list of WordMetadata
        """
        if self.verbose:
            print(f"[WordExtractor] Extracting text-based words from PDF...")
        
        doc = fitz.open(pdf_path)
        all_pages = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            words = []
            
            # Get words with position
            word_list = page.get_text("words")  # Returns: (x0, y0, x1, y1, "word", block_no, line_no, word_no)
            
            for word_tuple in word_list:
                x0, y0, x1, y1, text, block_no, line_no, word_no = word_tuple
                
                # Try to get font information from text dict
                font_info = self._get_font_info_from_page(page, (x0, y0, x1, y1))
                
                word_meta = WordMetadata(
                    text=text,
                    page=page_num,
                    bbox=(x0, y0, x1, y1),
                    font_size=font_info.get('size'),
                    font_name=font_info.get('name'),
                    font_color=font_info.get('color'),
                    is_bold=font_info.get('is_bold', False),
                    is_italic=font_info.get('is_italic', False),
                    is_uppercase=text.isupper() and len(text) > 1,
                    confidence=1.0
                )
                
                words.append(word_meta)
            
            all_pages.append(words)
            
            if self.verbose:
                print(f"  Page {page_num + 1}: {len(words)} words")
        
        doc.close()
        
        if self.verbose:
            total_words = sum(len(page) for page in all_pages)
            print(f"  Total: {total_words} words across {len(all_pages)} pages")
        
        return all_pages
    
    def extract_pdf_ocr(self, pdf_path: str, dpi: int = 300, languages: List[str] = None) -> List[List[WordMetadata]]:
        """
        Extract words from PDF using OCR (EasyOCR)
        
        Args:
            pdf_path: Path to PDF file
            dpi: DPI for rendering PDF to image
            languages: List of language codes for OCR
            
        Returns:
            List of pages, each containing list of WordMetadata
        """
        if not HAS_EASYOCR:
            raise ImportError("EasyOCR not installed. Install with: pip install easyocr")
        
        if languages is None:
            languages = ['en']
        
        if self.verbose:
            print(f"[WordExtractor] Extracting OCR words from PDF...")
            print(f"  DPI: {dpi}, Languages: {languages}")
        
        # Initialize OCR reader (lazy)
        if self._ocr_reader is None:
            if self.verbose:
                print("  Initializing EasyOCR reader...")
            self._ocr_reader = easyocr.Reader(languages, gpu=False)
        
        doc = fitz.open(pdf_path)
        all_pages = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Render page to image
            mat = fitz.Matrix(dpi / 72, dpi / 72)  # 72 DPI is default
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to numpy array for EasyOCR
            import numpy as np
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            
            # Run OCR
            results = self._ocr_reader.readtext(img)
            
            # Convert OCR results to WordMetadata
            words = []
            page_width = page.rect.width
            page_height = page.rect.height
            img_width = pix.width
            img_height = pix.height
            
            for detection in results:
                bbox_coords, text, confidence = detection
                
                # OCR bbox is [[x0,y0], [x1,y0], [x1,y1], [x0,y1]]
                x0 = min(point[0] for point in bbox_coords)
                y0 = min(point[1] for point in bbox_coords)
                x1 = max(point[0] for point in bbox_coords)
                y1 = max(point[1] for point in bbox_coords)
                
                # Scale back to PDF coordinates
                x0_pdf = x0 * page_width / img_width
                y0_pdf = y0 * page_height / img_height
                x1_pdf = x1 * page_width / img_width
                y1_pdf = y1 * page_height / img_height
                
                # Split text into words
                word_texts = text.split()
                if not word_texts:
                    continue
                
                # Estimate bbox for each word
                word_width = (x1_pdf - x0_pdf) / len(word_texts)
                
                for i, word_text in enumerate(word_texts):
                    word_x0 = x0_pdf + i * word_width
                    word_x1 = word_x0 + word_width
                    
                    word_meta = WordMetadata(
                        text=word_text,
                        page=page_num,
                        bbox=(word_x0, y0_pdf, word_x1, y1_pdf),
                        font_size=y1_pdf - y0_pdf,  # Approximate
                        font_name=None,
                        font_color=None,
                        is_bold=False,
                        is_italic=False,
                        is_uppercase=word_text.isupper() and len(word_text) > 1,
                        confidence=confidence
                    )
                    
                    words.append(word_meta)
            
            all_pages.append(words)
            
            if self.verbose:
                print(f"  Page {page_num + 1}: {len(words)} words (OCR)")
        
        doc.close()
        
        if self.verbose:
            total_words = sum(len(page) for page in all_pages)
            print(f"  Total: {total_words} words across {len(all_pages)} pages")
        
        return all_pages
    
    def extract_docx(self, docx_path: str) -> List[List[WordMetadata]]:
        """
        Extract words from DOCX with metadata
        
        Note: DOCX doesn't have precise positioning, so we estimate
        
        Args:
            docx_path: Path to DOCX file
            
        Returns:
            List containing single page of WordMetadata
        """
        if not HAS_DOCX:
            raise ImportError("python-docx not installed. Install with: pip install python-docx")
        
        if self.verbose:
            print(f"[WordExtractor] Extracting words from DOCX...")
        
        doc = Document(docx_path)
        words = []
        
        y_position = 0.0
        line_height = 12.0  # Approximate
        
        for para in doc.paragraphs:
            if not para.text.strip():
                y_position += line_height * 0.5  # Empty line
                continue
            
            # Process runs (formatted text segments)
            x_position = 72.0  # Left margin
            
            for run in para.runs:
                run_text = run.text
                if not run_text.strip():
                    continue
                
                # Get formatting
                is_bold = run.bold or False
                is_italic = run.italic or False
                font_size = run.font.size.pt if run.font.size else 12.0
                font_name = run.font.name
                
                # Split into words
                run_words = run_text.split()
                
                for word_text in run_words:
                    # Estimate word width (very rough)
                    word_width = len(word_text) * font_size * 0.6
                    
                    word_meta = WordMetadata(
                        text=word_text,
                        page=0,  # DOCX doesn't have pages in the same way
                        bbox=(x_position, y_position, x_position + word_width, y_position + font_size),
                        font_size=font_size,
                        font_name=font_name,
                        font_color=None,  # Hard to extract from DOCX
                        is_bold=is_bold,
                        is_italic=is_italic,
                        is_uppercase=word_text.isupper() and len(word_text) > 1,
                        confidence=1.0
                    )
                    
                    words.append(word_meta)
                    x_position += word_width + font_size * 0.3  # Space between words
            
            y_position += line_height
        
        if self.verbose:
            print(f"  Total: {len(words)} words")
        
        return [words]  # Return as single page
    
    def _get_font_info_from_page(self, page, bbox: Tuple[float, float, float, float]) -> Dict[str, Any]:
        """
        Extract font information for a bounding box region
        
        Args:
            page: PyMuPDF page object
            bbox: Bounding box (x0, y0, x1, y1)
            
        Returns:
            Dictionary with font info
        """
        try:
            # Get text dict for detailed info
            text_dict = page.get_text("dict")
            
            x0, y0, x1, y1 = bbox
            x_center = (x0 + x1) / 2
            y_center = (y0 + y1) / 2
            
            # Find matching span
            for block in text_dict.get("blocks", []):
                if block.get("type") != 0:  # Not text
                    continue
                
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        span_bbox = span.get("bbox", [0, 0, 0, 0])
                        sx0, sy0, sx1, sy1 = span_bbox
                        
                        # Check if our word is in this span
                        if sx0 <= x_center <= sx1 and sy0 <= y_center <= sy1:
                            font_name = span.get("font", "")
                            font_size = span.get("size", 12.0)
                            color = span.get("color", 0)  # Integer color code
                            
                            # Convert color to RGB
                            r = (color >> 16) & 0xFF
                            g = (color >> 8) & 0xFF
                            b = color & 0xFF
                            
                            # Detect bold/italic from font name
                            font_lower = font_name.lower()
                            is_bold = 'bold' in font_lower or 'heavy' in font_lower
                            is_italic = 'italic' in font_lower or 'oblique' in font_lower
                            
                            return {
                                'name': font_name,
                                'size': font_size,
                                'color': (r, g, b),
                                'is_bold': is_bold,
                                'is_italic': is_italic
                            }
            
            # Default if not found
            return {
                'name': 'Unknown',
                'size': 12.0,
                'color': (0, 0, 0),
                'is_bold': False,
                'is_italic': False
            }
            
        except Exception:
            return {
                'name': 'Unknown',
                'size': 12.0,
                'color': (0, 0, 0),
                'is_bold': False,
                'is_italic': False
            }


if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python word_extractor.py <file_path> [--ocr]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    use_ocr = '--ocr' in sys.argv
    
    extractor = WordExtractor(verbose=True)
    
    if file_path.endswith('.pdf'):
        if use_ocr:
            pages = extractor.extract_pdf_ocr(file_path)
        else:
            pages = extractor.extract_pdf_text_based(file_path)
    elif file_path.endswith('.docx'):
        pages = extractor.extract_docx(file_path)
    else:
        print(f"Unsupported file type: {file_path}")
        sys.exit(1)
    
    # Print summary
    print("\n" + "="*60)
    print("EXTRACTION SUMMARY")
    print("="*60)
    print(f"Total pages: {len(pages)}")
    print(f"Total words: {sum(len(page) for page in pages)}")
    
    # Show sample from first page
    if pages and pages[0]:
        print(f"\nSample words from page 1 (first 5):")
        for word in pages[0][:5]:
            print(f"  '{word.text}' @ {word.bbox} | size={word.font_size} | bold={word.is_bold}")
