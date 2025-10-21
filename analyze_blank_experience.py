#!/usr/bin/env python3
"""
Analyze resumes with blank Experience sections
"""
import pandas as pd
import sys
from pathlib import Path

def main():
    # Try Excel file first, then CSV
    excel_path = Path("outputs/batch_results.xlsx")
    csv_path = Path("outputs/batch_sections_4 1(Sections).csv")
    
    if excel_path.exists():
        print(f"Reading from {excel_path}...")
        df = pd.read_excel(excel_path)
    elif csv_path.exists():
        print(f"Reading from {csv_path}...")
        # Read the CSV file with proper encoding handling
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(csv_path, encoding='latin-1')
            except:
                df = pd.read_csv(csv_path, encoding='cp1252')
    else:
        print(f"Error: No data file found")
        print(f"  Looked for: {excel_path}")
        print(f"  Looked for: {csv_path}")
        return 1
    
    # Check for resumes with blank/empty Experience column
    blank_exp = df[df['Experience'].isna() | (df['Experience'].str.strip() == '')]
    
    print(f'Total resumes: {len(df)}')
    print(f'Resumes with blank Experience: {len(blank_exp)}')
    print('\nResumes with blank Experience:')
    print('='*80)
    
    for idx, row in blank_exp.iterrows():
        filename = row['pdf_path'].split('/')[-1] if pd.notna(row['pdf_path']) else 'Unknown'
        print(f'{idx+1}. {filename}')
        
        # Check what sections ARE populated
        populated = []
        for col in df.columns:
            if col not in ['pdf_path', 'contact_info'] and pd.notna(row[col]) and str(row[col]).strip():
                populated.append(col)
        
        if populated:
            sections_str = ', '.join(populated[:5])
            print(f'   Has sections: {sections_str}')
        else:
            print(f'   WARNING: NO SECTIONS FOUND!')
        
        # Check Unknown Sections
        if 'Unknown Sections' in df.columns and pd.notna(row['Unknown Sections']):
            unknown = str(row['Unknown Sections']).strip()
            if unknown:
                lines = unknown.split('\n')[:3]
                print(f'   Unknown sections: {len(lines)} lines')
                for line in lines:
                    print(f'      {line[:60]}...' if len(line) > 60 else f'      {line}')
        print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
