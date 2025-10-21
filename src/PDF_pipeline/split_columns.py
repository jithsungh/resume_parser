from src.PDF_pipeline.get_words import get_words_from_pdf, get_all_words_flat

def run_length_encoding(data):
    if not data:
        return []

    rle = []
    prev = data[0]
    count = 1

    for item in data[1:]:
        if item == prev:
            count += 1
        else:
            rle.append((prev, count))
            prev = item
            count = 1

    rle.append((prev, count))
    return rle

def get_columns(rle, page_width, min_gap_width=None):
    # trim starting and ending zeros
    while rle and rle[0][0] == 0:
        rle.pop(0)
    while rle and rle[-1][0] == 0:
        rle.pop()

    if not rle:
        return []
    
    # Dynamic min gap width ~2% of page width (≈12px for 595)
    if min_gap_width is None:
        min_gap_width = max(3, int(page_width * 0.02))

    # Identify gaps (0 counts) that are wide enough to be column separators
    gaps = []
    pos = 0
    for value, length in rle:
        if value == 0 and length >= min_gap_width:
            gaps.append((pos, pos + length - 1))
        pos += length

    # Define columns based on gaps (use full page width, not len(rle))
    columns = []
    if not gaps:
        columns.append((0, int(page_width) - 1))
    else:
        # First column before the first gap
        if gaps[0][0] > 0:
            columns.append((0, gaps[0][0] - 1))
        
        # Columns between gaps
        for i in range(len(gaps) - 1):
            columns.append((gaps[i][1] + 1, gaps[i + 1][0] - 1))
        
        # Last column after the last gap
        last_px = int(page_width) - 1
        if gaps[-1][1] < last_px:
            columns.append((gaps[-1][1] + 1, last_px))

    return columns

def identify_columns_in_page(words, page_width, min_words_per_column=10, dynamic_min_words=True):
    """
    Build columns by horizontal gaps, then drop/merge columns with too few words.
    Avoids counting small-height peaks as columns.
    """
    if not words:
        return []

    vertical = [0] * (int(page_width) + 1)

    for word in words:
        x0 = int(word['x0'])
        x1 = int(word['x1'])
        for x in range(x0, x1 + 1):
            if 0 <= x < len(vertical):
                vertical[x] += 1

    # Identify gaps in the vertical histogram
    rle = run_length_encoding(vertical)

    # Identify column ranges
    columns = get_columns(rle, page_width)

    # If no gaps -> treat entire page as one column
    if not columns:
        return [{
            'column_index': 0,
            'x_start': min(word['x0'] for word in words),
            'x_end': max(word['x1'] for word in words),
            'width': max(word['x1'] for word in words) - min(word['x0'] for word in words),
            'words': sorted(words, key=lambda w: (w['top'], w['x0']))
        }]

    # Assign words to initial columns
    initial_cols = []
    for i, (x_start, x_end) in enumerate(columns):
        col_words = []
        for word in words:
            word_center = (word['x0'] + word['x1']) / 2
            if x_start <= word_center <= x_end:
                col_words.append(word)
        if col_words:
            col_words.sort(key=lambda w: (w['top'], w['x0']))
            initial_cols.append({
                'column_index': i,
                'x_start': x_start,
                'x_end': x_end,
                'width': x_end - x_start + 1,
                'words': col_words
            })

    if not initial_cols:
        # Fallback single column
        return [{
            'column_index': 0,
            'x_start': min(word['x0'] for word in words),
            'x_end': max(word['x1'] for word in words),
            'width': max(word['x1'] for word in words) - min(word['x0'] for word in words),
            'words': sorted(words, key=lambda w: (w['top'], w['x0']))
        }]

    # Minimum words requirement (avoid tiny peaks)
    if dynamic_min_words:
        required_min_words = max(min_words_per_column, int(len(words) * 0.04))  # 4% of page words, at least 10
    else:
        required_min_words = min_words_per_column

    valid = [c for c in initial_cols if len(c['words']) >= required_min_words]
    invalid = [c for c in initial_cols if len(c['words']) < required_min_words]

    # If no valid columns -> fallback to single column
    if not valid:
        return [{
            'column_index': 0,
            'x_start': min(word['x0'] for word in words),
            'x_end': max(word['x1'] for word in words),
            'width': max(word['x1'] for word in words) - min(word['x0'] for word in words),
            'words': sorted(words, key=lambda w: (w['top'], w['x0']))
        }]

    # Merge invalid columns into nearest valid column (by center distance)
    def center(col):
        return (col['x_start'] + col['x_end']) / 2.0

    for col in invalid:
        c = center(col)
        nearest = min(valid, key=lambda v: abs(center(v) - c))
        nearest['words'].extend(col['words'])

    # Sort and recompute bounds for valid columns after merging
    for idx, col in enumerate(sorted(valid, key=lambda c: c['x_start'])):
        col['words'].sort(key=lambda w: (w['top'], w['x0']))
        # Tighten x bounds to actual assigned words
        xs = [w['x0'] for w in col['words']]
        xe = [w['x1'] for w in col['words']]
        col['x_start'] = int(min(xs))
        col['x_end'] = int(max(xe))
        col['width'] = col['x_end'] - col['x_start'] + 1
        col['column_index'] = idx

    return valid

def split_columns_by_multi_section_header(
    words,
    page_width,
    multi_section_line,
    min_words_per_column=5
):
    """
    Split words into columns based on a multi-section header line.
    
    This function analyzes the X-coordinates of section headers that appear
    on the same line (e.g., "EXPERIENCE    SKILLS") and uses those positions
    to split the page into columns.
    
    Args:
        words: List of word dictionaries with x0, x1, top, text
        page_width: Width of the page in PDF coordinates
        multi_section_line: Dict with 'text', 'boundaries', 'multi_sections', etc.
        min_words_per_column: Minimum words required for a valid column
        
    Returns:
        List of column dictionaries, each with column_index, x_start, x_end, words
    """
    if not words or not multi_section_line:
        return []
    
    # Extract multi-section information
    multi_sections = multi_section_line.get('multi_sections', [])
    if len(multi_sections) < 2:
        # Not a multi-section header, fall back to standard column detection
        return identify_columns_in_page(words, page_width, min_words_per_column)
    
    # Get the full text of the header line
    header_text = multi_section_line.get('text', '')
    
    # Parse the boundaries to get X-coordinates
    boundaries = multi_section_line.get('boundaries', {})
    header_x0 = boundaries.get('x0', 0)
    header_x1 = boundaries.get('x1', page_width)
    header_width = header_x1 - header_x0
    
    # Strategy: Find where each section name appears in the header text
    # and map that to X-coordinate ranges
    section_positions = []
    
    for i, section_name in enumerate(multi_sections):
        # Find position in text (case-insensitive)
        text_lower = header_text.lower()
        section_lower = section_name.lower()
        
        # Try to find the section name in the header
        pos = text_lower.find(section_lower)
        
        if pos == -1:
            # Try finding any variant of the section name
            # This handles cases like "WORK EXPERIENCE" when section is "Experience"
            words_in_section = section_lower.split()
            for word in words_in_section:
                if len(word) > 3:  # Skip short words
                    pos = text_lower.find(word)
                    if pos != -1:
                        break
        
        if pos != -1:
            # Calculate approximate X position based on character position
            char_ratio = pos / len(header_text) if len(header_text) > 0 else 0
            approx_x = header_x0 + (char_ratio * header_width)
            
            section_positions.append({
                'section': section_name,
                'text_pos': pos,
                'approx_x': approx_x,
                'index': i
            })
    
    # Sort by X position
    section_positions.sort(key=lambda x: x['approx_x'])
    
    if len(section_positions) < 2:
        # Couldn't determine positions, fall back
        return identify_columns_in_page(words, page_width, min_words_per_column)
    
    # Define column boundaries based on section positions
    # Strategy: Split at midpoints between sections
    columns = []
    
    for i in range(len(section_positions)):
        if i == 0:
            # First column: from start to midpoint to next section
            x_start = 0
            if i + 1 < len(section_positions):
                x_end = (section_positions[i]['approx_x'] + section_positions[i + 1]['approx_x']) / 2
            else:
                x_end = page_width
        elif i == len(section_positions) - 1:
            # Last column: from midpoint to end
            x_start = (section_positions[i - 1]['approx_x'] + section_positions[i]['approx_x']) / 2
            x_end = page_width
        else:
            # Middle column: midpoint to midpoint
            x_start = (section_positions[i - 1]['approx_x'] + section_positions[i]['approx_x']) / 2
            x_end = (section_positions[i]['approx_x'] + section_positions[i + 1]['approx_x']) / 2
        
        # Assign words to this column
        col_words = []
        for word in words:
            word_center = (word['x0'] + word['x1']) / 2
            if x_start <= word_center <= x_end:
                col_words.append(word)
        
        if len(col_words) >= min_words_per_column:
            col_words.sort(key=lambda w: (w['top'], w['x0']))
            
            # Tighten bounds to actual words
            if col_words:
                actual_x_start = min(w['x0'] for w in col_words)
                actual_x_end = max(w['x1'] for w in col_words)
            else:
                actual_x_start = x_start
                actual_x_end = x_end
            
            columns.append({
                'column_index': i,
                'x_start': int(actual_x_start),
                'x_end': int(actual_x_end),
                'width': int(actual_x_end - actual_x_start + 1),
                'words': col_words,
                'section_hint': section_positions[i]['section']  # Hint for section detection
            })
    
    # If no valid columns found, fall back
    if not columns:
        return identify_columns_in_page(words, page_width, min_words_per_column)
    
    # Reindex columns
    for idx, col in enumerate(columns):
        col['column_index'] = idx
    
    return columns


def refine_columns_with_word_clustering(words, page_width, initial_columns):
    """
    Refine column boundaries using word clustering analysis.
    
    This is useful when the initial column detection (gap-based or multi-section)
    needs fine-tuning based on actual word distribution.
    
    Args:
        words: List of all words on the page
        page_width: Width of the page
        initial_columns: Initial column boundaries from other methods
        
    Returns:
        Refined list of columns
    """
    if not initial_columns or len(initial_columns) == 1:
        return initial_columns
    
    # Analyze X-coordinate distribution of words
    x_centers = [((w['x0'] + w['x1']) / 2) for w in words]
    
    if not x_centers:
        return initial_columns
    
    # For each column, check if word distribution is consistent
    refined_columns = []
    
    for col in initial_columns:
        col_words = col['words']
        if not col_words:
            continue
        
        # Calculate density profile within this column
        col_x_centers = [((w['x0'] + w['x1']) / 2) for w in col_words]
        
        # Check for bimodal distribution (indicates column should be split)
        # Simple check: are words clustered in two distinct regions?
        col_x_centers.sort()
        
        if len(col_x_centers) >= 20:  # Only try splitting if enough words
            # Find largest gap in X distribution
            gaps = []
            for i in range(1, len(col_x_centers)):
                gap = col_x_centers[i] - col_x_centers[i-1]
                gaps.append((gap, col_x_centers[i-1], col_x_centers[i]))
            
            if gaps:
                max_gap = max(gaps, key=lambda x: x[0])
                
                # If gap is significant (> 10% of column width), consider splitting
                if max_gap[0] > (col['x_end'] - col['x_start']) * 0.1:
                    # Split column at this gap
                    split_point = (max_gap[1] + max_gap[2]) / 2
                    
                    left_words = [w for w in col_words if (w['x0'] + w['x1'])/2 < split_point]
                    right_words = [w for w in col_words if (w['x0'] + w['x1'])/2 >= split_point]
                    
                    if len(left_words) >= 5 and len(right_words) >= 5:
                        # Valid split
                        refined_columns.append({
                            'column_index': len(refined_columns),
                            'x_start': min(w['x0'] for w in left_words),
                            'x_end': max(w['x1'] for w in left_words),
                            'width': max(w['x1'] for w in left_words) - min(w['x0'] for w in left_words),
                            'words': sorted(left_words, key=lambda w: (w['top'], w['x0']))
                        })
                        refined_columns.append({
                            'column_index': len(refined_columns),
                            'x_start': min(w['x0'] for w in right_words),
                            'x_end': max(w['x1'] for w in right_words),
                            'width': max(w['x1'] for w in right_words) - min(w['x0'] for w in right_words),
                            'words': sorted(right_words, key=lambda w: (w['top'], w['x0']))
                        })
                        continue
        
        # No split needed, keep original column
        refined_columns.append(col)
    
    # Reindex
    for idx, col in enumerate(refined_columns):
        col['column_index'] = idx
    
    return refined_columns

def get_global_columns(all_columns):
    """
    Identify global column structure across all pages.
    Groups columns with similar x-positions across different pages.
    """
    if not all_columns:
        return []
    
    # Group columns by similar x_start positions (with tolerance)
    tolerance = 10  # pixels
    global_columns = []
    
    for col in all_columns:
        matched = False
        for global_col in global_columns:
            if abs(col['x_start'] - global_col['avg_x_start']) <= tolerance:
                global_col['columns'].append(col)
                # Update averages
                global_col['avg_x_start'] = sum(c['x_start'] for c in global_col['columns']) / len(global_col['columns'])
                global_col['avg_x_end'] = sum(c['x_end'] for c in global_col['columns']) / len(global_col['columns'])
                matched = True
                break
        
        if not matched:
            global_columns.append({
                'global_column_index': len(global_columns),
                'avg_x_start': col['x_start'],
                'avg_x_end': col['x_end'],
                'columns': [col]
            })
    
    global_columns.sort(key=lambda gc: gc['avg_x_start'])
    for i, gc in enumerate(global_columns):
        gc['global_column_index'] = i
    
    return global_columns

def split_columns(pages, min_words_per_column=10, dynamic_min_words=True):
    """
    Split words into columns for each page and return a flat list of columns.
    Also attaches page['columns'] for convenience.
    """
    all_columns = []
    for page in pages:
        words = page['words']
        page_width = page['width']
        
        page_columns = identify_columns_in_page(
            words,
            page_width,
            min_words_per_column=min_words_per_column,
            dynamic_min_words=dynamic_min_words
        )
        
        for col in page_columns:
            col['page'] = page['page_no']
        
        page['columns'] = page_columns
        all_columns.extend(page_columns)
    return all_columns

def main():
    pdf_path = "freshteams_resume/ReactJs/UI_Developer.pdf"
    
    # Extract words from all pages
    print("Extracting words from PDF...")
    pages = get_words_from_pdf(pdf_path)
    total_words = sum(len(p['words']) for p in pages)
    print(f"Total words extracted: {total_words}")
    
    # Split into columns
    print("\nIdentifying columns...")
    columns = split_columns(pages, min_words_per_column=10, dynamic_min_words=True)
    print(f"Total columns found: {len(columns)}")
    
    # Display column information
    for col in columns:
        print(f"\nPage {col.get('page', 'Unknown')}, Column {col['column_index']}:")
        print(f"  Position: x={col['x_start']:.1f} to {col['x_end']:.1f} (width: {col.get('width', 0):.1f})")
        print(f"  Words: {len(col['words'])}")
        
        # Show first few words in each column
        print("  First 5 words:")
        for word in col['words'][:5]:
            print(f"    '{word['text']}' at ({word['x0']:.1f}, {word['top']:.1f})")
    
    # Get global column structure
    print("\n" + "="*50)
    print("GLOBAL COLUMN ANALYSIS")
    print("="*50)
    
    global_cols = get_global_columns(columns)
    print(f"Global columns identified: {len(global_cols)}")
    
    for gc in global_cols:
        print(f"\nGlobal Column {gc['global_column_index']}:")
        print(f"  Average position: x={gc['avg_x_start']:.1f} to {gc['avg_x_end']:.1f}")
        print(f"  Appears on {len(gc['columns'])} pages")
        
        total_words_gc = sum(len(col['words']) for col in gc['columns'])
        print(f"  Total words: {total_words_gc}")
        
        # Show pages where this column appears
        pages_list = [col.get('page', 'Unknown') for col in gc['columns']]
        print(f"  Pages: {pages_list}")

# if __name__ == "__main__":
#     main()