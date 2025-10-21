"""
Batch Resume Parser
Process multiple resumes from a folder and export to Excel/CSV
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime

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

from src.core.complete_resume_parser import CompleteResumeParser


class BatchResumeProcessor:
    """Process multiple resume files in batch"""
    
    def __init__(self, model_path: str):
        """Initialize with model path"""
        print("🚀 Initializing Batch Resume Processor...")
        self.parser = CompleteResumeParser(model_path)
        print("✅ Ready to process resumes!\n")
    
    def process_folder(self, folder_path: str, 
                      output_file: str = None,
                      file_extensions: List[str] = None) -> pd.DataFrame:
        """
        Process all resumes in a folder
        
        Args:
            folder_path: Path to folder containing resumes
            output_file: Output Excel/CSV file path
            file_extensions: List of extensions to process (default: .pdf, .docx, .txt)
            
        Returns:
            DataFrame with parsed resume data
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
                    continue
                
                # Parse resume
                result = self.parser.parse_resume(text, filename=file_path.name)
                
                # Add metadata
                result['filename'] = file_path.name
                result['file_path'] = str(file_path)
                
                results.append(result)
                
                print(f"   ✅ Parsed: {result.get('name', 'Unknown')} - {result.get('primary_role', 'N/A')}")
                
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
                continue
        
        print(f"\n✅ Successfully processed {len(results)}/{len(resume_files)} resumes\n")
        
        # Convert to DataFrame
        df = self._create_dataframe(results)
        
        # Save to file
        if output_file:
            self._save_results(df, output_file)
        
        return df
    
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
                    text.append(page.extract_text())
                return '\n'.join(text)
        except Exception as e:
            raise ValueError(f"Error reading PDF: {e}")
    
    def _extract_from_docx(self, file_path: Path) -> str:
        """Extract text from DOCX"""
        try:
            doc = Document(file_path)
            text = []
            for para in doc.paragraphs:
                text.append(para.text)
            return '\n'.join(text)
        except Exception as e:
            raise ValueError(f"Error reading DOCX: {e}")
    
    def _create_dataframe(self, results: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convert results to DataFrame with flattened structure"""
        rows = []
        
        for result in results:
            # Flatten experience data
            exp_companies = []
            exp_roles = []
            exp_periods = []
            exp_skills = []
            
            for exp in result.get('experiences', []):
                exp_companies.append(exp.get('company_name', ''))
                exp_roles.append(exp.get('role', ''))
                period = f"{exp.get('from_date', '')} - {exp.get('to_date', '')}"
                exp_periods.append(period)
                exp_skills.append(', '.join(exp.get('skills', [])))
            
            row = {
                'Name': result.get('name'),
                'Email': result.get('email'),
                'Mobile': result.get('mobile'),
                'Location': result.get('location'),
                'Total Experience (Years)': result.get('total_experience_years'),
                'Primary Role': result.get('primary_role'),
                'Number of Companies': len(result.get('experiences', [])),
                'Companies': ' | '.join(exp_companies),
                'Roles': ' | '.join(exp_roles),
                'Periods': ' | '.join(exp_periods),
                'All Skills': ' | '.join(exp_skills),
                'Filename': result.get('filename'),
                'File Path': result.get('file_path')
            }
            
            rows.append(row)
        
        return pd.DataFrame(rows)
    
    def _save_results(self, df: pd.DataFrame, output_file: str):
        """Save results to Excel or CSV"""
        output_path = Path(output_file)
        ext = output_path.suffix.lower()
        
        print(f"💾 Saving results to: {output_file}")
        
        if ext == '.xlsx':
            df.to_excel(output_file, index=False, engine='openpyxl')
        elif ext == '.csv':
            df.to_csv(output_file, index=False, encoding='utf-8')
        else:
            raise ValueError(f"Unsupported output format: {ext}")
        
        print(f"✅ Results saved successfully!")


def main():
    parser = argparse.ArgumentParser(description='Batch Resume Parser')
    parser.add_argument('folder', help='Folder containing resumes')
    parser.add_argument('--model', default='ml_model', help='Path to NER model')
    parser.add_argument('--output', help='Output file (Excel or CSV)')
    parser.add_argument('--extensions', nargs='+', default=['.pdf', '.docx', '.txt'],
                       help='File extensions to process')
    
    args = parser.parse_args()
    
    # Generate default output filename if not provided
    if not args.output:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = f'resume_results_{timestamp}.xlsx'
    
    print("=" * 80)
    print("📊 BATCH RESUME PARSER")
    print("=" * 80)
    print()
    
    # Initialize processor
    try:
        processor = BatchResumeProcessor(args.model)
    except Exception as e:
        print(f"❌ Error initializing processor: {e}")
        return
    
    # Process resumes
    try:
        df = processor.process_folder(
            args.folder,
            output_file=args.output,
            file_extensions=args.extensions
        )
        
        print()
        print("=" * 80)
        print("📈 SUMMARY STATISTICS")
        print("=" * 80)
        print(f"Total Resumes Processed: {len(df)}")
        print(f"Resumes with Email:      {df['Email'].notna().sum()}")
        print(f"Resumes with Mobile:     {df['Mobile'].notna().sum()}")
        print(f"Resumes with Location:   {df['Location'].notna().sum()}")
        print()
        print(f"Average Experience:      {df['Total Experience (Years)'].mean():.1f} years")
        print(f"Top Roles:")
        if 'Primary Role' in df.columns:
            role_counts = df['Primary Role'].value_counts().head(5)
            for role, count in role_counts.items():
                print(f"   - {role}: {count}")
        
        print()
        print("=" * 80)
        print("✅ BATCH PROCESSING COMPLETED!")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
