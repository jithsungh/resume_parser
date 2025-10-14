import pdfplumber

def get_words_from_pdf(pdf_path, x_tolerance=2, y_tolerance=2.5, keep_blank_chars=False):
    """Extract words from all pages of a PDF with their coordinates"""
    pages = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                words = page.extract_words(
                    x_tolerance=x_tolerance,
                    y_tolerance=y_tolerance,
                    keep_blank_chars=keep_blank_chars
                )
                
                # Add page info to each word
                for word in words:
                    word['page'] = page_num  # 0-indexed for consistency with pipeline
                    word['page_width'] = float(page.width)
                    word['page_height'] = float(page.height)
                
                pages.append({
                    "page_no": page_num,
                    "width": float(page.width),
                    "height": float(page.height),
                    "words": words
                })
                
    except Exception as e:
        print(f"Error extracting from {pdf_path}: {e}")
        return []
    
    return pages

def get_all_words_flat(pdf_path, x_tolerance=2, y_tolerance=2.5, keep_blank_chars=False):
    """Extract all words as a flat list (for backward compatibility)"""
    pages = get_words_from_pdf(pdf_path, x_tolerance, y_tolerance, keep_blank_chars)
    all_words = []
    
    for page in pages:
        all_words.extend(page['words'])
    
    return all_words

def get_words_from_single_page(pdf_path, page_number=0):
    """Extract words from a single page of a PDF"""
    with pdfplumber.open(pdf_path) as pdf:
        if page_number >= len(pdf.pages):
            raise ValueError(f"Page {page_number} does not exist. PDF has {len(pdf.pages)} pages.")
        
        page = pdf.pages[page_number]
        words = page.extract_words()
        
        # Add page info to each word
        for word in words:
            word['page'] = page_number + 1
            word['page_width'] = page.width
            word['page_height'] = page.height
            
        return words

def main():
    pdf_path = "freshteams_resume/ReactJs/UI_Developer.pdf"
    
    # Extract words from all pages
    print("Extracting words from all pages...")
    pages = get_words_from_pdf(pdf_path)
    
    print(f"Total pages extracted: {len(pages)}")

    for page in pages:
        for word in page['words'][:3]:  # Show first 3 words of each page
            print(f"Page {page['page_no'] + 1}: '{word['text']}' at ({word['x0']:.1f}, {word['top']:.1f})")
    
    # # Group by pages and show summary
    # pages = {}
    # for word in words:
    #     page_num = word.get('page', 1)
    #     if page_num not in pages:
    #         pages[page_num] = []
    #     pages[page_num].append(word)
    
    # print(f"Pages found: {len(pages)}")
    
    # for page_num in sorted(pages.keys()):
    #     page_words = pages[page_num]
    #     print(f"Page {page_num}: {len(page_words)} words")
        
    #     # Show first few words from each page
    #     print("  First 3 words:")
    #     for w in page_words[:3]:
    #         print(f"    '{w['text']}' at ({w['x0']:.1f}, {w['top']:.1f})")
    
    # print("\n" + "="*50)
    # print("Testing single page extraction...")
    
    # # Test single page extraction
    # try:
    #     single_page_words = get_words_from_single_page(pdf_path, 0)
    #     print(f"Single page (page 1) words: {len(single_page_words)}")
    # except ValueError as e:
    #     print(f"Error: {e}")
if __name__ == "__main__":
    main()