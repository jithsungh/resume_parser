"""
Intelligent Multi-Stage Resume Parser
=====================================

Strategy:
1. Detect file type (PDF vs DOCX)
2. Try native extraction first (PDF or DOCX pipeline)
3. Validate quality (sections found, text extracted)
4. If poor quality (<=2 sections or minimal text):
   - Check if scanned → use OCR
   - Check if multi-column → use layout-aware parsing
5. Return best result

This ensures we always try the fastest method first, then escalate only if needed.
"""

import time
import json
from typing import Dict, Any, Tuple, Optional
from pathlib import Path


def detect_file_type(file_path: str) -> str:
    """Detect if file is PDF or DOCX based on extension."""
    suffix = Path(file_path).suffix.lower()
    if suffix == '.pdf':
        return 'pdf'
    elif suffix in ['.docx', '.doc']:
        return 'docx'
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def validate_extraction_quality(result: Dict[str, Any], verbose: bool = False) -> Dict[str, Any]:
    """
    Validate the quality of extraction.
    
    Returns quality metrics:
        - is_good: bool (True if extraction seems successful)
        - num_sections: int
        - total_lines: int
        - has_contact: bool
        - reasons: list of quality issues
    """
    quality = {
        'is_good': True,
        'num_sections': 0,
        'total_lines': 0,
        'has_contact': False,
        'reasons': []
    }
    
    sections = result.get('sections', [])
    quality['num_sections'] = len(sections)
    
    # Count total lines across all sections
    total_lines = sum(len(s.get('lines', [])) for s in sections)
    quality['total_lines'] = total_lines
    
    # Check contact info
    contact = result.get('contact', {})
    quality['has_contact'] = bool(contact.get('email') or contact.get('phone') or contact.get('name'))
    
    # Quality checks
    if quality['num_sections'] == 0:
        quality['is_good'] = False
        quality['reasons'].append("No sections detected")
    
    if quality['num_sections'] <= 2:
        quality['is_good'] = False
        quality['reasons'].append(f"Only {quality['num_sections']} sections detected (expected 3+)")
    
    if total_lines < 10:
        quality['is_good'] = False
        quality['reasons'].append(f"Only {total_lines} lines extracted (too few)")
    
    # Check if text is jumbled (very long lines might indicate column mixing)
    for section in sections:
        for line in section.get('lines', []):
            if len(line) > 500:  # Suspiciously long line
                quality['is_good'] = False
                quality['reasons'].append("Detected jumbled/merged text (lines too long)")
                break
        if not quality['is_good']:
            break
    
    if verbose:
        print(f"  [Quality Check] Sections: {quality['num_sections']}, Lines: {quality['total_lines']}, "
              f"Contact: {quality['has_contact']}, Good: {quality['is_good']}")
        if quality['reasons']:
            for reason in quality['reasons']:
                print(f"    - {reason}")
    
    return quality


def check_if_scanned(pdf_path: str) -> bool:
    """Quick check if PDF is scanned (no text layer)."""
    import fitz
    try:
        pdf_path = str(Path(pdf_path).resolve())
        doc = fitz.open(pdf_path)
        if len(doc) == 0:
            doc.close()
            return True
        
        # Check first page for text
        text = doc[0].get_text().strip()
        doc.close()
        
        return len(text) < 50  # Less than 50 chars = likely scanned
    except Exception:
        return False


def detect_multi_column_layout(pdf_path: str) -> Tuple[bool, int]:
    """
    Quick check if PDF has multi-column layout.
    Returns (is_multi_column, num_columns)
    """
    import fitz
    try:
        pdf_path = str(Path(pdf_path).resolve())
        doc = fitz.open(pdf_path)
        if len(doc) == 0:
            doc.close()
            return False, 1
        
        page = doc[0]
        words = page.get_text("words")
        doc.close()
        
        if len(words) < 20:
            return False, 1
        
        # Simple heuristic: group words by horizontal position
        # If we have distinct X clusters, likely multi-column
        x_positions = [w[0] for w in words]  # x0 coordinate
        
        # Find gaps in X distribution
        x_positions.sort()
        page_width = page.rect.width
        mid_x = page_width / 2
        
        # Count words in left vs right half
        left_count = sum(1 for x in x_positions if x < mid_x)
        right_count = sum(1 for x in x_positions if x >= mid_x)
        
        # If both halves have substantial content, likely 2-column
        if left_count > 10 and right_count > 10:
            ratio = min(left_count, right_count) / max(left_count, right_count)
            if ratio > 0.3:  # At least 30% balance
                return True, 2
        
        return False, 1
        
    except Exception:
        return False, 1


def intelligent_parse_resume(
    file_path: str,
    force_pipeline: Optional[str] = None,
    verbose: bool = True
) -> Tuple[Dict[str, Any], str, Dict[str, Any]]:
    """
    Intelligent multi-stage resume parser.
    
    Strategy:
    1. Detect file type (PDF/DOCX)
    2. Try native pipeline first
    3. Validate quality
    4. If poor quality:
       - Check if scanned → OCR
       - Check if multi-column → layout-aware
    5. Return best result
    
    Args:
        file_path: Path to resume file
        force_pipeline: Force specific pipeline ('pdf', 'ocr', 'docx')
        verbose: Print detailed progress
        
    Returns:
        (result_dict, simplified_json, metadata)
    """
    from src.PDF_pipeline.pipeline import run_pipeline as run_pdf_pipeline
    from src.IMG_pipeline.pipeline import run_pipeline_ocr
    # from src.DOCX_pipeline.pipeline import run_docx_pipeline  # TODO: implement if needed
    
    start_time = time.time()
    
    metadata = {
        'file_name': Path(file_path).name,
        'file_type': None,
        'attempts': [],
        'final_pipeline': None,
        'processing_time': 0.0,
        'success': False
    }
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Intelligent Parser: {Path(file_path).name}")
        print(f"{'='*60}")
    
    try:
        # Step 1: Detect file type
        file_type = detect_file_type(file_path)
        metadata['file_type'] = file_type
        
        if verbose:
            print(f"[Step 1] File type: {file_type.upper()}")
        
        if file_type == 'docx':
            if verbose:
                print("[Note] DOCX pipeline not implemented yet. Treating as unsupported.")
            raise NotImplementedError("DOCX pipeline not yet available")
        
        # Step 2: Try native PDF extraction first
        if not force_pipeline or force_pipeline == 'pdf':
            if verbose:
                print(f"[Step 2] Trying native PDF extraction...")
                attempt = {
                    'pipeline': 'pdf',
                    'stage': 'native',
                    'start_time': time.time()
                }
            
            try:
                result, simplified = run_pdf_pipeline(
                    pdf_path=file_path,
                    use_histogram_columns=True,  # Enable histogram-based column detection
                    verbose=False  # Suppress internal logs
                )
                
                attempt['duration'] = time.time() - attempt['start_time']
                attempt['success'] = True
                
                # Step 3: Validate quality
                quality = validate_extraction_quality(result, verbose=verbose)
                attempt['quality'] = quality
                
                metadata['attempts'].append(attempt)
                
                if quality['is_good']:
                    # Success! Native extraction worked
                    if verbose:
                        print(f"  ✓ Native PDF extraction successful")
                        print(f"    Sections: {quality['num_sections']}, Lines: {quality['total_lines']}")
                    
                    metadata['final_pipeline'] = 'pdf'
                    metadata['processing_time'] = time.time() - start_time
                    metadata['success'] = True
                    
                    return result, simplified, metadata
                
                else:
                    # Quality is poor, need to try alternative methods
                    if verbose:
                        print(f"  ✗ Native PDF extraction has quality issues:")
                        for reason in quality['reasons']:
                            print(f"      - {reason}")
                    
            except Exception as e:
                attempt['duration'] = time.time() - attempt['start_time']
                attempt['success'] = False
                attempt['error'] = str(e)
                metadata['attempts'].append(attempt)
                
                if verbose:
                    print(f"  ✗ Native PDF extraction failed: {e}")
        
        # Step 4: Check if scanned (needs OCR)
        if verbose:
            print(f"[Step 3] Diagnosing issue...")
        
        is_scanned = check_if_scanned(file_path)
        is_multi_col, num_cols = detect_multi_column_layout(file_path)
        
        if verbose:
            print(f"  Scanned document: {is_scanned}")
            print(f"  Multi-column layout: {is_multi_col} ({num_cols} columns)")
        
        # Step 5: Choose recovery strategy
        if is_scanned or force_pipeline == 'ocr':
            # Use OCR for scanned documents
            if verbose:
                print(f"[Step 4] Trying OCR pipeline (document is scanned)...")
            
            attempt = {
                'pipeline': 'ocr',
                'stage': 'recovery',
                'reason': 'scanned_document',
                'start_time': time.time()
            }
            
            try:
                result, simplified = run_pipeline_ocr(
                    pdf_path=file_path,
                    dpi=300,
                    languages=['en'],
                    verbose=False,
                    gpu=False
                )
                
                attempt['duration'] = time.time() - attempt['start_time']
                attempt['success'] = True
                
                quality = validate_extraction_quality(result, verbose=verbose)
                attempt['quality'] = quality
                
                metadata['attempts'].append(attempt)
                metadata['final_pipeline'] = 'ocr'
                metadata['processing_time'] = time.time() - start_time
                metadata['success'] = True
                
                if verbose:
                    print(f"  ✓ OCR extraction completed")
                    print(f"    Sections: {quality['num_sections']}, Lines: {quality['total_lines']}")
                
                return result, simplified, metadata
                
            except Exception as e:
                attempt['duration'] = time.time() - attempt['start_time']
                attempt['success'] = False
                attempt['error'] = str(e)
                metadata['attempts'].append(attempt)
                
                if verbose:
                    print(f"  ✗ OCR extraction failed: {e}")
        
        elif is_multi_col:
            # Complex multi-column layout needs special handling
            if verbose:
                print(f"[Step 4] Complex multi-column layout detected")
                print(f"  TODO: Implement layout-aware parsing")
                print(f"  For now, returning best available result...")
            
            # For now, return the PDF result (even if low quality)
            # TODO: Implement layout-aware recursive parsing
            if metadata['attempts']:
                last_attempt = metadata['attempts'][-1]
                if 'result' in locals():
                    metadata['final_pipeline'] = 'pdf_lowquality'
                    metadata['processing_time'] = time.time() - start_time
                    metadata['success'] = True
                    metadata['warning'] = 'Multi-column layout may have quality issues'
                    
                    return result, simplified, metadata
        
        # If we get here, all strategies failed
        if verbose:
            print(f"[Failed] All extraction strategies failed")
        
        metadata['processing_time'] = time.time() - start_time
        metadata['success'] = False
        
        # Return empty result
        empty = {
            "meta": {"pages": 0, "columns": 0, "sections": 0, "lines_total": 0},
            "sections": [],
            "contact": {}
        }
        return empty, "[]", metadata
        
    except Exception as e:
        metadata['processing_time'] = time.time() - start_time
        metadata['success'] = False
        metadata['error'] = str(e)
        
        if verbose:
            print(f"[Error] {e}")
        
        empty = {
            "meta": {"pages": 0, "columns": 0, "sections": 0, "lines_total": 0},
            "sections": [],
            "contact": {}
        }
        return empty, "[]", metadata


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Intelligent multi-stage resume parser")
    parser.add_argument("--pdf", required=True, help="PDF file to parse")
    parser.add_argument("--force", choices=['pdf', 'ocr'], help="Force specific pipeline")
    parser.add_argument("--quiet", action="store_true", help="Quiet mode")
    parser.add_argument("--save", help="Save output to JSON file")
    
    args = parser.parse_args()
    
    result, simplified, metadata = intelligent_parse_resume(
        file_path=args.pdf,
        force_pipeline=args.force,
        verbose=not args.quiet
    )
    
    print("\n" + "="*60)
    print("FINAL RESULT")
    print("="*60)
    print(simplified)
    
    if metadata.get('warning'):
        print(f"\n⚠️  Warning: {metadata['warning']}")
    
    print(f"\nProcessing time: {metadata['processing_time']:.2f}s")
    print(f"Pipeline used: {metadata['final_pipeline']}")
    
    if args.save:
        with open(args.save, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\nSaved to: {args.save}")
