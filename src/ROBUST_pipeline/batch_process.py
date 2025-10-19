"""
Batch processing for robust resume parsing pipeline.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
import pandas as pd
from tqdm import tqdm

from .pipeline import robust_pipeline


def process_single_resume(
    file_path: Path,
    use_ocr: bool = True,
    use_gpu: bool = False,
    dpi: int = 300,
    max_depth: int = 3,
) -> Dict[str, Any]:
    """
    Process a single resume file.
    
    Args:
        file_path: Path to resume file
        use_ocr: Whether to use OCR
        use_gpu: Whether to use GPU
        dpi: DPI for PDF rendering
        max_depth: Max recursion depth
        
    Returns:
        Dictionary with results and metadata
    """
    try:
        result, simplified = robust_pipeline(
            str(file_path),
            use_ocr=use_ocr,
            use_gpu=use_gpu,
            dpi=dpi,
            max_depth=max_depth,
            verbose=False,
        )
        
        return {
            'file': file_path.name,
            'success': True,
            'result': result,
            'simplified': simplified,
            'error': None,
        }
    except Exception as e:
        return {
            'file': file_path.name,
            'success': False,
            'result': None,
            'simplified': None,
            'error': str(e),
        }


def batch_process_resumes(
    input_dir: str,
    output_dir: str,
    *,
    use_ocr: bool = True,
    use_gpu: bool = False,
    dpi: int = 300,
    max_depth: int = 3,
    max_workers: int = 4,
    file_pattern: str = "*.pdf",
) -> pd.DataFrame:
    """
    Batch process multiple resume files.
    
    Args:
        input_dir: Directory containing resume files
        output_dir: Directory to save results
        use_ocr: Whether to use OCR
        use_gpu: Whether to use GPU
        dpi: DPI for PDF rendering
        max_depth: Max recursion depth
        max_workers: Number of parallel workers
        file_pattern: Glob pattern for files to process
        
    Returns:
        DataFrame with processing results
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all matching files
    files = list(input_path.glob(file_pattern))
    
    if not files:
        print(f"No files found matching {file_pattern} in {input_dir}")
        return pd.DataFrame()
    
    print(f"Found {len(files)} files to process")
    
    # Process files
    results = []
    
    # Use ProcessPoolExecutor for parallel processing
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(
                process_single_resume,
                file_path,
                use_ocr,
                use_gpu,
                dpi,
                max_depth,
            ): file_path
            for file_path in files
        }
        
        # Collect results with progress bar
        with tqdm(total=len(files), desc="Processing resumes") as pbar:
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                pbar.update(1)
                
                # Save individual result
                if result['success']:
                    file_stem = Path(result['file']).stem
                    
                    # Save full result as JSON
                    json_path = output_path / f"{file_stem}_full.json"
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(result['result'], f, ensure_ascii=False, indent=2)
                    
                    # Save simplified result
                    simple_path = output_path / f"{file_stem}_simple.json"
                    with open(simple_path, 'w', encoding='utf-8') as f:
                        f.write(result['simplified'])
    
    # Create summary DataFrame
    summary_data = []
    for r in results:
        row = {
            'file': r['file'],
            'success': r['success'],
            'error': r['error'],
        }
        
        if r['success'] and r['result']:
            meta = r['result'].get('meta', {})
            row.update({
                'pages': meta.get('pages', 0),
                'sections': meta.get('sections', 0),
                'total_lines': meta.get('total_lines', 0),
            })
            
            # Add section names
            sections = r['result'].get('sections', [])
            row['section_names'] = ', '.join(s['section'] for s in sections)
        else:
            row.update({
                'pages': 0,
                'sections': 0,
                'total_lines': 0,
                'section_names': '',
            })
        
        summary_data.append(row)
    
    df = pd.DataFrame(summary_data)
    
    # Save summary
    summary_path = output_path / "batch_summary.xlsx"
    df.to_excel(summary_path, index=False)
    print(f"\nSummary saved to: {summary_path}")
    
    # Print statistics
    successful = df['success'].sum()
    failed = len(df) - successful
    print(f"\nProcessing complete:")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    
    if failed > 0:
        print(f"\nFailed files:")
        for _, row in df[~df['success']].iterrows():
            print(f"  - {row['file']}: {row['error']}")
    
    return df


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch process resumes with robust pipeline")
    parser.add_argument("--input", required=True, help="Input directory with resumes")
    parser.add_argument("--output", required=True, help="Output directory for results")
    parser.add_argument("--pattern", default="*.pdf", help="File pattern (default: *.pdf)")
    parser.add_argument("--dpi", type=int, default=300, help="DPI for PDF rendering")
    parser.add_argument("--max_depth", type=int, default=3, help="Max recursion depth")
    parser.add_argument("--no_ocr", action="store_true", help="Disable OCR")
    parser.add_argument("--gpu", action="store_true", help="Use GPU for OCR")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers")
    
    args = parser.parse_args()
    
    df = batch_process_resumes(
        args.input,
        args.output,
        use_ocr=not args.no_ocr,
        use_gpu=args.gpu,
        dpi=args.dpi,
        max_depth=args.max_depth,
        max_workers=args.workers,
        file_pattern=args.pattern,
    )
    
    print("\n" + "="*60)
    print("BATCH PROCESSING SUMMARY")
    print("="*60)
    print(df.to_string())
