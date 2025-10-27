#!/usr/bin/env python3
"""
Results Viewer
==============
Interactive viewer for batch segmentation results with PDF preview support.

Usage:
    python view_results.py <results_file>
    python view_results.py <single_resume_json>  # View single resume
    
Supports:
    - JSON files (batch_results_*.json or single_resume_*.json)
    - Excel files (batch_results_*.xlsx)
    - PDF preview (optional, requires PyMuPDF)

Features:
    - Summary statistics
    - File-by-file navigation
    - Section content with full text
    - Side-by-side PDF viewing (if available)
    - Search and filter
    - Export specific results
    - Detect missing/unknown sections
"""

import sys
import json
from pathlib import Path
import argparse
from typing import Dict, Any, List, Optional
import os

# Optional PDF support
try:
    import fitz  # PyMuPDF
    HAS_PDF_SUPPORT = True
except ImportError:
    HAS_PDF_SUPPORT = False


def load_json_results(file_path: Path) -> Dict[str, Any]:
    """Load results from JSON file (supports both batch and single resume format)"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle list format (old segmentation output)
    if isinstance(data, list):
        # Convert list to batch format
        results = []
        for item in data:
            if isinstance(item, dict):
                # Extract file info
                file_path = item.get('file_path', item.get('filename', 'unknown'))
                file_name = Path(file_path).name if file_path != 'unknown' else 'unknown'
                
                results.append({
                    'file_name': file_name,
                    'file_path': file_path,
                    'success': True,  # Assume success if in list
                    'result': item,
                    'error': None
                })
        
        return {
            'metadata': {
                'total_files': len(results),
                'successful': len(results),
                'failed': 0,
                'timestamp': None,
                'version': 'legacy'
            },
            'results': results
        }
    
    # Check if it's a single resume JSON (has 'file_path' at root)
    if 'file_path' in data and 'sections' in data:
        # Convert single resume to batch format
        return {
            'metadata': {
                'total_files': 1,
                'successful': 1 if data.get('metadata', {}).get('success', True) else 0,
                'failed': 0 if data.get('metadata', {}).get('success', True) else 1,
                'timestamp': data.get('metadata', {}).get('timestamp'),
                'version': data.get('metadata', {}).get('pipeline_version', '2.0.0')
            },
            'results': [{
                'file_name': data.get('file_name', Path(data['file_path']).name),
                'file_path': data.get('file_path'),
                'success': data.get('metadata', {}).get('success', True),
                'result': data,
                'error': data.get('metadata', {}).get('error')
            }]
        }
    
    # Batch format with metadata
    if 'results' in data:
        return data
    
    # Unknown format - try to handle gracefully
    print("⚠️  Unknown JSON format, attempting to parse...")
    return {
        'metadata': {
            'total_files': 1,
            'successful': 1,
            'failed': 0,
            'timestamp': None,
            'version': 'unknown'
        },
        'results': [{
            'file_name': 'unknown',
            'file_path': 'unknown',
            'success': True,
            'result': data,
            'error': None
        }]
    }


def load_excel_results(file_path: Path) -> Dict[str, Any]:
    """Load results from Excel file"""
    try:
        import pandas as pd
        
        # Read summary sheet
        summary_df = pd.read_excel(file_path, sheet_name='Summary')
        sections_df = pd.read_excel(file_path, sheet_name='Sections')
        
        # Convert to format similar to JSON
        results = []
        
        for _, row in summary_df.iterrows():
            if row['Success'] == 'Yes':
                # Get sections for this file
                file_sections = sections_df[sections_df['File Name'] == row['File Name']]
                
                sections = []
                for _, sec_row in file_sections.iterrows():
                    sections.append({
                        'section_name': sec_row['Section Name'],
                        'page': sec_row['Page'] - 1,
                        'column_id': sec_row['Column'] - 1,
                        'line_count': sec_row['Line Count'],
                        'content': sec_row.get('Full Content', '')
                    })
                
                results.append({
                    'file_name': row['File Name'],
                    'file_path': row['File Path'],
                    'success': True,
                    'result': {
                        'statistics': {
                            'total_pages': row.get('Pages', 0),
                            'total_words': row.get('Words', 0),
                            'total_sections': row.get('Sections', 0)
                        },
                        'sections': sections
                    }
                })
            else:
                results.append({
                    'file_name': row['File Name'],
                    'file_path': row['File Path'],
                    'success': False,
                    'error': row.get('Error', 'Unknown')
                })
        
        return {
            'metadata': {
                'total_files': len(results),
                'successful': sum(1 for r in results if r['success']),
                'failed': sum(1 for r in results if not r['success'])
            },
            'results': results
        }
        
    except ImportError:
        print("❌ Error: pandas required to read Excel files")
        print("   Install with: pip install pandas openpyxl")
        sys.exit(1)


def print_summary(data: Dict[str, Any]):
    """Print summary statistics"""
    metadata = data.get('metadata', {})
    
    print("\n" + "="*70)
    print("BATCH RESULTS SUMMARY")
    print("="*70)
    print(f"\nTotal files: {metadata.get('total_files', 0)}")
    print(f"Successful: {metadata.get('successful', 0)}")
    print(f"Failed: {metadata.get('failed', 0)}")
    
    if metadata.get('timestamp'):
        print(f"Timestamp: {metadata['timestamp']}")
    
    # Section statistics
    results = data.get('results', [])
    if results:
        all_sections = []
        for r in results:
            if r.get('success'):
                result_data = r.get('result', {})
                sections = result_data.get('sections', [])
                all_sections.extend([s.get('section_name', '') for s in sections])
        
        if all_sections:
            from collections import Counter
            section_counts = Counter(all_sections)
            
            print(f"\n📊 Most Common Sections:")
            for section, count in section_counts.most_common(10):
                print(f"   {section}: {count} times")


def print_file_details(result: Dict[str, Any], index: int, total: int, show_full_content: bool = False):
    """Print details for a single file with enhanced visualization"""
    print("\n" + "="*80)
    print(f"FILE {index + 1}/{total}")
    print("="*80)
    print(f"\n📄 {result['file_name']}")
    print(f"   Path: {result['file_path']}")
    
    if not result['success']:
        print(f"\n❌ Error: {result.get('error', 'Unknown')}")
        return
    
    result_data = result.get('result', {})
    stats = result_data.get('statistics', {})
    doc_type = result_data.get('document_type', {})
    
    # Document info
    print(f"\n📋 Document Info:")
    print(f"   Type: {doc_type.get('file_type', 'unknown').upper()}")
    print(f"   Scanned: {'Yes' if doc_type.get('is_scanned') else 'No'}")
    print(f"   Extraction: {doc_type.get('recommended_extraction', 'text').upper()}")
    
    print(f"\n📊 Statistics:")
    print(f"   Pages: {stats.get('total_pages', 0)}")
    print(f"   Words: {stats.get('total_words', 0):,}")
    print(f"   Columns: {stats.get('total_columns', 0)}")
    print(f"   Lines: {stats.get('total_lines', 0)}")
    print(f"   Sections: {stats.get('total_sections', 0)}")
    print(f"   Unknown Sections: {stats.get('unknown_sections_count', 0)}")
    
    # Layout info
    layouts = result_data.get('layouts', [])
    if layouts:
        print(f"\n📐 Layout Detection:")
        for layout in layouts:
            print(f"   Page {layout.get('page', 0) + 1}: {layout.get('type', 'unknown')} ({layout.get('num_columns', 0)} columns)")
    
    # Sections
    sections = result_data.get('sections', [])
    unknown_sections = result_data.get('unknown_sections', [])
    
    print(f"\n📑 Sections ({len(sections)}):")
    print("-" * 80)
    
    for i, section in enumerate(sections, 1):
        section_name = section.get('section_name', 'Unknown')
        is_unknown = any(u.get('section_name') == section_name for u in unknown_sections)
        
        # Header
        marker = "⚠️" if is_unknown else "✓"
        print(f"\n{marker} [{i}] {section_name}")
        print(f"   📍 Page {section.get('page', 0) + 1}, Column {section.get('column_id', 0) + 1}")
        print(f"   📏 {section.get('line_count', 0)} lines")
        
        # Content
        content = section.get('content', '')
        full_text = section.get('full_text', content)
        
        if show_full_content:
            print(f"\n   Content:")
            for line in full_text.split('\n'):
                print(f"   │ {line}")
        else:
            preview = content[:200].replace('\n', ' ║ ').strip()
            if len(content) > 200:
                preview += "..."
            print(f"   Preview: {preview}")
    
    # Unknown sections
    if unknown_sections:
        print(f"\n⚠️  Unknown/Ambiguous Sections ({len(unknown_sections)}):")
        print("-" * 80)
        for u in unknown_sections:
            print(f"   • '{u.get('section_name')}': {u.get('reason')}")
            if u.get('similar_to'):
                print(f"     Similar to: '{u.get('similar_to')}' (confidence: {u.get('confidence', 0):.0%})")
    
    # Processing metadata
    metadata = result_data.get('metadata', {})
    if metadata.get('processing_time'):
        print(f"\n⏱️  Processing Time: {metadata['processing_time']:.2f}s")


def show_pdf_preview(pdf_path: str, page_num: int = 0):
    """Show PDF preview (text extraction)"""
    if not HAS_PDF_SUPPORT:
        print("\n⚠️  PDF preview not available (install PyMuPDF: pip install pymupdf)")
        return
    
    if not os.path.exists(pdf_path):
        print(f"\n⚠️  PDF not found: {pdf_path}")
        return
    
    try:
        doc = fitz.open(pdf_path)
        
        if page_num >= len(doc):
            print(f"\n⚠️  Page {page_num + 1} not found (total pages: {len(doc)})")
            doc.close()
            return
        
        page = doc[page_num]
        text = page.get_text()
        
        print(f"\n📄 PDF Preview - Page {page_num + 1}/{len(doc)}")
        print("=" * 80)
        print(text[:2000])  # Show first 2000 chars
        if len(text) > 2000:
            print("\n... (truncated)")
        print("=" * 80)
        
        doc.close()
    except Exception as e:
        print(f"\n⚠️  Error loading PDF: {e}")


def export_section_to_file(result: Dict[str, Any], section_index: int, output_dir: Path):
    """Export a specific section to a text file"""
    result_data = result.get('result', {})
    sections = result_data.get('sections', [])
    
    if 0 <= section_index < len(sections):
        section = sections[section_index]
        section_name = section.get('section_name', 'Unknown').replace(' ', '_').replace('/', '_')
        file_name = result['file_name'].replace('.pdf', '').replace('.docx', '')
        
        output_file = output_dir / f"{file_name}_{section_name}.txt"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Section: {section.get('section_name')}\n")
            f.write(f"File: {result['file_name']}\n")
            f.write(f"Page: {section.get('page', 0) + 1}\n")
            f.write(f"Column: {section.get('column_id', 0) + 1}\n")
            f.write(f"Lines: {section.get('line_count', 0)}\n")
            f.write("\n" + "=" * 80 + "\n\n")
            f.write(section.get('full_text', section.get('content', '')))
        
        print(f"\n✅ Exported to: {output_file}")
    else:
        print(f"\n❌ Invalid section index")


def interactive_mode(data: Dict[str, Any]):
    """Enhanced interactive browsing mode"""
    results = data.get('results', [])
    
    if not results:
        print("No results to display")
        return
    
    current_index = 0
    show_full = False
    
    while True:
        print_file_details(results[current_index], current_index, len(results), show_full_content=show_full)
        
        print("\n" + "-"*80)
        print("Commands:")
        print("  [n]ext, [p]revious, [j]ump N, [s]earch, [f]ull toggle, [v]iew PDF")
        print("  [e]xport section N, [d]etails, [q]uit")
        print("-"*80)
        
        try:
            cmd = input("\n> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break
        
        if not cmd:
            continue
        
        if cmd == 'q' or cmd == 'quit':
            break
        
        elif cmd == 'n' or cmd == 'next':
            if current_index < len(results) - 1:
                current_index += 1
            else:
                print("Already at last file")
        
        elif cmd == 'p' or cmd == 'prev' or cmd == 'previous':
            if current_index > 0:
                current_index -= 1
            else:
                print("Already at first file")
        
        elif cmd == 'f' or cmd == 'full':
            show_full = not show_full
            print(f"Full content display: {'ON' if show_full else 'OFF'}")
        
        elif cmd.startswith('v') or cmd.startswith('view'):
            # View PDF
            result = results[current_index]
            pdf_path = result.get('file_path', '')
            
            # Ask for page number
            try:
                page_input = input("Enter page number (default=1): ").strip()
                page_num = int(page_input) - 1 if page_input else 0
            except ValueError:
                page_num = 0
            
            show_pdf_preview(pdf_path, page_num)
        
        elif cmd.startswith('e') or cmd.startswith('export'):
            # Export section
            try:
                parts = cmd.split()
                if len(parts) > 1:
                    section_idx = int(parts[1]) - 1
                else:
                    section_idx = int(input("Enter section number: ").strip()) - 1
                
                output_dir = Path("exported_sections")
                export_section_to_file(results[current_index], section_idx, output_dir)
            except (ValueError, IndexError) as e:
                print(f"❌ Error: {e}")
        
        elif cmd.startswith('d') or cmd.startswith('details'):
            # Show debug details
            result = results[current_index]
            result_data = result.get('result', {})
            
            print("\n" + "="*80)
            print("DEBUG DETAILS")
            print("="*80)
            
            # Show layouts
            layouts = result_data.get('layouts', [])
            print(f"\nLayouts: {len(layouts)}")
            for layout in layouts:
                print(f"  {json.dumps(layout, indent=2)}")
            
            # Show unknown sections
            unknown = result_data.get('unknown_sections', [])
            print(f"\nUnknown Sections: {len(unknown)}")
            for u in unknown:
                print(f"  {json.dumps(u, indent=2)}")
        
        elif cmd.startswith('j') or cmd.startswith('jump'):
            try:
                parts = cmd.split()
                if len(parts) > 1:
                    target = int(parts[1]) - 1  # 1-based to 0-based
                    if 0 <= target < len(results):
                        current_index = target
                    else:
                        print(f"Invalid index. Range: 1-{len(results)}")
                else:
                    print("Usage: jump <number>")
            except ValueError:
                print("Invalid number")
        
        elif cmd == 's' or cmd == 'search':
            query = input("Search in file names: ").strip().lower()
            matches = [
                (i, r) for i, r in enumerate(results)
                if query in r['file_name'].lower()
            ]
            
            if matches:
                print(f"\nFound {len(matches)} matches:")
                for i, (idx, r) in enumerate(matches[:10], 1):
                    print(f"  {i}. [{idx+1}] {r['file_name']}")
                
                if len(matches) > 10:
                    print(f"  ... and {len(matches) - 10} more")
                
                try:
                    choice = input("\nJump to (number or press Enter to cancel): ").strip()
                    if choice:
                        choice_idx = int(choice) - 1
                        if 0 <= choice_idx < len(matches):
                            current_index = matches[choice_idx][0]
                except ValueError:
                    pass
            else:
                print("No matches found")
        
        elif cmd == 'h' or cmd == 'help':
            print("\nCommands:")
            print("  n, next       - Next file")
            print("  p, previous   - Previous file")
            print("  j, jump N     - Jump to file N")
            print("  s, search     - Search by filename")
            print("  f, full       - Toggle full content display")
            print("  v, view       - View PDF page")
            print("  e, export N   - Export section N to file")
            print("  d, details    - Show debug details")
            print("  q, quit       - Exit")
        
        else:
            print("Unknown command. Type 'h' for help.")


def main():
    parser = argparse.ArgumentParser(
        description="View batch or single resume segmentation results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # View batch results interactively
  python view_results.py outputs/batch_results_20251027.json
  
  # View single resume
  python view_results.py freshteams_resume/Resumes/Resume_segmented.json
  
  # View specific file from batch
  python view_results.py outputs/batch_results.json --file-index 5
  
  # Show summary only
  python view_results.py outputs/batch_results.xlsx --summary-only
  
  # Full content display
  python view_results.py resume.json --full-content
        """
    )
    
    parser.add_argument('results_file', help='Results file (JSON or Excel)')
    parser.add_argument('--summary-only', action='store_true', 
                       help='Show summary only, no interactive mode')
    parser.add_argument('--file-index', type=int, 
                       help='Show specific file by index (1-based)')
    parser.add_argument('--full-content', action='store_true',
                       help='Show full section content instead of preview')
    parser.add_argument('--export-all', type=str, metavar='DIR',
                       help='Export all sections to directory')
    
    args = parser.parse_args()
    
    # Load results
    results_path = Path(args.results_file)
    
    if not results_path.exists():
        print(f"❌ Error: File not found: {results_path}")
        sys.exit(1)
    
    print(f"📂 Loading results from: {results_path.name}")
    
    if results_path.suffix.lower() == '.json':
        data = load_json_results(results_path)
    elif results_path.suffix.lower() in ['.xlsx', '.xls']:
        data = load_excel_results(results_path)
    else:
        print(f"❌ Error: Unsupported file type: {results_path.suffix}")
        print("   Supported: .json, .xlsx")
        sys.exit(1)
    
    # Print summary
    print_summary(data)
    
    # Export all sections if requested
    if args.export_all:
        export_dir = Path(args.export_all)
        export_dir.mkdir(parents=True, exist_ok=True)
        
        results = data.get('results', [])
        total_exported = 0
        
        for result in results:
            if result.get('success'):
                result_data = result.get('result', {})
                sections = result_data.get('sections', [])
                for i in range(len(sections)):
                    export_section_to_file(result, i, export_dir)
                    total_exported += 1
        
        print(f"\n✅ Exported {total_exported} sections to {export_dir}")
        return
    
    # Show specific file
    if args.file_index is not None:
        results = data.get('results', [])
        idx = args.file_index - 1  # Convert to 0-based
        
        if 0 <= idx < len(results):
            print_file_details(results[idx], idx, len(results), show_full_content=args.full_content)
        else:
            print(f"\n❌ Error: Invalid file index. Range: 1-{len(results)}")
        
        return
    
    # Interactive mode (unless summary only)
    if not args.summary_only:
        interactive_mode(data)


if __name__ == "__main__":
    main()
