#!/usr/bin/env python3
"""
Quick Resume Parser - Simple CLI tool
Usage: python quick_parse.py <resume_file>
"""

import sys
import json
from pathlib import Path

# Import parser
from src.core.complete_resume_parser import CompleteResumeParser

# Import text extractors
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


def extract_text(file_path: str) -> str:
    """Extract text from file"""
    path = Path(file_path)
    ext = path.suffix.lower()
    
    if ext == '.txt':
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    elif ext == '.pdf':
        if not PDF_AVAILABLE:
            raise ImportError("PyPDF2 not installed. Install with: pip install PyPDF2")
        with open(path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = []
            for page in reader.pages:
                text.append(page.extract_text())
            return '\n'.join(text)
    
    elif ext == '.docx':
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx not installed. Install with: pip install python-docx")
        doc = Document(path)
        return '\n'.join([para.text for para in doc.paragraphs])
    
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def print_result(result: dict):
    """Pretty print the parsing result"""
    print()
    print("=" * 80)
    print("📄 RESUME PARSING RESULT")
    print("=" * 80)
    print()
    
    # Personal Info
    print("👤 PERSONAL INFORMATION")
    print("-" * 80)
    print(f"Name:     {result.get('name') or '❌ Not found'}")
    print(f"Email:    {result.get('email') or '❌ Not found'}")
    print(f"Mobile:   {result.get('mobile') or '❌ Not found'}")
    print(f"Location: {result.get('location') or '❌ Not found'}")
    print()
    
    # Professional Summary
    print("💼 PROFESSIONAL SUMMARY")
    print("-" * 80)
    print(f"Primary Role:      {result.get('primary_role') or '❌ Not found'}")
    print(f"Total Experience:  {result.get('total_experience_years', 0)} years")
    print(f"Companies Worked:  {len(result.get('experiences', []))}")
    print()
    
    # Work Experience
    experiences = result.get('experiences', [])
    if experiences:
        print("🏢 WORK EXPERIENCE")
        print("-" * 80)
        for i, exp in enumerate(experiences, 1):
            print(f"\n{i}. {exp.get('company_name', 'Unknown Company')}")
            print(f"   Role:     {exp.get('role', 'Not specified')}")
            print(f"   Period:   {exp.get('from_date', '?')} - {exp.get('to_date', '?')}")
            
            if exp.get('duration_months'):
                years = exp['duration_months'] // 12
                months = exp['duration_months'] % 12
                duration_str = f"{years}y {months}m" if years > 0 else f"{months}m"
                print(f"   Duration: {duration_str}")
            
            skills = exp.get('skills', [])
            if skills:
                # Show first 8 skills
                skills_display = skills[:8]
                skills_str = ', '.join(skills_display)
                if len(skills) > 8:
                    skills_str += f" ... (+{len(skills) - 8} more)"
                print(f"   Skills:   {skills_str}")
    else:
        print("🏢 WORK EXPERIENCE")
        print("-" * 80)
        print("❌ No work experience extracted")
    
    print()
    print("=" * 80)


def main():
    if len(sys.argv) < 2:
        print("Usage: python quick_parse.py <resume_file>")
        print("\nExample:")
        print("  python quick_parse.py resume.pdf")
        print("  python quick_parse.py resume.docx")
        print("  python quick_parse.py resume.txt")
        sys.exit(1)
    
    resume_file = sys.argv[1]
    
    # Check if file exists
    if not Path(resume_file).exists():
        print(f"❌ Error: File not found: {resume_file}")
        sys.exit(1)
    
    print()
    print("=" * 80)
    print("🚀 QUICK RESUME PARSER")
    print("=" * 80)
    print()
    print(f"📁 File: {resume_file}")
    print()
    
    # Initialize parser
    print("⏳ Initializing parser...")
    try:
        parser = CompleteResumeParser(model_path="ml_model")
    except Exception as e:
        print(f"❌ Error loading parser: {e}")
        print("\n💡 Make sure:")
        print("   1. The ml_model folder exists")
        print("   2. spaCy model is installed: python -m spacy download en_core_web_sm")
        sys.exit(1)
    
    # Extract text
    print("⏳ Extracting text from file...")
    try:
        text = extract_text(resume_file)
    except Exception as e:
        print(f"❌ Error extracting text: {e}")
        sys.exit(1)
    
    if len(text.strip()) < 50:
        print("⚠️  Warning: Extracted text is very short. File may be empty or corrupted.")
    
    # Parse resume
    print("⏳ Parsing resume...")
    try:
        result = parser.parse_resume(text, filename=Path(resume_file).name)
    except Exception as e:
        print(f"❌ Error parsing resume: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Display result
    print_result(result)
    
    # Option to save JSON
    print("💾 Save as JSON? (y/n): ", end='')
    try:
        choice = input().strip().lower()
        if choice == 'y':
            output_file = Path(resume_file).stem + "_parsed.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved to: {output_file}")
    except (EOFError, KeyboardInterrupt):
        print("\n👋 Skipping JSON export")
    
    print()
    print("=" * 80)
    print("✅ PARSING COMPLETED!")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
