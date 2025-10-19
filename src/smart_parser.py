"""
Smart Resume Parser - Routes to best pipeline based on layout detection.
Simple, pragmatic approach: use the right tool for the right job.
"""

from typing import Dict, Any, Tuple
from pathlib import Path

from src.layout_detector import detect_resume_layout
from src.PDF_pipeline.pipeline import run_pipeline as run_pdf_pipeline
from src.IMG_pipeline.pipeline import run_pipeline_ocr


def smart_parse_resume(
    pdf_path: str,
    force_pipeline: str = None,
    ocr_dpi: int = 300,
    ocr_languages: list = None,
    verbose: bool = True
) -> Tuple[Dict[str, Any], str, Dict[str, Any]]:
    """
    Smart resume parser that automatically selects the best pipeline.
    
    Args:
        pdf_path: Path to PDF resume
        force_pipeline: Force 'pdf' or 'ocr' pipeline (None = auto-detect)
        ocr_dpi: DPI for OCR (if used)
        ocr_languages: Languages for OCR (if used)
        verbose: Print progress
        
    Returns:
        (result_dict, simplified_json, metadata)
        
    metadata contains:
        - pipeline_used: 'pdf' or 'ocr'
        - layout_analysis: dict from detector
        - processing_time: float
    """
    import time
    
    if ocr_languages is None:
        ocr_languages = ['en']
    
    metadata = {
        'pipeline_used': None,
        'layout_analysis': None,
        'processing_time': 0.0,
        'file_name': Path(pdf_path).name
    }
    
    start_time = time.time()
    
    # Detect layout
    if force_pipeline:
        use_pipeline = force_pipeline
        if verbose:
            print(f"[Smart Parser] Forced to use {use_pipeline.upper()} pipeline")
        metadata['layout_analysis'] = {'forced': True}
    else:
        analysis = detect_resume_layout(pdf_path)
        use_pipeline = analysis['recommended_pipeline']
        metadata['layout_analysis'] = analysis
        
        if verbose:
            print(f"[Smart Parser] Auto-detected: {use_pipeline.upper()} pipeline")
            print(f"  Confidence: {analysis['confidence']:.2%}")
            print(f"  Columns: {analysis['num_columns']}")
            print(f"  Scanned: {analysis['is_scanned']}")
    
    # Run appropriate pipeline
    try:
        if use_pipeline == 'pdf':
            if verbose:
                print(f"[Smart Parser] Running PDF pipeline (PyMuPDF)...")
            
            result, simplified = run_pdf_pipeline(
                pdf_path=pdf_path,
                verbose=verbose
            )
            metadata['pipeline_used'] = 'pdf'
            
        else:  # ocr
            if verbose:
                print(f"[Smart Parser] Running OCR pipeline (EasyOCR)...")
            
            result, simplified = run_pipeline_ocr(
                pdf_path=pdf_path,
                dpi=ocr_dpi,
                languages=ocr_languages,
                verbose=verbose,
                gpu=False  # CPU mode for compatibility
            )
            metadata['pipeline_used'] = 'ocr'
        
        metadata['processing_time'] = time.time() - start_time
        metadata['success'] = True
        
        if verbose:
            print(f"[Smart Parser] Completed in {metadata['processing_time']:.2f}s")
            print(f"  Sections found: {len(result.get('sections', []))}")
            total_lines = sum(len(s.get('lines', [])) for s in result.get('sections', []))
            print(f"  Total lines: {total_lines}")
        
        return result, simplified, metadata
        
    except Exception as e:
        metadata['processing_time'] = time.time() - start_time
        metadata['success'] = False
        metadata['error'] = str(e)
        
        if verbose:
            print(f"[Smart Parser] Error: {e}")
        
        # Return empty result
        empty = {
            "meta": {"pages": 0, "columns": 0, "sections": 0, "lines_total": 0}, 
            "sections": [], 
            "contact": {}
        }
        return empty, "[]", metadata


def batch_smart_parse(
    input_dir: str,
    output_dir: str = None,
    file_pattern: str = "*.pdf",
    max_files: int = None,
    verbose: bool = True
) -> list:
    """
    Batch process resumes with smart routing.
    
    Args:
        input_dir: Directory containing PDFs
        output_dir: Optional output directory for saving results
        file_pattern: Glob pattern for files
        max_files: Maximum number of files to process
        verbose: Print progress
        
    Returns:
        List of (file_path, result, simplified, metadata) tuples
    """
    from pathlib import Path
    import json
    
    input_path = Path(input_dir)
    files = list(input_path.glob(file_pattern))
    
    if max_files:
        files = files[:max_files]
    
    if not files:
        print(f"No files found matching {file_pattern} in {input_dir}")
        return []
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Smart Batch Processing")
        print(f"{'='*60}")
        print(f"Files found: {len(files)}")
        print(f"Input: {input_dir}")
        if output_dir:
            print(f"Output: {output_dir}")
        print(f"{'='*60}\n")
    
    results = []
    
    for i, file_path in enumerate(files, 1):
        if verbose:
            print(f"\n[{i}/{len(files)}] Processing: {file_path.name}")
            print("-" * 60)
        
        try:
            result, simplified, metadata = smart_parse_resume(
                str(file_path),
                verbose=verbose
            )
            
            results.append((file_path, result, simplified, metadata))
            
            # Save if output directory specified
            if output_dir:
                out_path = Path(output_dir)
                out_path.mkdir(parents=True, exist_ok=True)
                
                stem = file_path.stem
                
                # Save full result
                with open(out_path / f"{stem}_full.json", 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                # Save simplified
                with open(out_path / f"{stem}_simple.json", 'w', encoding='utf-8') as f:
                    f.write(simplified)
                
                # Save metadata
                with open(out_path / f"{stem}_metadata.json", 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            if verbose:
                print(f"ERROR: {e}")
            results.append((file_path, None, None, {'error': str(e)}))
    
    # Summary
    if verbose:
        print(f"\n{'='*60}")
        print(f"Batch Processing Summary")
        print(f"{'='*60}")
        
        pdf_count = sum(1 for _, _, _, m in results if m.get('pipeline_used') == 'pdf')
        ocr_count = sum(1 for _, _, _, m in results if m.get('pipeline_used') == 'ocr')
        error_count = sum(1 for _, _, _, m in results if 'error' in m)
        
        print(f"Total files: {len(results)}")
        print(f"  PDF pipeline: {pdf_count}")
        print(f"  OCR pipeline: {ocr_count}")
        print(f"  Errors: {error_count}")
        
        if results:
            avg_time = sum(m.get('processing_time', 0) for _, _, _, m in results) / len(results)
            print(f"\nAverage processing time: {avg_time:.2f}s")
        
        print(f"{'='*60}\n")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart resume parser with automatic pipeline selection")
    parser.add_argument("--pdf", help="Single PDF file to parse")
    parser.add_argument("--batch", help="Directory of PDFs to batch process")
    parser.add_argument("--output", help="Output directory for batch processing")
    parser.add_argument("--force", choices=['pdf', 'ocr'], help="Force specific pipeline")
    parser.add_argument("--dpi", type=int, default=300, help="DPI for OCR")
    parser.add_argument("--max", type=int, help="Max files for batch processing")
    parser.add_argument("--quiet", action="store_true", help="Quiet mode")
    
    args = parser.parse_args()
    
    if args.pdf:
        # Single file
        result, simplified, metadata = smart_parse_resume(
            args.pdf,
            force_pipeline=args.force,
            ocr_dpi=args.dpi,
            verbose=not args.quiet
        )
        
        print("\n" + "="*60)
        print("RESULT")
        print("="*60)
        print(simplified)
        
    elif args.batch:
        # Batch processing
        results = batch_smart_parse(
            input_dir=args.batch,
            output_dir=args.output,
            max_files=args.max,
            verbose=not args.quiet
        )
        
    else:
        parser.print_help()
