"""
Step 1: Document Type Detection
================================
Identifies document type (PDF/DOCX) and checks if it's text-based or scanned.

Workflow:
1. Detect file type by extension
2. For PDF: Check if text-based or scanned
3. For DOCX: Check if contains embedded images (scanned pages)
4. Return detection result with confidence score
"""

from pathlib import Path
from typing import Dict, Any, Literal
from dataclasses import dataclass
import fitz  # PyMuPDF

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


@dataclass
class DocumentType:
    """Document type detection result"""
    file_type: Literal['pdf', 'docx', 'unknown']
    is_scanned: bool
    has_text_layer: bool
    confidence: float
    text_char_count: int
    image_count: int
    page_count: int
    recommended_extraction: Literal['text', 'ocr']
    metadata: Dict[str, Any]


class DocumentDetector:
    """Detects document type and determines extraction method"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
    
    def detect(self, file_path: str) -> DocumentType:
        """
        Detect document type and characteristics
        
        Args:
            file_path: Path to document
            
        Returns:
            DocumentType with detection results
        """
        path = Path(file_path)
        file_ext = path.suffix.lower()
        
        if self.verbose:
            print(f"[DocumentDetector] Analyzing: {path.name}")
        
        if file_ext == '.pdf':
            return self._detect_pdf(file_path)
        elif file_ext in ['.docx', '.doc']:
            return self._detect_docx(file_path)
        else:
            return DocumentType(
                file_type='unknown',
                is_scanned=False,
                has_text_layer=False,
                confidence=0.0,
                text_char_count=0,
                image_count=0,
                page_count=0,
                recommended_extraction='text',
                metadata={'error': f'Unsupported file type: {file_ext}'}
            )
    
    def _detect_pdf(self, file_path: str) -> DocumentType:
        """Detect PDF characteristics"""
        try:
            doc = fitz.open(file_path)
            
            total_chars = 0
            total_images = 0
            page_count = len(doc)
            
            # Analyze first few pages (sample)
            sample_size = min(3, page_count)
            
            for page_num in range(sample_size):
                page = doc[page_num]
                
                # Extract text
                text = page.get_text()
                total_chars += len(text.strip())
                
                # Count images
                images = page.get_images()
                total_images += len(images)
            
            # Average out for full document estimate
            if sample_size < page_count:
                total_chars = int(total_chars * page_count / sample_size)
                total_images = int(total_images * page_count / sample_size)
            
            # Determine if scanned
            avg_chars_per_page = total_chars / page_count if page_count > 0 else 0
            is_scanned = avg_chars_per_page < 100  # Less than 100 chars per page = likely scanned
            has_text_layer = avg_chars_per_page > 50
            
            # Image-heavy check
            avg_images_per_page = total_images / page_count if page_count > 0 else 0
            if avg_images_per_page > 3 and avg_chars_per_page < 500:
                is_scanned = True
            
            # Recommendation
            recommended_extraction = 'ocr' if is_scanned else 'text'
            
            # Confidence
            if is_scanned:
                confidence = 0.9
            elif has_text_layer and avg_chars_per_page > 500:
                confidence = 0.95
            else:
                confidence = 0.7
            
            doc.close()
            
            result = DocumentType(
                file_type='pdf',
                is_scanned=is_scanned,
                has_text_layer=has_text_layer,
                confidence=confidence,
                text_char_count=total_chars,
                image_count=total_images,
                page_count=page_count,
                recommended_extraction=recommended_extraction,
                metadata={
                    'avg_chars_per_page': avg_chars_per_page,
                    'avg_images_per_page': avg_images_per_page,
                    'sample_pages': sample_size
                }
            )
            
            if self.verbose:
                print(f"  Type: PDF")
                print(f"  Scanned: {is_scanned}")
                print(f"  Text layer: {has_text_layer}")
                print(f"  Chars: {total_chars}")
                print(f"  Images: {total_images}")
                print(f"  Recommended: {recommended_extraction.upper()}")
            
            return result
            
        except Exception as e:
            if self.verbose:
                print(f"  Error detecting PDF: {e}")
            
            return DocumentType(
                file_type='pdf',
                is_scanned=False,
                has_text_layer=True,
                confidence=0.5,
                text_char_count=0,
                image_count=0,
                page_count=1,
                recommended_extraction='text',
                metadata={'error': str(e)}
            )
    
    def _detect_docx(self, file_path: str) -> DocumentType:
        """Detect DOCX characteristics"""
        if not HAS_DOCX:
            return DocumentType(
                file_type='docx',
                is_scanned=False,
                has_text_layer=True,
                confidence=0.5,
                text_char_count=0,
                image_count=0,
                page_count=1,
                recommended_extraction='text',
                metadata={'error': 'python-docx not installed'}
            )
        
        try:
            doc = Document(file_path)
            
            # Count paragraphs and text
            text_length = 0
            para_count = 0
            for para in doc.paragraphs:
                text_length += len(para.text)
                if para.text.strip():
                    para_count += 1
            
            # Count images (inline shapes)
            image_count = 0
            for shape in doc.inline_shapes:
                image_count += 1
            
            # Determine if scanned (if mostly images, few paragraphs)
            is_scanned = image_count > 3 and para_count < 10
            has_text_layer = text_length > 50
            
            recommended_extraction = 'ocr' if is_scanned else 'text'
            confidence = 0.9 if text_length > 100 else 0.7
            
            result = DocumentType(
                file_type='docx',
                is_scanned=is_scanned,
                has_text_layer=has_text_layer,
                confidence=confidence,
                text_char_count=text_length,
                image_count=image_count,
                page_count=1,  # DOCX doesn't have clear page boundaries
                recommended_extraction=recommended_extraction,
                metadata={
                    'paragraph_count': para_count,
                    'avg_para_length': text_length / para_count if para_count > 0 else 0
                }
            )
            
            if self.verbose:
                print(f"  Type: DOCX")
                print(f"  Scanned: {is_scanned}")
                print(f"  Paragraphs: {para_count}")
                print(f"  Images: {image_count}")
                print(f"  Recommended: {recommended_extraction.upper()}")
            
            return result
            
        except Exception as e:
            if self.verbose:
                print(f"  Error detecting DOCX: {e}")
            
            return DocumentType(
                file_type='docx',
                is_scanned=False,
                has_text_layer=True,
                confidence=0.5,
                text_char_count=0,
                image_count=0,
                page_count=1,
                recommended_extraction='text',
                metadata={'error': str(e)}
            )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python document_detector.py <file_path>")
        sys.exit(1)
    
    detector = DocumentDetector(verbose=True)
    result = detector.detect(sys.argv[1])
    
    print("\n" + "="*60)
    print("DETECTION RESULT")
    print("="*60)
    print(f"File Type: {result.file_type.upper()}")
    print(f"Is Scanned: {result.is_scanned}")
    print(f"Has Text Layer: {result.has_text_layer}")
    print(f"Confidence: {result.confidence:.1%}")
    print(f"Recommended Extraction: {result.recommended_extraction.upper()}")
    print(f"Text Chars: {result.text_char_count:,}")
    print(f"Images: {result.image_count}")
    print(f"Pages: {result.page_count}")
    print(f"\nMetadata: {result.metadata}")
