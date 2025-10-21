# 🚀 Resume Parser - Quick Reference

## ⚡ Quick Start (3 Commands)

```bash
# 1. Install dependencies
pip install -r requirements.txt && python -m spacy download en_core_web_sm

# 2. Parse single resume
python quick_parse.py resume.pdf

# 3. Batch process folder
python batch_resume_parser.py freshteams_resume/ReactJs/ --output results.xlsx
```

---

## 📋 Common Commands

### Single File Parsing

```bash
# Parse any resume
python quick_parse.py path/to/resume.pdf
python quick_parse.py path/to/resume.docx
python quick_parse.py path/to/resume.txt
```

### Batch Processing

```bash
# Basic - process all PDFs and DOCXs
python batch_resume_parser.py folder_path/

# With custom output file
python batch_resume_parser.py folder_path/ --output candidates.xlsx

# Specify file types
python batch_resume_parser.py folder_path/ --extensions .pdf .txt

# Custom model
python batch_resume_parser.py folder_path/ --model custom_model_path/
```

### Testing

```bash
# Test complete pipeline
python test_complete_parser.py

# Test name extraction
python test_name_extraction.py

# Test NER model
python test_ner_pipeline.py
```

---

## 💻 Python API

### Basic Usage

```python
from src.core.complete_resume_parser import CompleteResumeParser

# Initialize once
parser = CompleteResumeParser(model_path="ml_model")

# Parse resume
result = parser.parse_resume(resume_text, filename="resume.pdf")

# Access results
name = result['name']
email = result['email']
experience = result['total_experience_years']
role = result['primary_role']
```

### Access Work History

```python
for exp in result['experiences']:
    print(f"{exp['company_name']} - {exp['role']}")
    print(f"  Period: {exp['from_date']} to {exp['to_date']}")
    print(f"  Skills: {', '.join(exp['skills'])}")
```

### Batch Processing in Code

```python
from batch_resume_parser import BatchResumeProcessor

processor = BatchResumeProcessor(model_path="ml_model")
df = processor.process_folder("resumes/", output_file="results.xlsx")

# Work with DataFrame
print(f"Processed {len(df)} resumes")
print(df[['Name', 'Primary Role', 'Total Experience (Years)']].head())
```

---

## 📊 Output Fields

| Field                    | Type  | Description              |
| ------------------------ | ----- | ------------------------ |
| `name`                   | str   | Candidate's full name    |
| `email`                  | str   | Email address            |
| `mobile`                 | str   | Mobile number            |
| `location`               | str   | City/Location            |
| `total_experience_years` | float | Years of experience      |
| `primary_role`           | str   | Current or main role     |
| `experiences`            | list  | Work history (see below) |

### Experience Object

```python
{
  "company_name": "Company XYZ",
  "role": "Software Engineer",
  "from_date": "Jan 2022",
  "to_date": "Dec 2023",
  "duration_months": 24,
  "skills": ["Python", "React", "AWS", "..."]
}
```

---

## 🔧 Troubleshooting

### Problem: spaCy model not found

```bash
python -m spacy download en_core_web_sm
```

### Problem: PDF extraction fails

```bash
pip install PyPDF2
```

### Problem: DOCX extraction fails

```bash
pip install python-docx
```

### Problem: Model files missing

```bash
# Check if model files exist
ls ml_model/
# Should show: config.json, model.safetensors, tokenizer files
```

### Problem: Import errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

---

## 📁 File Structure

```
resume_parser/
├── ml_model/              # NER model (required)
├── src/core/              # Core modules
│   ├── complete_resume_parser.py
│   └── name_location_extractor.py
├── config/roles.py        # Role mappings
├── quick_parse.py         # Single file CLI
├── batch_resume_parser.py # Batch processing
└── test_*.py              # Test scripts
```

---

## 🎯 Use Cases

### Scenario 1: Quick Resume Review

```bash
python quick_parse.py candidate_resume.pdf
# See structured output in terminal
```

### Scenario 2: Process Job Applications

```bash
python batch_resume_parser.py applications/ --output applicants.xlsx
# Open applicants.xlsx in Excel for review
```

### Scenario 3: Build Candidate Database

```python
processor = BatchResumeProcessor("ml_model")
df = processor.process_folder("all_resumes/")
df.to_sql("candidates", db_connection)
```

### Scenario 4: Filter by Experience

```python
# After batch processing
df = pd.read_excel("results.xlsx")
senior_devs = df[
    (df['Primary Role'].str.contains('Developer')) &
    (df['Total Experience (Years)'] >= 5)
]
```

---

## 📈 Performance Tips

### For Single Files

- Pre-load parser once, reuse for multiple parses
- Use `.txt` files when possible (fastest)

### For Batch Processing

- Process in chunks if folder is very large
- Use SSD for better I/O performance
- Consider parallel processing for 1000+ files

### Memory Optimization

```python
# For very large batches, process in chunks
import glob

for chunk in chunks_of(glob.glob("resumes/*.pdf"), 100):
    df = processor.process_files(chunk)
    df.to_csv("output_chunk.csv", mode='a')
```

---

## 🎓 Advanced Features

### Custom Role Mapping

```python
# Edit config/roles.py to add custom roles
CANONICAL_ROLES = {
    "Your Custom Role": [
        "variant1", "variant2", "..."
    ]
}
```

### Extract Specific Sections

```python
parser = CompleteResumeParser("ml_model")

# Get only experience section
exp_text = parser._extract_experience_section(resume_text)

# Run NER only
entities = parser._extract_experiences(exp_text)
```

### Custom Post-Processing

```python
result = parser.parse_resume(text)

# Add custom fields
result['years_at_current_company'] = calculate_tenure(result)
result['skill_count'] = len(set(
    skill
    for exp in result['experiences']
    for skill in exp['skills']
))
```

---

## 📞 Support Checklist

Before asking for help:

- [ ] Ran `pip install -r requirements.txt`
- [ ] Downloaded spaCy model
- [ ] Verified `ml_model/` folder exists
- [ ] Ran test scripts successfully
- [ ] Checked file format is supported
- [ ] Tried with a simple .txt file first

---

## 🎉 Success Indicators

You're ready to use the parser when:

- ✅ Test scripts run without errors
- ✅ Sample resume parses correctly
- ✅ Name, email, and companies extracted
- ✅ Batch processing works on test folder

---

## 📚 Documentation

- **COMPLETE_PARSER_README.md** - Full documentation
- **IMPLEMENTATION_COMPLETE.md** - Technical summary
- **This file** - Quick reference

---

**Ready to parse resumes! 🚀**

```bash
# Start here:
python quick_parse.py your_resume.pdf
```
