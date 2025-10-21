#!/usr/bin/env python3
"""
Debug Resume Parser - Shows NER model output
Usage: python debug_parser.py <resume_file>
"""

import sys
from pathlib import Path

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

from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from transformers.utils import logging as transformers_logging

# Suppress transformers logging
transformers_logging.set_verbosity_error()


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


def extract_experience_section(text: str) -> str:
    """Extract the experience section"""
    import re
    
    headers = [
        r'(?:professional\s+)?(?:work\s+)?experience',
        r'employment\s+history',
        r'work\s+history',
        r'professional\s+background',
        r'career\s+history'
    ]
    
    text_lower = text.lower()
    
    # Find experience section start
    start_idx = -1
    for header in headers:
        match = re.search(header, text_lower)
        if match:
            start_idx = match.start()
            break
    
    if start_idx == -1:
        return text
    
    # Find next major section
    end_headers = [
        r'education',
        r'academic',
        r'qualifications',
        r'skills',
        r'technical\s+skills',
        r'certifications',
        r'projects',
        r'achievements'
    ]
    
    end_idx = len(text)
    for end_header in end_headers:
        match = re.search(end_header, text_lower[start_idx + 50:])
        if match:
            potential_end = start_idx + 50 + match.start()
            end_idx = min(end_idx, potential_end)
    
    return text[start_idx:end_idx]


def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_parser.py <resume_file>")
        sys.exit(1)
    
    resume_file = sys.argv[1]
    
    if not Path(resume_file).exists():
        print(f"❌ Error: File not found: {resume_file}")
        sys.exit(1)
    
    print()
    print("=" * 100)
    print("🔍 DEBUG RESUME PARSER - NER MODEL OUTPUT")
    print("=" * 100)
    print()
    print(f"📁 File: {resume_file}")
    print()
    
    # Load NER model
    print("⏳ Loading NER model...")
    model_path = "ml_model"
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForTokenClassification.from_pretrained(model_path)
    ner_pipeline = pipeline(
        "ner", 
        model=model, 
        tokenizer=tokenizer, 
        aggregation_strategy="simple"
    )
    print("✅ Model loaded")
    print()
    
    # Extract text
    print("⏳ Extracting text from file...")
    text = extract_text(resume_file)
    print(f"✅ Extracted {len(text)} characters")
    print()
    
    # Extract experience section
    print("⏳ Extracting experience section...")
    experience_text = extract_experience_section(text)
    print(f"✅ Experience section: {len(experience_text)} characters")
    print()
    
    # Show experience section preview
    print("=" * 100)
    print("📄 EXPERIENCE SECTION (First 500 chars)")
    print("=" * 100)
    print(experience_text[:500])
    print("..." if len(experience_text) > 500 else "")
    print()
    
    # Run NER
    print("=" * 100)
    print("🤖 RUNNING NER MODEL...")
    print("=" * 100)
    print()
    
    # Chunk the text
    max_chunk_size = 512
    chunks = [experience_text[i:i+max_chunk_size] 
              for i in range(0, len(experience_text), max_chunk_size)]
    
    print(f"Processing {len(chunks)} chunks...")
    print()
    
    all_entities = []
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
        print("-" * 100)
        
        try:
            chunk_results = ner_pipeline(chunk)
            
            if chunk_results:
                print(f"Found {len(chunk_results)} entities:")
                print()
                print(f"{'Entity Text':<40} | {'Type':<12} | {'Score':<8} | {'Start':<6} | {'End':<6}")
                print("-" * 100)
                
                for entity in chunk_results:
                    print(f"{entity['word']:<40} | {entity['entity_group']:<12} | "
                          f"{entity['score']:<8.3f} | {entity['start']:<6} | {entity['end']:<6}")
                    all_entities.append(entity)
            else:
                print("No entities found in this chunk")
            
            print()
        
        except Exception as e:
            print(f"❌ Error processing chunk: {e}")
            print()
    
    # Summary
    print()
    print("=" * 100)
    print("📊 SUMMARY")
    print("=" * 100)
    print()
    print(f"Total entities found: {len(all_entities)}")
    print()
    
    # Count by type
    from collections import Counter
    entity_counts = Counter(e['entity_group'] for e in all_entities)
    
    print("Entity counts by type:")
    for entity_type, count in entity_counts.most_common():
        print(f"  {entity_type:<15}: {count}")
    print()
    
    # Show all entities grouped by type
    print("=" * 100)
    print("📋 ALL ENTITIES GROUPED BY TYPE")
    print("=" * 100)
    print()
    
    for entity_type in ['COMPANY', 'ROLE', 'DATE', 'TECH']:
        entities_of_type = [e for e in all_entities if e['entity_group'] == entity_type]
        if entities_of_type:
            print(f"\n{entity_type} ({len(entities_of_type)} entities):")
            print("-" * 100)
            for entity in entities_of_type:
                print(f"  '{entity['word']:<40}' | Score: {entity['score']:.3f} | "
                      f"Pos: {entity['start']}-{entity['end']}")
    
    print()
    print("=" * 100)
    print("✅ DEBUG COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()
    