#!/usr/bin/env python3
"""
Resume Parser CLI
=================
Command-line interface for resume parsing.

Usage:
    # Parse single resume
    python parse.py resume.pdf
    
    # Parse with verbose output
    python parse.py resume.pdf --verbose
    
    # Force specific strategy
    python parse.py resume.pdf --strategy pdf_histogram
    
    # Save output
    python parse.py resume.pdf --output result.json
    
    # Batch processing
    python parse.py --batch "resumes/*.pdf" --output outputs/
"""

import sys
import json
import argparse
from pathlib import Path

from src.core.parser import ResumeParser, ParserStrategy


def parse_single(args):
    """Parse a single resume"""
    parser = ResumeParser()
    
    # Parse strategy if provided
    strategy = None
    if args.strategy:
        try:
            strategy = ParserStrategy(args.strategy)
        except ValueError:
            print(f"Invalid strategy: {args.strategy}")
            print(f"Valid strategies: {[s.value for s in ParserStrategy]}")
            return 1
    
    result = parser.parse(
        file_path=args.input,
        force_strategy=strategy,
        verbose=args.verbose
    )
    
    if not result.success:
        print(f"❌ Parsing failed")
        if result.errors:
            print(f"Errors: {result.errors}")
        return 1
    
    # Print simplified JSON
    print("\n" + "="*70)
    print("RESULT")
    print("="*70)
    print(result.simplified_json)
    
    # Print summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Strategy: {result.strategy_used.value}")
    print(f"Quality: {result.quality_score:.1f}/100")
    print(f"Sections: {len(result.data.get('sections', []))}")
    print(f"Time: {result.processing_time:.2f}s")
    
    if result.warnings:
        print(f"\n⚠️  Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")
    
    # Save if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result.data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Saved to: {output_path}")
    
    return 0


def parse_batch(args):
    """Parse multiple resumes"""
    from batch_process import BatchProcessor
    
    # Collect files
    input_pattern = args.batch
    input_path = Path(input_pattern)
    
    if input_path.is_dir():
        files = [
            str(f) for f in input_path.rglob("*")
            if f.suffix.lower() in ['.pdf', '.docx']
        ]
    else:
        # Glob pattern
        files = [str(f) for f in Path.cwd().glob(input_pattern)]
    
    if not files:
        print(f"❌ No files found matching: {input_pattern}")
        return 1
    
    print(f"Found {len(files)} files to process\n")
    
    # Process
    processor = BatchProcessor(
        output_dir=args.output or "outputs/batch",
        max_workers=args.workers
    )
    
    summary = processor.process_batch(
        file_paths=files,
        save_individual=True,
        save_summary=True,
        enable_learning=not args.no_learning,
        verbose=args.verbose
    )
    
    return 0 if summary['statistics']['success_count'] > 0 else 1


def main():
    parser = argparse.ArgumentParser(
        description="Parse resumes with automatic strategy selection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse single resume
  python parse.py resume.pdf
  
  # Parse with verbose output
  python parse.py resume.pdf --verbose
  
  # Force specific strategy
  python parse.py resume.pdf --strategy pdf_histogram
  
  # Save output
  python parse.py resume.pdf --output result.json
  
  # Batch processing
  python parse.py --batch "resumes/*.pdf"
  python parse.py --batch resumes/ --output outputs/
        """
    )
    
    # Input
    parser.add_argument(
        "input",
        nargs="?",
        help="Resume file to parse (PDF or DOCX)"
    )
    
    parser.add_argument(
        "--batch",
        help="Batch mode: glob pattern or directory"
    )
    
    # Options
    parser.add_argument(
        "--strategy",
        choices=[s.value for s in ParserStrategy],
        help="Force specific parsing strategy"
    )
    
    parser.add_argument(
        "--output",
        "-o",
        help="Output file path (single mode) or directory (batch mode)"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    
    # Batch options
    parser.add_argument(
        "--workers",
        type=int,
        help="Number of parallel workers (batch mode)"
    )
    
    parser.add_argument(
        "--no-learning",
        action="store_true",
        help="Disable self-learning (batch mode)"
    )
    
    args = parser.parse_args()
    
    # Validate
    if not args.input and not args.batch:
        parser.print_help()
        return 1
    
    if args.input and args.batch:
        print("❌ Cannot use both single and batch mode")
        return 1
    
    # Route
    if args.batch:
        return parse_batch(args)
    else:
        return parse_single(args)


if __name__ == "__main__":
    sys.exit(main())
