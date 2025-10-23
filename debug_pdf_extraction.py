"""Debug script to see what text PyMuPDF extracts from the Nikhil resume."""

import fitz  # PyMuPDF

pdf_path = "freshteams_resume/Resumes/Nikhil_Matta.pdf"

doc = fitz.open(pdf_path)
page = doc[0]  # First page

print("="*80)
print("EXTRACTING TEXT FROM PAGE 1 using get_text('dict')")
print("="*80)

# Extract text with structure
text_dict = page.get_text("dict")

# Print all text blocks
for block_idx, block in enumerate(text_dict["blocks"]):
    if block["type"] == 0:  # Text block
        print(f"\n--- BLOCK {block_idx} ---")
        print(f"Bbox: {block['bbox']}")
        
        for line_idx, line in enumerate(block["lines"]):
            line_text = ""
            for span in line["spans"]:
                line_text += span["text"]
            
            bbox = line["bbox"]
            print(f"  Line {line_idx}: y0={bbox[1]:.1f}, y1={bbox[3]:.1f}, height={bbox[3]-bbox[1]:.1f}")
            print(f"    Text: '{line_text}'")

print("\n" + "="*80)
print("EXTRACTING TEXT using extract_text_from_pdf_page function")
print("="*80)

from src.ROBUST_pipeline.pipeline import extract_text_from_pdf_page

lines = extract_text_from_pdf_page(page)
print(f"\nExtracted {len(lines)} lines:")
for i, line in enumerate(lines[:20]):  # Show first 20
    print(f"{i:2d}. y0={line['y0']:6.1f} h={line['height']:4.1f} | {line['text']}")

doc.close()
