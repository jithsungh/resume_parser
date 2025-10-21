"""
Batch Segmentation Debugger
============================
Process resumes and export detailed segmentation results for debugging.
Helps identify if parsing issues are due to segmentation or model problems.
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime
import traceback

# PDF/DOCX extraction
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("⚠️  PyPDF2 not available - PDF processing disabled")

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    print("⚠️  python-docx not available - DOCX processing disabled")

# Try to import segmentation module
try:
    from src.PDF_pipeline.segment_sections import segment_resume
    SEGMENT_AVAILABLE = True
except ImportError:
    SEGMENT_AVAILABLE = False
    print("⚠️  Segmentation module not available")


class SegmentationDebugger:
    """Debug resume segmentation to identify parsing issues"""
    
    def __init__(self):
        """Initialize debugger"""
        print("🔍 Initializing Segmentation Debugger...")
        if not SEGMENT_AVAILABLE:
            raise ImportError("Segmentation module not available. Check src/PDF_pipeline/segment_sections.py")
        print("✅ Ready to debug segmentation!\n")
    
    def process_folder(self, 
                      folder_path: str, 
                      output_format: str = 'json',
                      output_file: Optional[str] = None,
                      file_extensions: List[str] = None) -> List[Dict[str, Any]]:
        """
        Process all resumes in a folder and extract segmentation data
        
        Args:
            folder_path: Path to folder containing resumes
            output_format: 'json' or 'csv' or 'both'
            output_file: Base output filename (without extension)
            file_extensions: List of extensions to process
            
        Returns:
            List of segmentation results
        """
        if file_extensions is None:
            file_extensions = ['.pdf', '.docx', '.txt']
        
        folder = Path(folder_path)
        
        if not folder.exists():
            raise ValueError(f"Folder not found: {folder_path}")
        
        # Find all resume files
        resume_files = []
        for ext in file_extensions:
            resume_files.extend(folder.glob(f'**/*{ext}'))
        
        print(f"📁 Found {len(resume_files)} resume files")
        print(f"📂 Processing from: {folder_path}\n")
        
        # Process each resume
        results = []
        for i, file_path in enumerate(resume_files, 1):
            print(f"[{i}/{len(resume_files)}] Processing: {file_path.name}")
            
            try:
                # Extract text from file
                text = self._extract_text_from_file(str(file_path))
                
                if not text or len(text.strip()) < 50:
                    print(f"   ⚠️  Warning: File appears empty or too short")
                    result = {
                        'filename': file_path.name,
                        'file_path': str(file_path),
                        'status': 'empty',
                        'error': 'File appears empty or too short',
                        'text_length': len(text) if text else 0,
                        'sections': []
                    }
                    results.append(result)
                    continue
                
                # Segment resume
                segments = self._segment_resume(text, file_path.name)
                
                # Create debug result
                result = {
                    'filename': file_path.name,
                    'file_path': str(file_path),
                    'status': 'success',
                    'text_length': len(text),
                    'text_preview': text[:500].replace('\n', ' ')[:200] + '...',
                    'sections_found': list(segments.keys()) if segments else [],
                    'section_count': len(segments) if segments else 0,
                    'sections': self._format_sections(segments)
                }
                
                results.append(result)
                
                # Print summary
                if segments:
                    print(f"   ✅ Found {len(segments)} sections: {', '.join(segments.keys())}")
                else:
                    print(f"   ⚠️  No sections detected")
                
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
                result = {
                    'filename': file_path.name,
                    'file_path': str(file_path),
                    'status': 'error',
                    'error': str(e),
                    'error_traceback': traceback.format_exc(),
                    'sections': []
                }
                results.append(result)
                continue
        
        print(f"\n✅ Successfully processed {len(results)} resumes\n")
        
        # Save results
        if output_file:
            self._save_results(results, output_file, output_format)
        
        return results
    
    def _extract_text_from_file(self, file_path: str) -> str:
        """Extract text from PDF, DOCX, or TXT file"""
        file_path = Path(file_path)
        ext = file_path.suffix.lower()
        
        if ext == '.txt':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        
        elif ext == '.pdf' and PDF_AVAILABLE:
            return self._extract_from_pdf(file_path)
        
        elif ext == '.docx' and DOCX_AVAILABLE:
            return self._extract_from_docx(file_path)
        
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    
    def _extract_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF"""
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = []
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text.append(page_text)
                return '\n'.join(text)
        except Exception as e:
            raise ValueError(f"Error reading PDF: {e}")
    
    def _extract_from_docx(self, file_path: Path) -> str:
        """Extract text from DOCX"""
        try:
            doc = Document(file_path)
            text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    text.append(para.text)
            return '\n'.join(text)
        except Exception as e:
            raise ValueError(f"Error reading DOCX: {e}")
    
    def _segment_resume(self, text: str, filename: str) -> Dict[str, str]:
        """Segment resume into sections"""
        try:
            # Try to use the segment_resume function
            segments = segment_resume(text)
            return segments if segments else {}
        except Exception as e:
            print(f"   ⚠️  Segmentation error: {e}")
            # Fallback to basic segmentation
            return self._fallback_segmentation(text)
    
    def _fallback_segmentation(self, text: str) -> Dict[str, str]:
        """Basic fallback segmentation using pattern matching"""
        sections = {}
        
        # Common section patterns
        patterns = {
            'Experience': r'(?i)(experience|employment|work history)',
            'Education': r'(?i)(education|academic|qualification)',
            'Skills': r'(?i)(skills|technical|expertise|competencies)',
            'Summary': r'(?i)(summary|objective|profile|about)',
            'Projects': r'(?i)(projects|portfolio)',
            'Certifications': r'(?i)(certifications|certificates|licenses)'
        }
        
        lines = text.split('\n')
        current_section = 'Unsegmented'
        current_content = []
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # Check if line is a section header
            matched_section = None
            for section_name, pattern in patterns.items():
                if re.match(pattern, line_stripped):
                    matched_section = section_name
                    break
            
            if matched_section:
                # Save previous section
                if current_content:
                    sections[current_section] = '\n'.join(current_content)
                # Start new section
                current_section = matched_section
                current_content = []
            else:
                current_content.append(line)
        
        # Save last section
        if current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def _format_sections(self, segments: Dict[str, str]) -> List[Dict[str, Any]]:
        """Format sections for output"""
        formatted = []
        for section_name, content in segments.items():
            formatted.append({
                'section_name': section_name,
                'content_length': len(content),
                'content_preview': content[:300].replace('\n', ' ')[:200] + '...' if content else '',
                'line_count': len(content.split('\n')) if content else 0,
                'word_count': len(content.split()) if content else 0,
                'full_content': content  # Include full content for JSON export
            })
        return formatted
    
    def _save_results(self, results: List[Dict[str, Any]], 
                     output_file: str, 
                     output_format: str):
        """Save results to JSON and/or CSV"""
        
        # JSON output (detailed)
        if output_format in ['json', 'both']:
            json_file = output_file if output_file.endswith('.json') else f"{output_file}.json"
            print(f"💾 Saving detailed results to: {json_file}")
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            print(f"✅ JSON saved successfully!")
        
        # CSV output (summary)
        if output_format in ['csv', 'both']:
            csv_file = output_file if output_file.endswith('.csv') else f"{output_file}.csv"
            print(f"💾 Saving summary to: {csv_file}")
            
            # Flatten results for CSV
            csv_rows = []
            for result in results:
                sections_info = result.get('sections', [])
                
                row = {
                    'Filename': result.get('filename'),
                    'Status': result.get('status'),
                    'Text Length': result.get('text_length', 0),
                    'Section Count': result.get('section_count', 0),
                    'Sections Found': ', '.join(result.get('sections_found', [])),
                    'Error': result.get('error', ''),
                    'Text Preview': result.get('text_preview', '')
                }
                
                # Add section-level details
                for i, section in enumerate(sections_info[:10]):  # Limit to 10 sections
                    row[f'Section_{i+1}_Name'] = section.get('section_name', '')
                    row[f'Section_{i+1}_Length'] = section.get('content_length', 0)
                    row[f'Section_{i+1}_Preview'] = section.get('content_preview', '')
                
                csv_rows.append(row)
            
            df = pd.DataFrame(csv_rows)
            df.to_csv(csv_file, index=False, encoding='utf-8')
            
            print(f"✅ CSV saved successfully!")
        
        # Excel output with multiple sheets
        if output_format in ['excel', 'xlsx', 'both']:
            excel_file = output_file if output_file.endswith('.xlsx') else f"{output_file}.xlsx"
            print(f"💾 Saving to Excel: {excel_file}")
            
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                # Summary sheet
                summary_rows = []
                for result in results:
                    summary_rows.append({
                        'Filename': result.get('filename'),
                        'Status': result.get('status'),
                        'Text Length': result.get('text_length', 0),
                        'Section Count': result.get('section_count', 0),
                        'Sections Found': ', '.join(result.get('sections_found', [])),
                        'Error': result.get('error', '')
                    })
                
                df_summary = pd.DataFrame(summary_rows)
                df_summary.to_excel(writer, sheet_name='Summary', index=False)
                
                # Detailed sections sheet
                detail_rows = []
                for result in results:
                    for section in result.get('sections', []):
                        detail_rows.append({
                            'Filename': result.get('filename'),
                            'Section Name': section.get('section_name'),
                            'Content Length': section.get('content_length'),
                            'Line Count': section.get('line_count'),
                            'Word Count': section.get('word_count'),
                            'Preview': section.get('content_preview')
                        })
                
                if detail_rows:
                    df_details = pd.DataFrame(detail_rows)
                    df_details.to_excel(writer, sheet_name='Section Details', index=False)
            
            print(f"✅ Excel saved successfully!")


def main():
    parser = argparse.ArgumentParser(
        description='Batch Segmentation Debugger - Analyze resume segmentation issues',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process resumes and save to JSON
  python batch_segmentation_debugger.py resumes/ --output debug_results --format json
  
  # Process and save to CSV
  python batch_segmentation_debugger.py resumes/ --output debug_results --format csv
  
  # Process and save to both JSON and CSV
  python batch_segmentation_debugger.py resumes/ --output debug_results --format both
  
  # Process specific file types
  python batch_segmentation_debugger.py resumes/ --extensions .pdf .docx
        """
    )
    
    parser.add_argument('folder', help='Folder containing resumes')
    parser.add_argument('--output', '-o', help='Output filename (without extension)', 
                       default=None)
    parser.add_argument('--format', '-f', 
                       choices=['json', 'csv', 'excel', 'xlsx', 'both'], 
                       default='both',
                       help='Output format (default: both)')
    parser.add_argument('--extensions', nargs='+', 
                       default=['.pdf', '.docx', '.txt'],
                       help='File extensions to process (default: .pdf .docx .txt)')
    
    args = parser.parse_args()
    
    # Generate default output filename if not provided
    if not args.output:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = f'segmentation_debug_{timestamp}'
    
    print("=" * 80)
    print("🔍 BATCH SEGMENTATION DEBUGGER")
    print("=" * 80)
    print()
    print("This tool helps you debug resume parsing issues by showing:")
    print("  • Raw text extraction")
    print("  • Section segmentation results")
    print("  • Section boundaries and content")
    print("  • Parsing errors and warnings")
    print()
    print("=" * 80)
    print()
    
    # Initialize debugger
    try:
        debugger = SegmentationDebugger()
    except Exception as e:
        print(f"❌ Error initializing debugger: {e}")
        return 1
    
    # Process resumes
    try:
        results = debugger.process_folder(
            args.folder,
            output_format=args.format,
            output_file=args.output,
            file_extensions=args.extensions
        )
        
        # Print statistics
        print()
        print("=" * 80)
        print("📊 SEGMENTATION ANALYSIS")
        print("=" * 80)
        
        success_count = sum(1 for r in results if r.get('status') == 'success')
        error_count = sum(1 for r in results if r.get('status') == 'error')
        empty_count = sum(1 for r in results if r.get('status') == 'empty')
        
        print(f"\nTotal Files:         {len(results)}")
        print(f"Successfully Parsed: {success_count}")
        print(f"Empty/Too Short:     {empty_count}")
        print(f"Errors:              {error_count}")
        
        # Section statistics
        all_sections = {}
        for r in results:
            for section in r.get('sections_found', []):
                all_sections[section] = all_sections.get(section, 0) + 1
        
        if all_sections:
            print(f"\nSections Found:")
            for section, count in sorted(all_sections.items(), key=lambda x: x[1], reverse=True):
                print(f"  • {section}: {count} times")
        
        # Files with no sections
        no_sections = [r for r in results if r.get('section_count', 0) == 0]
        if no_sections:
            print(f"\n⚠️  Files with NO sections detected ({len(no_sections)}):")
            for r in no_sections[:10]:  # Show first 10
                print(f"  • {r['filename']}")
            if len(no_sections) > 10:
                print(f"  ... and {len(no_sections) - 10} more")
        
        # Files with errors
        if error_count > 0:
            print(f"\n❌ Files with errors ({error_count}):")
            for r in [r for r in results if r.get('status') == 'error'][:10]:
                print(f"  • {r['filename']}: {r.get('error', 'Unknown error')}")
        
        print()
        print("=" * 80)
        print("✅ SEGMENTATION DEBUGGING COMPLETED!")
        print("=" * 80)
        print()
        print("📝 Next Steps:")
        print("  1. Review the output files to understand segmentation")
        print("  2. Check files with no sections detected")
        print("  3. If segmentation looks good, the issue is likely in the NER model")
        print("  4. If segmentation is bad, improve section detection logic")
        print()
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
