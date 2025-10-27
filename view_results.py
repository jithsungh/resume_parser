#!/usr/bin/env python3
"""
Results Viewer
==============
Interactive viewer for batch segmentation results.

Usage:
    python view_results.py <results_file>
    
Supports:
    - JSON files (batch_results_*.json)
    - Excel files (batch_results_*.xlsx)

Features:
    - Summary statistics
    - File-by-file navigation
    - Section content preview
    - Search and filter
    - Export specific results
"""

import sys
import json
from pathlib import Path
import argparse
from typing import Dict, Any, List, Optional


def load_json_results(file_path: Path) -> Dict[str, Any]:
    """Load results from JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


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


def print_file_details(result: Dict[str, Any], index: int, total: int):
    """Print details for a single file"""
    print("\n" + "="*70)
    print(f"FILE {index + 1}/{total}")
    print("="*70)
    print(f"\n📄 {result['file_name']}")
    print(f"   Path: {result['file_path']}")
    
    if not result['success']:
        print(f"\n❌ Error: {result.get('error', 'Unknown')}")
        return
    
    result_data = result.get('result', {})
    stats = result_data.get('statistics', {})
    
    print(f"\n📊 Statistics:")
    print(f"   Pages: {stats.get('total_pages', 0)}")
    print(f"   Words: {stats.get('total_words', 0):,}")
    print(f"   Sections: {stats.get('total_sections', 0)}")
    
    sections = result_data.get('sections', [])
    
    print(f"\n📑 Sections ({len(sections)}):")
    for i, section in enumerate(sections, 1):
        print(f"\n   [{i}] {section.get('section_name', 'Unknown')}")
        print(f"       Page {section.get('page', 0) + 1}, Column {section.get('column_id', 0) + 1}")
        print(f"       Lines: {section.get('line_count', 0)}")
        
        content = section.get('content', '')
        preview = content[:150].replace('\n', ' ').strip()
        if len(content) > 150:
            preview += "..."
        print(f"       Preview: {preview}")


def interactive_mode(data: Dict[str, Any]):
    """Interactive browsing mode"""
    results = data.get('results', [])
    
    if not results:
        print("No results to display")
        return
    
    current_index = 0
    
    while True:
        print_file_details(results[current_index], current_index, len(results))
        
        print("\n" + "-"*70)
        print("Commands: [n]ext, [p]revious, [j]ump N, [s]earch, [q]uit")
        print("-"*70)
        
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
            print("  n, next     - Next file")
            print("  p, previous - Previous file")
            print("  j, jump N   - Jump to file N")
            print("  s, search   - Search by filename")
            print("  q, quit     - Exit")
        
        else:
            print("Unknown command. Type 'h' for help.")


def main():
    parser = argparse.ArgumentParser(
        description="View batch segmentation results",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('results_file', help='Results file (JSON or Excel)')
    parser.add_argument('--summary-only', action='store_true', 
                       help='Show summary only, no interactive mode')
    parser.add_argument('--file-index', type=int, 
                       help='Show specific file by index (1-based)')
    
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
    
    # Show specific file
    if args.file_index is not None:
        results = data.get('results', [])
        idx = args.file_index - 1  # Convert to 0-based
        
        if 0 <= idx < len(results):
            print_file_details(results[idx], idx, len(results))
        else:
            print(f"\n❌ Error: Invalid file index. Range: 1-{len(results)}")
        
        return
    
    # Interactive mode (unless summary only)
    if not args.summary_only:
        interactive_mode(data)


if __name__ == "__main__":
    main()
