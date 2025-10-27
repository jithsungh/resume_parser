#!/usr/bin/env python3
"""
Single Resume Segmenter
========================
Segments a single resume file and displays the results.

Usage:
    python segment_single.py <resume_file> [options]
    
Options:
    --save-json         Save output to JSON file
    --save-excel        Save output to Excel file  
    --debug             Include debug information
    --no-ocr            Disable OCR for scanned PDFs
    --no-embeddings     Disable semantic embeddings
    --verbose           Show detailed progress

Examples:
    python segment_single.py resume.pdf
    python segment_single.py resume.pdf --save-json --debug
    python segment_single.py resume.docx --save-excel
"""

import sys
import json
from pathlib import Path
import argparse
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.unified_resume_pipeline import UnifiedResumeParser
from src.core.section_learner import SectionLearner


def save_to_json(result, output_path: str, include_debug: bool = False):
    """Save result to JSON file"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result.to_json(include_debug=include_debug, indent=2))
        print(f"\n💾 Saved JSON to: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Error saving JSON: {e}")
        return False


def save_to_excel(result, output_path: str):
    """Save result to Excel file"""
    try:
        import pandas as pd
        
        # Prepare data for Excel
        rows = []
        
        for section in result.sections:
            row = {
                'Section Name': section.section_name,
                'Page': section.page + 1,
                'Column': section.column_id + 1,
                'Line Count': len(section.content_lines),
                'Word Count': sum(line.word_count for line in section.content_lines),
                'Content Preview': section.content_text[:200] + '...' if len(section.content_text) > 200 else section.content_text,
                'Full Content': section.content_text
            }
            rows.append(row)
        
        # Create DataFrame
        df = pd.DataFrame(rows)
        
        # Save to Excel
        df.to_excel(output_path, index=False, engine='openpyxl')
        print(f"\n💾 Saved Excel to: {output_path}")
        return True
    except ImportError:
        print("❌ Error: pandas and openpyxl required for Excel export")
        print("   Install with: pip install pandas openpyxl")
        return False
    except Exception as e:
        print(f"❌ Error saving Excel: {e}")
        return False


def print_results(result):
    """Print formatted results to console"""
    print("\n" + "="*70)
    print("SEGMENTATION RESULTS")
    print("="*70)
    
    print(f"\n📄 File: {result.file_name}")
    print(f"📊 Statistics:")
    print(f"   - Type: {result.document_type.file_type.upper()}")
    print(f"   - Scanned: {'Yes' if result.document_type.is_scanned else 'No'}")
    print(f"   - Pages: {result.total_pages}")
    print(f"   - Words: {result.total_words:,}")
    print(f"   - Columns: {result.total_columns}")
    print(f"   - Lines: {result.total_lines}")
    print(f"   - Sections: {len(result.sections)}")
    print(f"   - Processing Time: {result.processing_time:.2f}s")
    
    # Layout info
    print(f"\n📐 Layout Detection:")
    for i, layout in enumerate(result.layouts):
        print(f"   Page {i+1}: {layout.type_name} ({layout.num_columns} columns)")
    
    # Sections
    print(f"\n📑 Sections Detected:")
    for i, section in enumerate(result.sections, 1):
        print(f"\n   [{i}] {section.section_name}")
        print(f"       Page: {section.page + 1}, Column: {section.column_id + 1}")
        print(f"       Lines: {len(section.content_lines)}")
        
        # Content preview
        preview = section.content_text[:150]
        if len(section.content_text) > 150:
            preview += "..."
        
        # Replace newlines for compact display
        preview = preview.replace('\n', ' ').strip()
        print(f"       Preview: {preview}")
    
    # Unknown sections
    if result.unknown_sections:
        print(f"\n⚠️  Unknown/Ambiguous Sections ({len(result.unknown_sections)}):")
        for unk in result.unknown_sections:
            print(f"   - '{unk.section.section_name}': {unk.reason}")
            if unk.similar_to:
                print(f"     (Similar to: {unk.similar_to})")
    
    print("\n" + "="*70)


def main():
    parser = argparse.ArgumentParser(
        description="Segment a single resume into sections",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python segment_single.py resume.pdf
  python segment_single.py resume.pdf --save-json --debug
  python segment_single.py resume.docx --save-excel --verbose
        """
    )
    
    parser.add_argument('resume_file', help='Path to resume file (PDF or DOCX)')
    parser.add_argument('--save-json', action='store_true', help='Save output to JSON')
    parser.add_argument('--save-excel', action='store_true', help='Save output to Excel')
    parser.add_argument('--output', '-o', help='Output file path (auto-generated if not specified)')
    parser.add_argument('--debug', action='store_true', help='Include debug information')
    parser.add_argument('--no-ocr', action='store_true', help='Disable OCR for scanned PDFs')
    parser.add_argument('--no-embeddings', action='store_true', help='Disable semantic embeddings')
    parser.add_argument('--verbose', action='store_true', help='Show detailed progress')
    parser.add_argument('--learn', action='store_true', help='Enable section learning')
    
    args = parser.parse_args()
    
    # Validate file
    resume_path = Path(args.resume_file)
    if not resume_path.exists():
        print(f"❌ Error: File not found: {resume_path}")
        sys.exit(1)
    
    if resume_path.suffix.lower() not in ['.pdf', '.docx', '.doc']:
        print(f"❌ Error: Unsupported file type: {resume_path.suffix}")
        print("   Supported: .pdf, .docx, .doc")
        sys.exit(1)
    
    print("="*70)
    print("SINGLE RESUME SEGMENTER v2.0")
    print("="*70)
    print(f"\n📂 Input: {resume_path.name}")
    
    # Create parser
    resume_parser = UnifiedResumeParser(
        use_ocr_if_scanned=not args.no_ocr,
        use_embeddings=not args.no_embeddings,
        save_debug=args.debug,
        verbose=args.verbose
    )
    
    # Parse resume
    print("\n🔄 Processing...")
    result = resume_parser.parse(str(resume_path))
    
    # Check success
    if not result.success:
        print(f"\n❌ Error: {result.error}")
        sys.exit(1)
    
    # Print results
    if not args.verbose:  # If verbose, already printed during processing
        print_results(result)
    
    # Learning (if enabled)
    if args.learn:
        print("\n" + "="*70)
        print("SECTION LEARNING")
        print("="*70)
        
        learner = SectionLearner(auto_save=True)
        
        # Observe sections
        for section in result.sections:
            learner.observe_section(section.section_name)
        
        # Print learning report
        learner.print_learning_report()
    
    # Save outputs
    if args.save_json or args.save_excel:
        # Determine output filename
        if args.output:
            output_base = Path(args.output).stem
            output_dir = Path(args.output).parent
        else:
            output_base = resume_path.stem + '_segmented'
            output_dir = resume_path.parent
        
        # Save JSON
        if args.save_json:
            json_path = output_dir / f"{output_base}.json"
            save_to_json(result, str(json_path), include_debug=args.debug)
        
        # Save Excel
        if args.save_excel:
            excel_path = output_dir / f"{output_base}.xlsx"
            save_to_excel(result, str(excel_path))
    
    print("\n✅ Done!\n")


if __name__ == "__main__":
    main()
