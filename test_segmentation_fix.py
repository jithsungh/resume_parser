"""
Quick test to verify segmentation fix
"""

import sys
from pathlib import Path
from src.PDF_pipeline.get_words import get_words_from_pdf
from src.PDF_pipeline.split_columns import split_columns
from src.PDF_pipeline.get_lines import get_column_wise_lines
from src.PDF_pipeline.segment_sections import segment_sections_from_columns

# Test with one of the problematic resumes
resume_file = Path("freshteams_resume/Golang Developer/AnirudhReddy_Resume.pdf")

if not resume_file.exists():
    print(f"❌ Resume not found: {resume_file}")
    sys.exit(1)

print(f"🧪 Testing segmentation fix on: {resume_file.name}\n")

# Extract with layout analysis
print("1️⃣  Extracting words...")
pages = get_words_from_pdf(str(resume_file))
print(f"   ✅ Extracted {len(pages)} pages")

print("\n2️⃣  Splitting columns...")
columns = split_columns(pages, min_words_per_column=10, dynamic_min_words=True)
print(f"   ✅ Found {len(columns)} columns")

print("\n3️⃣  Building lines...")
columns_with_lines = get_column_wise_lines(columns, y_tolerance=1.0)
print(f"   ✅ Built lines for {len(columns_with_lines)} columns")

print("\n4️⃣  Segmenting sections...")
result = segment_sections_from_columns(columns_with_lines)

# Analyze results
sections_found = [s.get('section') for s in result.get('sections', [])]
print(f"\n✅ Found {len(sections_found)} sections:")
for section in sections_found:
    print(f"   - {section}")

# Check Experience section specifically
print("\n" + "="*70)
print("🔍 CHECKING EXPERIENCE SECTION")
print("="*70)

for section in result.get('sections', []):
    if section.get('section') == 'Experience':
        lines = section.get('lines', [])
        print(f"\n📊 Experience Section:")
        print(f"   Lines: {len(lines)}")
        print(f"\n   First 10 lines:")
        for i, line in enumerate(lines[:10], 1):
            text = line.get('text', '')[:100]
            print(f"      [{i}] {text}")
        
        # Check if it contains work experience keywords
        all_text = ' '.join(line.get('text', '') for line in lines).lower()
        
        has_company = any(kw in all_text for kw in ['npci', 'national payments', 'associate', 'developer', 'intern'])
        has_education = any(kw in all_text for kw in ['b.tech', 'b tech', 'iiit', 'kerala blockchain academy'])
        
        print(f"\n   Analysis:")
        print(f"      Contains work experience keywords: {'✅' if has_company else '❌'}")
        print(f"      Contains education keywords: {'❌ WRONG!' if has_education else '✅ Good'}")
        
        if has_education:
            print(f"\n   ⚠️  WARNING: Experience section contains education content!")
            print(f"   This indicates the segmentation bug is still present.")
        else:
            print(f"\n   ✅ Experience section looks correct!")
        
        break
else:
    print("   ❌ No Experience section found!")

print("\n" + "="*70)
print("Test complete!")
