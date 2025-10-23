"""Debug script to test heading detection on specific text lines."""

from src.ROBUST_pipeline.pipeline import detect_headings_in_block, compute_text_features
from src.PDF_pipeline.segment_sections import guess_section_name, clean_for_heading
import numpy as np

# Sample lines that should be detected as headings
test_lines = [
    {'text': 'PROFILE', 'x0': 10, 'y0': 50, 'x1': 100, 'y1': 65, 'height': 15},
    {'text': 'Backend engineer with deep expertise in Go and Java...', 'x0': 10, 'y0': 70, 'x1': 400, 'y1': 80, 'height': 10},
    {'text': 'Strong foundation in algorithms...', 'x0': 10, 'y0': 85, 'x1': 400, 'y1': 95, 'height': 10},
    {'text': 'SKILLS', 'x0': 10, 'y0': 130, 'x1': 100, 'y1': 145, 'height': 15},
    {'text': 'Languages: Go, Java, Python', 'x0': 10, 'y0': 150, 'x1': 300, 'y1': 160, 'height': 10},
    {'text': 'PROFESSIONAL EXPERIENCE', 'x0': 10, 'y0': 200, 'x1': 250, 'y1': 215, 'height': 15},
    {'text': 'TIMECHAIN LABS PRIVATE LIMITED', 'x0': 10, 'y0': 230, 'x1': 300, 'y1': 240, 'height': 10},
]

# Compute block stats
heights = [l['height'] for l in test_lines]
avg_height = np.mean(heights)
med_height = np.median(heights)

spacings = []
for i in range(len(test_lines) - 1):
    spacing = test_lines[i+1]['y0'] - test_lines[i]['y1']
    spacings.append(spacing)

avg_spacing = np.mean(spacings)
med_spacing = np.median(spacings)

block_stats = {
    'avg_height': avg_height,
    'med_height': med_height,
    'avg_spacing': avg_spacing,
    'med_spacing': med_spacing,
}

print(f"Block stats: avg_height={avg_height:.1f}, avg_spacing={avg_spacing:.1f}")
print("\n" + "="*80)

# Test each line
for i, line in enumerate(test_lines):
    text = line['text']
    cleaned = clean_for_heading(text)
    canon = guess_section_name(cleaned)
    
    word_count = len(text.split())
    char_count = len(text)
    
    # Compute features
    features = compute_text_features(text, test_lines, block_stats)
    
    # Calculate score (same logic as detect_headings_in_block)
    score = 0.0
    
    has_keyword = canon is not None
    is_all_caps = features.get('upper_ratio', 0) >= 0.9
    has_colon = text.strip().endswith(':')
    
    print(f"\nLine {i}: {text}")
    print(f"  Word count: {word_count}, Char count: {char_count}")
    print(f"  Cleaned: {cleaned}")
    print(f"  Canon: {canon}")
    print(f"  Features: upper_ratio={features.get('upper_ratio', 0):.2f}, title_case={features.get('title_case', 0):.2f}")
    print(f"  has_keyword={has_keyword}, is_all_caps={is_all_caps}, has_colon={has_colon}")
    
    # Score calculation
    if has_keyword:
        score += 0.5
        print(f"    +0.5 (has keyword) -> {score:.2f}")
        
        if word_count <= 3 and (is_all_caps or has_colon):
            score += 0.3
            print(f"    +0.3 (keyword + short + all_caps/colon) -> {score:.2f}")
    
    if is_all_caps and word_count <= 5:
        score += 0.25
        print(f"    +0.25 (all caps + short) -> {score:.2f}")
    
    if has_colon and word_count <= 5:
        score += 0.2
        print(f"    +0.2 (has colon + short) -> {score:.2f}")
    
    if features.get('title_case', 0) >= 0.8 and word_count <= 4:
        score += 0.15
        print(f"    +0.15 (title case + short) -> {score:.2f}")
    
    if line['height'] > 1.3 * avg_height:
        score += 0.15
        print(f"    +0.15 (large height) -> {score:.2f}")
    
    if i > 0:
        space_above = line['y0'] - test_lines[i-1]['y1']
        if space_above > 2.0 * avg_spacing:
            score += 0.15
            print(f"    +0.15 (large spacing above: {space_above:.1f} > {2.0*avg_spacing:.1f}) -> {score:.2f}")
    
    # Penalties
    if text and text[0].islower():
        score -= 0.2
        print(f"    -0.2 (starts lowercase) -> {score:.2f}")
    
    num_digits = sum(c.isdigit() for c in text)
    if num_digits > len(text) * 0.3:
        score -= 0.15
        print(f"    -0.15 (too many digits) -> {score:.2f}")
    
    if word_count > 5:
        score -= 0.15
        print(f"    -0.15 (too long) -> {score:.2f}")
    
    print(f"  FINAL SCORE: {score:.2f} {'✓ ACCEPTED' if score >= 0.6 else '✗ REJECTED'} (threshold: 0.6)")
