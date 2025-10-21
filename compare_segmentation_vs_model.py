"""
Segmentation vs Model Comparison Tool
======================================
Compare segmentation output with NER model predictions to identify the problem source.
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime
import traceback

# Import both pipelines
try:
    from src.PDF_pipeline.segment_sections import segment_resume
    SEGMENT_AVAILABLE = True
except ImportError:
    SEGMENT_AVAILABLE = False
    print("⚠️  Segmentation module not available")

try:
    from src.core.complete_resume_parser import CompleteResumeParser
    PARSER_AVAILABLE = True
except ImportError:
    PARSER_AVAILABLE = False
    print("⚠️  Parser module not available")

# PDF/DOCX extraction
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


class ComparisonTool:
    """Compare segmentation vs model output"""
    
    def __init__(self, model_path: str):
        """Initialize with model path"""
        print("🔍 Initializing Comparison Tool...")
        
        if not SEGMENT_AVAILABLE:
            raise ImportError("Segmentation module not available")
        
        if not PARSER_AVAILABLE:
            raise ImportError("Parser module not available")
        
        self.parser = CompleteResumeParser(model_path)
        print("✅ Comparison tool ready!\n")
    
    def compare_file(self, file_path: str) -> Dict[str, Any]:
        """Compare segmentation vs model output for a single file"""
        
        file_path = Path(file_path)
        print(f"📄 Processing: {file_path.name}")
        
        # Extract text
        text = self._extract_text_from_file(str(file_path))
        
        if not text or len(text.strip()) < 50:
            return {
                'filename': file_path.name,
                'status': 'error',
                'error': 'File empty or too short'
            }
        
        # Get segmentation
        print("   🔸 Running segmentation...")
        try:
            segments = segment_resume(text)
            segment_success = True
            segment_error = None
        except Exception as e:
            segments = {}
            segment_success = False
            segment_error = str(e)
        
        # Get model output
        print("   🔸 Running NER model...")
        try:
            parsed = self.parser.parse_resume(text, filename=file_path.name)
            model_success = True
            model_error = None
        except Exception as e:
            parsed = {}
            model_success = True
            model_error = str(e)
        
        # Compare results
        comparison = {
            'filename': file_path.name,
            'file_path': str(file_path),
            'text_length': len(text),
            'text_preview': text[:500].replace('\n', ' ')[:300],
            
            # Segmentation results
            'segmentation': {
                'success': segment_success,
                'error': segment_error,
                'sections_found': list(segments.keys()) if segments else [],
                'section_count': len(segments) if segments else 0,
                'sections': self._format_segments(segments)
            },
            
            # Model results
            'model': {
                'success': model_success,
                'error': model_error,
                'name': parsed.get('name'),
                'email': parsed.get('email'),
                'mobile': parsed.get('mobile'),
                'location': parsed.get('location'),
                'total_experience': parsed.get('total_experience_years'),
                'primary_role': parsed.get('primary_role'),
                'experience_count': len(parsed.get('experiences', []))
            },
            
            # Analysis
            'analysis': self._analyze_comparison(segments, parsed, text)
        }
        
        print(f"   ✅ Comparison complete\n")
        return comparison
    
    def compare_folder(self, 
                      folder_path: str,
                      output_file: Optional[str] = None,
                      file_extensions: List[str] = None,
                      limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Compare all files in a folder"""
        
        if file_extensions is None:
            file_extensions = ['.pdf', '.docx', '.txt']
        
        folder = Path(folder_path)
        if not folder.exists():
            raise ValueError(f"Folder not found: {folder_path}")
        
        # Find files
        resume_files = []
        for ext in file_extensions:
            resume_files.extend(folder.glob(f'**/*{ext}'))
        
        if limit:
            resume_files = resume_files[:limit]
        
        print(f"📁 Found {len(resume_files)} resume files")
        print(f"📂 Processing from: {folder_path}\n")
        
        # Compare each file
        results = []
        for i, file_path in enumerate(resume_files, 1):
            print(f"[{i}/{len(resume_files)}]")
            try:
                result = self.compare_file(str(file_path))
                results.append(result)
            except Exception as e:
                print(f"   ❌ Error: {e}\n")
                results.append({
                    'filename': file_path.name,
                    'status': 'error',
                    'error': str(e)
                })
        
        # Save results
        if output_file:
            self._save_comparison(results, output_file)
        
        return results
    
    def _extract_text_from_file(self, file_path: str) -> str:
        """Extract text from file"""
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
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
            return '\n'.join(text)
    
    def _extract_from_docx(self, file_path: Path) -> str:
        """Extract text from DOCX"""
        doc = Document(file_path)
        text = []
        for para in doc.paragraphs:
            if para.text.strip():
                text.append(para.text)
        return '\n'.join(text)
    
    def _format_segments(self, segments: Dict[str, str]) -> List[Dict[str, Any]]:
        """Format segments for output"""
        formatted = []
        for name, content in segments.items():
            formatted.append({
                'name': name,
                'length': len(content),
                'preview': content[:200].replace('\n', ' ') + '...' if content else '',
                'line_count': len(content.split('\n')) if content else 0
            })
        return formatted
    
    def _analyze_comparison(self, 
                          segments: Dict[str, str], 
                          parsed: Dict[str, Any],
                          full_text: str) -> Dict[str, Any]:
        """Analyze the comparison to identify issues"""
        
        issues = []
        recommendations = []
        
        # Check if Experience section was found
        has_experience = any('experience' in s.lower() for s in segments.keys())
        parsed_experiences = len(parsed.get('experiences', []))
        
        if not has_experience:
            issues.append("No Experience section found in segmentation")
            recommendations.append("Check section detection patterns - Experience section missing")
        
        if has_experience and parsed_experiences == 0:
            issues.append("Experience section found but NER extracted 0 experiences")
            recommendations.append("Issue is likely in NER model - segmentation looks OK")
        
        # Check if contact info sections exist
        has_contact = any(s in segments for s in ['Contact Information', 'Summary'])
        if not has_contact and not parsed.get('email') and not parsed.get('mobile'):
            issues.append("No contact sections found and no contact info extracted")
            recommendations.append("Check text extraction and section detection")
        
        # Check section count
        if len(segments) < 2:
            issues.append(f"Very few sections detected ({len(segments)})")
            recommendations.append("Segmentation may be too aggressive or patterns are wrong")
        
        # Check if name was extracted
        if not parsed.get('name'):
            issues.append("Name not extracted")
            recommendations.append("Check name extraction logic and text format")
        
        # Overall assessment
        if len(segments) == 0:
            assessment = "CRITICAL: Segmentation completely failed"
        elif len(segments) > 0 and parsed_experiences == 0:
            assessment = "Segmentation OK, Model extraction failed"
        elif len(segments) > 0 and parsed_experiences > 0:
            assessment = "Both segmentation and model working"
        else:
            assessment = "Partial success - needs investigation"
        
        return {
            'assessment': assessment,
            'issues': issues,
            'recommendations': recommendations,
            'segment_count': len(segments),
            'has_experience_section': has_experience,
            'extracted_experiences': parsed_experiences
        }
    
    def _save_comparison(self, results: List[Dict[str, Any]], output_file: str):
        """Save comparison results"""
        
        # Save detailed JSON
        json_file = output_file if output_file.endswith('.json') else f"{output_file}.json"
        print(f"\n💾 Saving detailed comparison to: {json_file}")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"✅ JSON saved!")
        
        # Save summary CSV
        csv_file = output_file.replace('.json', '.csv') if '.json' in output_file else f"{output_file}.csv"
        print(f"💾 Saving summary to: {csv_file}")
        
        summary_rows = []
        for r in results:
            seg = r.get('segmentation', {})
            model = r.get('model', {})
            analysis = r.get('analysis', {})
            
            summary_rows.append({
                'Filename': r.get('filename'),
                'Assessment': analysis.get('assessment', ''),
                'Sections Found': seg.get('section_count', 0),
                'Section Names': ', '.join(seg.get('sections_found', [])),
                'Has Experience Section': analysis.get('has_experience_section', False),
                'Extracted Name': model.get('name', ''),
                'Extracted Email': model.get('email', ''),
                'Extracted Mobile': model.get('mobile', ''),
                'Extracted Role': model.get('primary_role', ''),
                'Extracted Experiences': model.get('experience_count', 0),
                'Issues': ' | '.join(analysis.get('issues', [])),
                'Recommendations': ' | '.join(analysis.get('recommendations', []))
            })
        
        df = pd.DataFrame(summary_rows)
        df.to_csv(csv_file, index=False, encoding='utf-8')
        print(f"✅ CSV saved!")
        
        # Save Excel with multiple sheets
        excel_file = output_file.replace('.json', '.xlsx').replace('.csv', '.xlsx')
        if not excel_file.endswith('.xlsx'):
            excel_file = f"{output_file}.xlsx"
        
        print(f"💾 Saving Excel to: {excel_file}")
        
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            # Summary sheet
            df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Detailed segmentation
            seg_rows = []
            for r in results:
                for section in r.get('segmentation', {}).get('sections', []):
                    seg_rows.append({
                        'Filename': r.get('filename'),
                        'Section Name': section.get('name'),
                        'Length': section.get('length'),
                        'Lines': section.get('line_count'),
                        'Preview': section.get('preview')
                    })
            
            if seg_rows:
                pd.DataFrame(seg_rows).to_excel(writer, sheet_name='Segmentation', index=False)
        
        print(f"✅ Excel saved!")


def main():
    parser = argparse.ArgumentParser(
        description='Compare segmentation vs NER model output',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('input', help='Resume file or folder')
    parser.add_argument('--model', default='ml_model', help='Path to NER model')
    parser.add_argument('--output', '-o', help='Output filename base')
    parser.add_argument('--limit', type=int, help='Limit number of files to process')
    parser.add_argument('--extensions', nargs='+', default=['.pdf', '.docx', '.txt'])
    
    args = parser.parse_args()
    
    # Generate default output
    if not args.output:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = f'comparison_{timestamp}'
    
    print("=" * 80)
    print("🔍 SEGMENTATION vs MODEL COMPARISON")
    print("=" * 80)
    print()
    
    # Initialize
    try:
        tool = ComparisonTool(args.model)
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    # Process
    try:
        input_path = Path(args.input)
        
        if input_path.is_file():
            # Single file
            result = tool.compare_file(str(input_path))
            tool._save_comparison([result], args.output)
            
            # Print analysis
            print("\n" + "=" * 80)
            print("📊 ANALYSIS")
            print("=" * 80)
            analysis = result.get('analysis', {})
            print(f"\nAssessment: {analysis.get('assessment')}")
            if analysis.get('issues'):
                print("\n⚠️  Issues:")
                for issue in analysis['issues']:
                    print(f"  • {issue}")
            if analysis.get('recommendations'):
                print("\n💡 Recommendations:")
                for rec in analysis['recommendations']:
                    print(f"  • {rec}")
        
        elif input_path.is_dir():
            # Folder
            results = tool.compare_folder(
                str(input_path),
                output_file=args.output,
                file_extensions=args.extensions,
                limit=args.limit
            )
            
            # Print statistics
            print("\n" + "=" * 80)
            print("📊 OVERALL STATISTICS")
            print("=" * 80)
            
            assessments = {}
            for r in results:
                assessment = r.get('analysis', {}).get('assessment', 'Unknown')
                assessments[assessment] = assessments.get(assessment, 0) + 1
            
            print("\nAssessments:")
            for assessment, count in sorted(assessments.items(), key=lambda x: x[1], reverse=True):
                print(f"  • {assessment}: {count}")
            
            # Common issues
            all_issues = {}
            for r in results:
                for issue in r.get('analysis', {}).get('issues', []):
                    all_issues[issue] = all_issues.get(issue, 0) + 1
            
            if all_issues:
                print("\nMost Common Issues:")
                for issue, count in sorted(all_issues.items(), key=lambda x: x[1], reverse=True)[:5]:
                    print(f"  • {issue}: {count} times")
        
        else:
            print(f"❌ Invalid input: {args.input}")
            return 1
        
        print("\n" + "=" * 80)
        print("✅ COMPARISON COMPLETED!")
        print("=" * 80)
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
