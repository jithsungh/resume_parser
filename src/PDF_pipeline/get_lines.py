from src.PDF_pipeline.get_words import get_words_from_pdf
from src.PDF_pipeline.split_columns import split_columns
import statistics
import re


def normalize_text(text: str) -> str:
    """Normalize text by cleaning up spacing and special characters, and removing illegal Excel characters."""
    if not text:
        return ""

    replacements = {
        "•": "• ",
        "–": "-",
        "—": "-",
        "\u2022": "• ",
        "\u2023": "• ",
        "\u25E6": "• "
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r'\s+', ' ', text)

    ILLEGAL_CHARACTERS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
    text = ILLEGAL_CHARACTERS_RE.sub('', text)

    return text.strip()


def group_words_to_lines_enhanced(words, y_tolerance=1.5):
    """Enhanced line grouping that matches the pipeline requirements"""
    if not words:
        return []
    
    words_sorted = sorted(words, key=lambda w: (w['top'], w['x0']))

    lines = []
    for word in words_sorted:
        added = False
        for line in lines:
            if not (word['bottom'] < line['y_top'] - y_tolerance or
                   word['top'] > line['y_bottom'] + y_tolerance):
                line['words'].append(word)
                line['y_top'] = min(line['y_top'], word['top'])
                line['y_bottom'] = max(line['y_bottom'], word['bottom'])
                added = True
                break

        if not added:
            lines.append({
                'words': [word],
                'y_top': word['top'],
                'y_bottom': word['bottom']
            })

    for line in lines:
        line['words'].sort(key=lambda w: w['x0'])
        line['text'] = normalize_text(' '.join(w['text'] for w in line['words']))

        xs = [w['x0'] for w in line['words']] + [w['x1'] for w in line['words']]
        line['x0'] = min(xs)
        line['x1'] = max(xs)

    lines.sort(key=lambda l: l['y_top'])
    return lines


def get_lines_from_columns(columns, line_height_threshold=5):
    """
    Extract lines from column-wise split words and compute metrics.
    Returns flat lines and metrics (legacy).
    """
    if not columns:
        return [], {}
    
    all_words = []
    for col in columns:
        all_words.extend(col['words'])

    if not all_words:
        return [], {}

    lines = group_words_into_lines(all_words, line_height_threshold)
    metrics = compute_line_metrics(lines)
    return lines, metrics


def group_words_into_lines(words, line_height_threshold=5):
    """
    Group words into lines based on their vertical positions (legacy, distance-based).
    """
    if not words:
        return []
    
    sorted_words = sorted(words, key=lambda w: (w['top'], w['x0']))
    lines = []
    current_line_words = []
    current_line_top = None

    for word in sorted_words:
        word_top = word['top']
        if current_line_top is None:
            current_line_top = word_top
            current_line_words = [word]
        elif abs(word_top - current_line_top) <= line_height_threshold:
            current_line_words.append(word)
        else:
            if current_line_words:
                line_data = create_line_data(current_line_words, len(lines))
                lines.append(line_data)
            current_line_top = word_top
            current_line_words = [word]

    if current_line_words:
        line_data = create_line_data(current_line_words, len(lines))
        lines.append(line_data)

    return lines


def create_line_data(line_words, line_index):
    """
    Create a line data structure from a list of words belonging to the same line.
    """
    if not line_words:
        return None
    
    line_words.sort(key=lambda w: w['x0'])

    line_x0 = min(word['x0'] for word in line_words)
    line_x1 = max(word['x1'] for word in line_words)
    line_top = min(word['top'] for word in line_words)
    line_bottom = max(word['bottom'] for word in line_words)

    line_text = ' '.join(word['text'] for word in line_words)
    char_count = len(line_text)
    word_count = len(line_words)

    return {
        'line_index': line_index,
        'words': line_words,
        'text': normalize_text(line_text),
        'boundaries': {
            'x0': line_x0,
            'x1': line_x1,
            'top': line_top,
            'bottom': line_bottom,
            'width': line_x1 - line_x0,
            'height': line_bottom - line_top
        },
        'properties': {
            'char_count': char_count,
            'word_count': word_count,
            'char_count_no_spaces': len(line_text.replace(' ', '')),
        }
    }


def compute_line_metrics(lines):
    """
    Compute detailed metrics for each line.
    Returns dict: line_index -> metrics dict
    """
    metrics = {}
    if not lines:
        return metrics
    
    for i, line in enumerate(lines):
        height = line['boundaries']['height']
        char_count = line['properties']['char_count']
        word_count = line['properties']['word_count']
        line_width = line['boundaries']['width']

        # Geometric font proxy (from bbox heights)
        word_heights = [w.get('bottom', 0) - w.get('top', 0) for w in line['words']]
        avg_font_size_geo = statistics.mean(word_heights) if word_heights else 0.0

        # PyMuPDF attributes if available
        span_sizes = [float(w.get('font_size', 0) or 0) for w in line['words'] if 'font_size' in w]
        avg_span_font_size = statistics.mean(span_sizes) if span_sizes else 0.0
        fonts = [str(w.get('font', '')) for w in line['words'] if w.get('font')]
        colors = [int(w.get('font_color', 0) or 0) for w in line['words'] if 'font_color' in w]
        bold_flags = [bool(w.get('is_bold', False)) for w in line['words']]
        bold_ratio = (sum(1 for b in bold_flags if b) / len(bold_flags)) if bold_flags else 0.0

        # Dominant font/color
        def _mode(arr):
            return max(set(arr), key=arr.count) if arr else None
        dominant_font = _mode(fonts)
        dominant_color = _mode(colors)

        space_above = 0.0
        space_below = 0.0

        if i > 0:
            prev_line = lines[i-1]
            space_above = line['boundaries']['top'] - prev_line['boundaries']['bottom']

        if i < len(lines) - 1:
            next_line = lines[i+1]
            space_below = next_line['boundaries']['top'] - line['boundaries']['bottom']

        metrics[i] = {
            'height': float(height),
            'space_above': float(space_above),
            'space_below': float(space_below),
            'char_count': int(char_count),
            'word_count': int(word_count),
            'avg_font_size': float(avg_font_size_geo),
            'avg_span_font_size': float(avg_span_font_size),
            'bold_ratio': float(bold_ratio),
            'dominant_font': dominant_font,
            'dominant_color': dominant_color,
            'line_width': float(line_width),
        }
    return metrics


# ===== New: tight y-overlap, column-wise output =====

def group_words_into_lines_tight(words, y_tolerance=0.5):
    """
    Column-safe line grouping using tight vertical overlap (no extra thresholds).
    """
    if not words:
        return []

    words_sorted = sorted(words, key=lambda w: (w['top'], w['x0']))
    groups = []

    def overlaps_vertically(word, y_top, y_bottom, tol):
        return not (word['bottom'] < y_top - tol or word['top'] > y_bottom + tol)

    for w in words_sorted:
        if groups and overlaps_vertically(w, groups[-1]['y_top'], groups[-1]['y_bottom'], y_tolerance):
            g = groups[-1]
            g['words'].append(w)
            g['y_top'] = min(g['y_top'], w['top'])
            g['y_bottom'] = max(g['y_bottom'], w['bottom'])
        else:
            groups.append({'words': [w], 'y_top': w['top'], 'y_bottom': w['bottom']})

    # Build line dicts with boundaries/properties
    lines = []
    for idx, g in enumerate(groups):
        line = create_line_data(g['words'], idx)
        lines.append(line)

    # Ensure top-to-bottom order
    lines.sort(key=lambda l: l['boundaries']['top'])
    # Re-index
    for i, line in enumerate(lines):
        line['line_index'] = i

    return lines


def get_column_wise_lines(columns, y_tolerance=1.0):
    """
    Build lines per column from split_columns output.
    Returns a list of columns, each with a 'lines' array. No extra thresholds.
    """
    if not columns:
        return []

    result = []
    for col in sorted(columns, key=lambda c: c.get('x_start', 0)):
        words = col.get('words', [])
        lines = group_words_into_lines_tight(words, y_tolerance=y_tolerance)
        metrics = compute_line_metrics(lines)

        # Attach metrics per line for convenience
        for i, line in enumerate(lines):
            if i in metrics:
                line['metrics'] = metrics[i]

        col_out = dict(col)
        col_out['lines'] = lines
        result.append(col_out)

    return result


def _truncate(text, max_len=120):
    s = "" if text is None else str(text)
    return s if len(s) <= max_len else s[: max_len - 1] + "…"


def main():
    # Static inputs
    PDF_PATH = "freshteams_resume/ReactJs/UI_Developer.pdf"
    Y_TOL = 0.5                 # tight y-overlap tolerance
    MIN_WORDS = 10              # min words per column
    DYNAMIC_MIN_WORDS = True    # dynamic min-words (4% of page words, at least MIN_WORDS)
    MAX_LINES_PREVIEW = 6       # preview lines per column
    PAGE_FILTER = None          # set to an int (0-indexed) to show only that page

    print("Extracting words from PDF...")
    pages = get_words_from_pdf(PDF_PATH)
    if not pages:
        print("No pages extracted.")
        return

    print(f"Pages: {len(pages)}")
    for p in pages:
        print(f"  Page {p['page_no']}: size {int(p['width'])}x{int(p['height'])}, words={len(p['words'])}")

    print("\nSplitting into columns...")
    columns = split_columns(
        pages,
        min_words_per_column=MIN_WORDS,
        dynamic_min_words=DYNAMIC_MIN_WORDS
    )
    print(f"Total columns: {len(columns)}")

    # Optional: filter by page
    if PAGE_FILTER is not None:
        columns = [c for c in columns if c.get('page') == PAGE_FILTER]

    print("\nBuilding lines per column (tight y-overlap)...")
    columns_with_lines = get_column_wise_lines(columns, y_tolerance=Y_TOL)

    # Group by page for display
    by_page = {}
    for col in columns_with_lines:
        pg = col.get('page', 0)
        by_page.setdefault(pg, []).append(col)

    print("\n========== COLUMN-WISE LINES ==========")
    for page_no in sorted(by_page.keys()):
        if PAGE_FILTER is not None and page_no != PAGE_FILTER:
            continue

        page_info = next((p for p in pages if p['page_no'] == page_no), None)
        if page_info:
            pw, ph = int(page_info['width']), int(page_info['height'])
            print(f"\nPage {page_no} ({pw}x{ph}) -> columns: {len(by_page[page_no])}")
        else:
            print(f"\nPage {page_no} -> columns: {len(by_page[page_no])}")

        page_cols = sorted(by_page[page_no], key=lambda c: (c.get('column_index', 0), c.get('x_start', 0)))
        for col in page_cols:
            x0 = col.get('x_start', 0)
            x1 = col.get('x_end', 0)
            w = col.get('width', (x1 - x0))
            idx = col.get('column_index', 0)
            word_count = len(col.get('words', []))
            lines = col.get('lines', [])
            print(f"  Col {idx}: x={x0:.1f}-{x1:.1f} (w={w:.1f}), words={word_count}, lines={len(lines)}")

            for line in lines[:MAX_LINES_PREVIEW]:
                b = line['boundaries']
                props = line['properties']
                m = line.get('metrics', {})
                text = _truncate(line.get('text', ''), 120)
                print(
                    f"    [{line['line_index']:>3}] "
                    f"y={b['top']:.1f}-{b['bottom']:.1f} h={b['height']:.1f} "
                    f"wc={props.get('word_count', 0)} "
                    f"fs={m.get('avg_font_size', 0):.1f} "
                    f"lw={m.get('line_width', b.get('width', 0)):.1f} "
                    f"↑{m.get('space_above', 0):.1f} ↓{m.get('space_below', 0):.1f} "
                    f"| {text}"
                )

    print("\nDone.")


# if __name__ == "__main__":
#     main()
