"""
Batch process resumes using NER pipeline
"""

import os
import sys
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from src.core.ner_pipeline import create_pipeline


def extract_text_from_file(file_path: str) -> str:
    """Extract text from PDF or DOCX file"""
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if ext == '.pdf':
            from src.PDF_pipeline.pdf_extractor import PDFExtractor
            extractor = PDFExtractor()
            return extractor.extract_text(file_path)
        elif ext in ['.docx', '.doc']:
            from src.DOCX_pipeline.docx_extractor import DOCXExtractor
            extractor = DOCXExtractor()
            return extractor.extract_text(file_path)
        else:
            # Try reading as text
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")
        return ""


def process_folder(folder_path: str, model_path: str, output_path: str):
    """
    Process all resumes in a folder
    
    Args:
        folder_path: Path to folder containing resumes
        model_path: Path to NER model
        output_path: Path to save output Excel/CSV
    """
    print("=" * 80)
    print("NER Resume Batch Processor")
    print("=" * 80)
    
    # Create pipeline
    print(f"\n1. Loading NER model from: {model_path}")
    parser = create_pipeline(model_path)
    print("   ✓ Model loaded successfully")
    
    # Find all resume files
    print(f"\n2. Scanning folder: {folder_path}")
    resume_files = []
    for ext in ['.pdf', '.docx', '.doc', '.txt']:
        resume_files.extend(Path(folder_path).glob(f'**/*{ext}'))
    
    print(f"   ✓ Found {len(resume_files)} resume files")
    
    if not resume_files:
        print("   ❌ No resume files found!")
        return
    
    # Process each resume
    results = []
    print(f"\n3. Processing resumes...")
    
    for idx, file_path in enumerate(resume_files, 1):
        print(f"\n   [{idx}/{len(resume_files)}] {file_path.name}")
        
        try:
            # Extract text
            text = extract_text_from_file(str(file_path))
            
            if not text or len(text.strip()) < 100:
                print(f"      ⚠️  Skipping - insufficient text")
                continue
            
            # Parse with NER
            result = parser.parse_resume(text)
            
            # Add metadata
            result['file_name'] = file_path.name
            result['file_path'] = str(file_path)
            
            results.append(result)
            
            # Print summary
            name = result.get('name', 'N/A')
            role = result.get('primary_role', 'N/A')
            exp_years = result.get('total_experience_years', 0)
            num_companies = len(result.get('experiences', []))
            
            print(f"      ✓ {name} | {role} | {exp_years}y exp | {num_companies} companies")
            
        except Exception as e:
            print(f"      ❌ Error: {e}")
            results.append({
                'file_name': file_path.name,
                'file_path': str(file_path),
                'error': str(e),
                'name': None,
                'email': None,
                'mobile': None,
                'experiences': []
            })
    
    # Save results
    print(f"\n4. Saving results to: {output_path}")
    save_results(results, output_path)
    print("   ✓ Results saved successfully")
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total files processed: {len(resume_files)}")
    print(f"Successful parses: {len([r for r in results if not r.get('error')])}")
    print(f"Errors: {len([r for r in results if r.get('error')])}")
    print("=" * 80)


def save_results(results: List[Dict], output_path: str):
    """Save results to Excel with multiple sheets"""
    
    # Prepare main data
    main_data = []
    for result in results:
        row = {
            'File Name': result.get('file_name'),
            'Name': result.get('name'),
            'Email': result.get('email'),
            'Mobile': result.get('mobile'),
            'Location': result.get('location'),
            'Total Experience (Years)': result.get('total_experience_years'),
            'Primary Role': result.get('primary_role'),
            'Number of Companies': len(result.get('experiences', [])),
            'Error': result.get('error', '')
        }
        main_data.append(row)
    
    # Prepare detailed experience data
    experience_data = []
    for result in results:
        name = result.get('name', 'Unknown')
        file_name = result.get('file_name')
        
        for exp in result.get('experiences', []):
            row = {
                'Candidate Name': name,
                'File Name': file_name,
                'Company': exp.get('company_name'),
                'Role': exp.get('role'),
                'From': exp.get('from'),
                'To': exp.get('to'),
                'Duration (Months)': exp.get('duration_months'),
                'Skills': ', '.join(exp.get('skills', []))
            }
            experience_data.append(row)
    
    # Create DataFrames
    df_main = pd.DataFrame(main_data)
    df_experience = pd.DataFrame(experience_data)
    
    # Save to Excel
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df_main.to_excel(writer, sheet_name='Summary', index=False)
        df_experience.to_excel(writer, sheet_name='Detailed Experience', index=False)
    
    # Also save JSON for complete data
    json_path = output_path.replace('.xlsx', '.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch process resumes with NER model')
    parser.add_argument('--folder', required=True, help='Folder containing resumes')
    parser.add_argument('--model', default='ml_model', help='Path to NER model')
    parser.add_argument('--output', default='outputs/ner_batch_results.xlsx', 
                       help='Output Excel file path')
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.exists(args.folder):
        print(f"Error: Folder not found: {args.folder}")
        sys.exit(1)
    
    if not os.path.exists(args.model):
        print(f"Error: Model not found: {args.model}")
        sys.exit(1)
    
    # Create output directory
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # Process
    process_folder(args.folder, args.model, args.output)


if __name__ == "__main__":
    main()
