#!/usr/bin/env python3
"""
Batch Resume Segmenter
=======================
Recursively finds and segments all resumes in a directory.

Usage:
    python segment_batch.py <directory> [options]
    
Options:
    --output-dir DIR    Output directory for results (default: ./batch_results)
    --format FORMAT     Output format: json, excel, both (default: both)
    --extensions EXTS   File extensions to process (default: .pdf .docx)
    --limit N           Limit number of files to process
    --debug             Include debug information in output
    --no-ocr            Disable OCR for scanned PDFs
    --no-embeddings     Disable semantic embeddings
    --verbose           Show detailed progress for each file
    --learn             Enable section learning
    --parallel          Process files in parallel (faster)
    --workers N         Number of parallel workers (default: 4)

Examples:
    python segment_batch.py freshteams_resume/
    python segment_batch.py freshteams_resume/ --format excel
    python segment_batch.py freshteams_resume/ --limit 10 --verbose
    python segment_batch.py data/ --extensions .pdf --parallel --workers 8
"""

import sys
import json
from pathlib import Path
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
import traceback

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.unified_resume_pipeline import UnifiedResumeParser
from src.core.section_learner import SectionLearner


def find_resume_files(
    directory: Path,
    extensions: List[str],
    limit: Optional[int] = None
) -> List[Path]:
    """
    Recursively find all resume files in directory
    
    Args:
        directory: Root directory to search
        extensions: List of file extensions (e.g., ['.pdf', '.docx'])
        limit: Maximum number of files to find
        
    Returns:
        List of file paths
    """
    files = []
    
    for ext in extensions:
        pattern = f"**/*{ext}"
        found = list(directory.glob(pattern))
        files.extend(found)
        
        if limit and len(files) >= limit:
            break
    
    # Remove duplicates and sort
    files = sorted(set(files))
    
    # Apply limit
    if limit:
        files = files[:limit]
    
    return files


def process_single_file(
    file_path: Path,
    use_ocr: bool,
    use_embeddings: bool,
    save_debug: bool,
    verbose: bool
) -> Dict[str, Any]:
    """
    Process a single resume file (for parallel processing)
    
    Returns:
        Dictionary with processing results
    """
    try:
        parser = UnifiedResumeParser(
            use_ocr_if_scanned=use_ocr,
            use_embeddings=use_embeddings,
            save_debug=save_debug,
            verbose=False  # Disable verbose in parallel mode
        )
        
        result = parser.parse(str(file_path))
        
        return {
            'file_path': str(file_path),
            'file_name': file_path.name,
            'success': result.success,
            'result': result.to_dict(include_debug=save_debug),
            'error': result.error
        }
    except Exception as e:
        return {
            'file_path': str(file_path),
            'file_name': file_path.name,
            'success': False,
            'result': None,
            'error': str(e)
        }


def save_batch_to_json(results: List[Dict], output_path: Path):
    """Save batch results to JSON"""
    try:
        output_data = {
            'metadata': {
                'total_files': len(results),
                'successful': sum(1 for r in results if r['success']),
                'failed': sum(1 for r in results if not r['success']),
                'timestamp': datetime.now().isoformat(),
                'version': '2.0.0'
            },
            'results': results
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Saved JSON to: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Error saving JSON: {e}")
        return False


def save_batch_to_excel(results: List[Dict], output_path: Path):
    """Save batch results to Excel with multiple sheets"""
    try:
        import pandas as pd
        
        # Sheet 1: Summary
        summary_rows = []
        for r in results:
            if r['success']:
                result_data = r['result']
                stats = result_data.get('statistics', {})
                
                summary_row = {
                    'File Name': r['file_name'],
                    'File Path': r['file_path'],
                    'Success': 'Yes',
                    'Pages': stats.get('total_pages', 0),
                    'Words': stats.get('total_words', 0),
                    'Sections': stats.get('total_sections', 0),
                    'Unknown Sections': stats.get('unknown_sections_count', 0),
                    'Processing Time (s)': result_data.get('metadata', {}).get('processing_time', 0)
                }
            else:
                summary_row = {
                    'File Name': r['file_name'],
                    'File Path': r['file_path'],
                    'Success': 'No',
                    'Error': r.get('error', 'Unknown error')
                }
            
            summary_rows.append(summary_row)
        
        summary_df = pd.DataFrame(summary_rows)
        
        # Sheet 2: Detailed sections
        section_rows = []
        for r in results:
            if not r['success']:
                continue
            
            result_data = r['result']
            sections = result_data.get('sections', [])
            
            for section in sections:
                section_row = {
                    'File Name': r['file_name'],
                    'Section Name': section.get('section_name', ''),
                    'Page': section.get('page', 0) + 1,
                    'Column': section.get('column_id', 0) + 1,
                    'Line Count': section.get('line_count', 0),
                    'Content Length': len(section.get('content', '')),
                    'Content Preview': section.get('content', '')[:200],
                    'Full Content': section.get('content', '')
                }
                section_rows.append(section_row)
        
        sections_df = pd.DataFrame(section_rows)
        
        # Sheet 3: Unknown sections
        unknown_rows = []
        for r in results:
            if not r['success']:
                continue
            
            result_data = r['result']
            unknowns = result_data.get('unknown_sections', [])
            
            for unk in unknowns:
                unknown_row = {
                    'File Name': r['file_name'],
                    'Section Name': unk.get('section_name', ''),
                    'Reason': unk.get('reason', ''),
                    'Confidence': unk.get('confidence', 0),
                    'Similar To': unk.get('similar_to', '')
                }
                unknown_rows.append(unknown_row)
        
        unknowns_df = pd.DataFrame(unknown_rows) if unknown_rows else pd.DataFrame()
        
        # Write to Excel
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            sections_df.to_excel(writer, sheet_name='Sections', index=False)
            if not unknowns_df.empty:
                unknowns_df.to_excel(writer, sheet_name='Unknown Sections', index=False)
        
        print(f"\n💾 Saved Excel to: {output_path}")
        print(f"   📊 Sheets: Summary, Sections" + (", Unknown Sections" if not unknowns_df.empty else ""))
        return True
        
    except ImportError:
        print("❌ Error: pandas and openpyxl required for Excel export")
        print("   Install with: pip install pandas openpyxl")
        return False
    except Exception as e:
        print(f"❌ Error saving Excel: {e}")
        traceback.print_exc()
        return False


def print_progress(current: int, total: int, file_name: str, success: bool):
    """Print progress update"""
    percent = (current / total) * 100
    status = "✅" if success else "❌"
    print(f"\r[{current}/{total}] ({percent:.1f}%) {status} {file_name[:50]:<50}", end='', flush=True)


def main():
    parser = argparse.ArgumentParser(
        description="Batch segment multiple resumes in a directory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python segment_batch.py freshteams_resume/
  python segment_batch.py freshteams_resume/ --format excel
  python segment_batch.py freshteams_resume/ --limit 10 --verbose
  python segment_batch.py data/ --extensions .pdf --parallel --workers 8
        """
    )
    
    parser.add_argument('directory', help='Directory containing resume files')
    parser.add_argument('--output-dir', '-o', default='batch_results', 
                       help='Output directory (default: batch_results)')
    parser.add_argument('--format', choices=['json', 'excel', 'both'], default='both',
                       help='Output format (default: both)')
    parser.add_argument('--extensions', nargs='+', default=['.pdf', '.docx'],
                       help='File extensions to process (default: .pdf .docx)')
    parser.add_argument('--limit', type=int, help='Limit number of files to process')
    parser.add_argument('--debug', action='store_true', help='Include debug information')
    parser.add_argument('--no-ocr', action='store_true', help='Disable OCR')
    parser.add_argument('--no-embeddings', action='store_true', help='Disable embeddings')
    parser.add_argument('--verbose', action='store_true', help='Verbose output per file')
    parser.add_argument('--learn', action='store_true', help='Enable section learning')
    parser.add_argument('--parallel', action='store_true', help='Process in parallel')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers')
    
    args = parser.parse_args()
    
    # Validate directory
    input_dir = Path(args.directory)
    if not input_dir.exists():
        print(f"❌ Error: Directory not found: {input_dir}")
        sys.exit(1)
    
    if not input_dir.is_dir():
        print(f"❌ Error: Not a directory: {input_dir}")
        sys.exit(1)
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("="*70)
    print("BATCH RESUME SEGMENTER v2.0")
    print("="*70)
    
    # Find files
    print(f"\n🔍 Searching for resume files in: {input_dir}")
    print(f"   Extensions: {', '.join(args.extensions)}")
    
    files = find_resume_files(input_dir, args.extensions, args.limit)
    
    if not files:
        print("❌ No resume files found!")
        sys.exit(1)
    
    print(f"\n✅ Found {len(files)} resume files")
    if args.limit:
        print(f"   (Limited to {args.limit} files)")
    
    # Process files
    print(f"\n🔄 Processing resumes...")
    print(f"   Mode: {'Parallel' if args.parallel else 'Sequential'}")
    if args.parallel:
        print(f"   Workers: {args.workers}")
    
    start_time = time.time()
    results = []
    
    if args.parallel:
        # Parallel processing
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(
                    process_single_file,
                    file_path,
                    not args.no_ocr,
                    not args.no_embeddings,
                    args.debug,
                    args.verbose
                ): file_path
                for file_path in files
            }
            
            for i, future in enumerate(as_completed(futures), 1):
                file_path = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    print_progress(i, len(files), file_path.name, result['success'])
                except Exception as e:
                    results.append({
                        'file_path': str(file_path),
                        'file_name': file_path.name,
                        'success': False,
                        'result': None,
                        'error': str(e)
                    })
                    print_progress(i, len(files), file_path.name, False)
    else:
        # Sequential processing
        resume_parser = UnifiedResumeParser(
            use_ocr_if_scanned=not args.no_ocr,
            use_embeddings=not args.no_embeddings,
            save_debug=args.debug,
            verbose=args.verbose
        )
        
        for i, file_path in enumerate(files, 1):
            try:
                if args.verbose:
                    print(f"\n\n{'='*70}")
                    print(f"[{i}/{len(files)}] Processing: {file_path.name}")
                    print('='*70)
                
                result = resume_parser.parse(str(file_path))
                
                results.append({
                    'file_path': str(file_path),
                    'file_name': file_path.name,
                    'success': result.success,
                    'result': result.to_dict(include_debug=args.debug),
                    'error': result.error
                })
                
                if not args.verbose:
                    print_progress(i, len(files), file_path.name, result.success)
                
            except Exception as e:
                results.append({
                    'file_path': str(file_path),
                    'file_name': file_path.name,
                    'success': False,
                    'result': None,
                    'error': str(e)
                })
                
                if not args.verbose:
                    print_progress(i, len(files), file_path.name, False)
    
    print()  # New line after progress
    
    processing_time = time.time() - start_time
    
    # Statistics
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    
    print("\n" + "="*70)
    print("BATCH PROCESSING COMPLETE")
    print("="*70)
    print(f"\n📊 Statistics:")
    print(f"   Total files: {len(results)}")
    print(f"   Successful: {successful} ({successful/len(results)*100:.1f}%)")
    print(f"   Failed: {failed}")
    print(f"   Total time: {processing_time:.2f}s")
    print(f"   Average time per file: {processing_time/len(results):.2f}s")
    
    # Show failures
    if failed > 0:
        print(f"\n❌ Failed files:")
        for r in results:
            if not r['success']:
                print(f"   - {r['file_name']}: {r.get('error', 'Unknown error')}")
    
    # Section learning
    if args.learn and successful > 0:
        print(f"\n" + "="*70)
        print("SECTION LEARNING")
        print("="*70)
        
        learner = SectionLearner(auto_save=False)
        
        # Observe all sections from all resumes
        for r in results:
            if r['success']:
                sections = r['result'].get('sections', [])
                for section in sections:
                    learner.observe_section(section.get('section_name', ''))
        
        # Print learning report
        learner.print_learning_report()
        
        # Auto-apply suggestions
        suggestions = learner.get_learning_suggestions()
        if suggestions:
            print("\n💡 Apply these suggestions? (y/n): ", end='')
            response = input().strip().lower()
            if response == 'y':
                learner.apply_suggestions(suggestions)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if args.format in ['json', 'both']:
        json_path = output_dir / f"batch_results_{timestamp}.json"
        save_batch_to_json(results, json_path)
    
    if args.format in ['excel', 'both']:
        excel_path = output_dir / f"batch_results_{timestamp}.xlsx"
        save_batch_to_excel(results, excel_path)
    
    print(f"\n✅ All results saved to: {output_dir}/")
    print("\n💡 Tip: Use view_results.py to interactively explore the results")
    print("\n")


if __name__ == "__main__":
    main()
