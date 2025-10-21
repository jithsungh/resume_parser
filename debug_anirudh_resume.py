"""
Debug specific resume (AnirudhReddy) to understand segmentation issue
"""

import json
from pathlib import Path
from src.PDF_pipeline.get_words import get_words_from_pdf
from src.PDF_pipeline.split_columns import split_columns
from src.PDF_pipeline.get_lines import get_column_wise_lines
from src.PDF_pipeline.segment_sections import segment_sections_from_columns, simple_json

# Find the AnirudhReddy resume
resume_folder = Path("freshteams_resume/Golang Developer")
resume_file = resume_folder / "AnirudhReddy_Resume.pdf"

if not resume_file.exists():
    print(f"❌ Resume not found: {resume_file}")
    exit(1)

print(f"🔍 Debugging: {resume_file.name}\n")

# Step 1: Extract words
print("1️⃣  Extracting words from PDF...")
pages = get_words_from_pdf(str(resume_file))
print(f"   ✅ Extracted {len(pages)} pages")

# Step 2: Split into columns
print("\n2️⃣  Splitting into columns...")
columns = split_columns(pages, min_words_per_column=10, dynamic_min_words=True)
print(f"   ✅ Found {len(columns)} columns")

# Step 3: Build lines
print("\n3️⃣  Building lines...")
columns_with_lines = get_column_wise_lines(columns, y_tolerance=1.0)
print(f"   ✅ Built lines for {len(columns_with_lines)} columns")

# Step 4: Segment sections
print("\n4️⃣  Segmenting sections...")
data = segment_sections_from_columns(columns_with_lines)
print(f"   ✅ Found {len(data.get('sections', []))} sections")

# Print results
print("\n" + "="*70)
print("📊 SEGMENTATION RESULTS")
print("="*70)

for section in data.get('sections', []):
    section_name = section.get('section', 'Unknown')
    lines = section.get('lines', [])
    
    print(f"\n🏷️  Section: {section_name}")
    print(f"   Lines: {len(lines)}")
    
    # Show first 5 lines
    print(f"   Content (first 5 lines):")
    for i, line in enumerate(lines[:5]):
        text = line.get('text', '')[:80]
        print(f"      [{i+1}] {text}")
    
    if len(lines) > 5:
        print(f"      ... ({len(lines) - 5} more lines)")

# Also show simplified JSON
print("\n" + "="*70)
print("📄 SIMPLIFIED JSON")
print("="*70)
print(simple_json(data))

# Save detailed output
output_file = "debug_anirudh_segmentation.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"\n💾 Detailed output saved to: {output_file}")
