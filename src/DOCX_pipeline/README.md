# DOCX Pipeline - Word Document Processing

Handles extraction from Microsoft Word documents (.docx, .doc).

## Purpose

Extract structured content from Word documents while preserving formatting, styles, and document structure.

## Key File

### `pipeline.py`

**Main entry point** for DOCX extraction.

**What it does**:

- Parses DOCX using python-docx library
- Extracts paragraphs and runs with styles
- Identifies headers based on styles (Heading 1, Heading 2, etc.)
- Detects sections using style hierarchy
- Handles tables, lists, and formatted text
- Preserves bold, italic, and font size information

## How It Works

### 1. Document Parsing

```python
from docx import Document
doc = Document("resume.docx")
```

### 2. Extract Paragraphs

Each paragraph has:

- **Text content**
- **Style** (Normal, Heading 1, Heading 2, etc.)
- **Runs** (individual formatted text segments)
- **Font information** (size, bold, italic)

### 3. Section Detection

Identifies sections using:

- **Style hierarchy**: Heading 1 = major section, Heading 2 = subsection
- **Formatting**: Bold, larger font = likely header
- **Keywords**: "Experience", "Education", etc.
- **Position**: Standalone paragraphs

### 4. Structure Extraction

Maintains document hierarchy:

```
Document
  ├─ Section: Contact Information
  │    └─ Text: "John Doe\nEmail: john@example.com"
  ├─ Section: Experience
  │    ├─ Subsection: Company A
  │    └─ Subsection: Company B
  └─ Section: Education
       └─ Text: "BS Computer Science, 2020"
```

## Features

### Style-Based Detection

Word's built-in styles make section detection highly accurate:

- `Heading 1` → Major section
- `Heading 2` → Subsection
- `Heading 3` → Sub-subsection
- `Normal` → Body content

### Formatting Preservation

Captures:

- **Bold** → Often used for job titles, company names
- **Italic** → Often used for dates, positions
- **Font size** → Larger = more important
- **Lists** → Bullet points, numbered lists

### Table Handling

Extracts tables (common for skills matrices):

```
| Skill      | Level      |
|------------|------------|
| Python     | Expert     |
| Java       | Advanced   |
```

## Usage

### Basic Usage

```python
from src.DOCX_pipeline.pipeline import run_pipeline

result, simplified_json = run_pipeline(
    "resume.docx",
    verbose=True
)

print(f"Sections found: {len(result['sections'])}")
```

### Access Structured Data

```python
for section in result['sections']:
    print(f"\n{section['section']}:")
    for line in section['lines']:
        print(f"  {line}")
```

## Output Format

Same as PDF pipeline for consistency:

```json
{
  "sections": [
    {
      "section": "Experience",
      "lines": [
        "Software Engineer at Google",
        "Jan 2020 - Present",
        "- Built scalable systems",
        "- Led team of 5 engineers"
      ]
    }
  ],
  "meta": {
    "total_paragraphs": 45,
    "total_sections": 8,
    "has_tables": true
  }
}
```

## Advantages Over PDF

1. **Style information**: Word documents have explicit styles
2. **More accurate headers**: Heading styles are clear indicators
3. **Faster**: No OCR or complex layout analysis needed
4. **Better tables**: Native table structure preserved
5. **Lists preserved**: Bullet points and numbering maintained

## Limitations

1. **Older .doc format**: May need conversion to .docx (python-docx only supports .docx)
2. **Complex layouts**: Very creative designs may not parse perfectly
3. **Images**: Text in images not extracted (no OCR)
4. **Embedded objects**: Charts, diagrams ignored

## Common Issues & Solutions

### Issue: Old .doc files not supported

**Solution**: Convert to .docx first using:

```python
# Use external tool or library like pywin32 (Windows only)
# Or: Use online converter
```

### Issue: No styles used (all "Normal")

**Solution**: Falls back to keyword and formatting detection (same as PDF)

### Issue: Tables not parsed correctly

**Solution**: Tables are extracted row-by-row as text lines

## Performance

- **Simple DOCX**: ~0.1-0.5 seconds
- **Complex with tables**: ~0.5-1 second
- **Very large documents**: ~1-2 seconds

Much faster than PDF because no layout analysis required!

## Best Practices

1. **Prefer DOCX over PDF** when available (faster, more accurate)
2. **Check for styles** - documents with proper styles parse better
3. **Test with sample** - some Word documents have unusual structures
4. **Convert old .doc** - always convert to .docx first

## Integration with Unified Pipeline

The unified pipeline automatically:

1. Detects .docx extension
2. Routes to DOCX_pipeline
3. Falls back to OCR if extraction fails
4. Validates quality

You don't need to call DOCX_pipeline directly - use `UnifiedPipeline`!

## Section Mapping

Same standard sections as PDF pipeline:

- Contact Information
- Summary
- Skills
- Experience
- Projects
- Education
- Certifications
- Achievements
- Publications
- Languages
- Volunteer
- Hobbies
- References
- Declarations
