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

if __name__ == "__main__":
    main()