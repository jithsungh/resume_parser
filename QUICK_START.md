# 🚀 Quick Start Guide - Smart Resume Parser API

## Start Server (Choose One)

```bash
# Python
python -m src.api

# Uvicorn
uvicorn src.api.main:app --reload --port 8000

# Docker
docker-compose up
```

## API Base URL

```
http://localhost:8000/api/v1
```

## Test Connection

```bash
curl http://localhost:8000/api/v1/health
```

## Parse Single Resume (RECOMMENDED)

```bash
curl -X POST "http://localhost:8000/api/v1/parse/smart" \
  -F "file=@resume.pdf"
```

## Parse Multiple Resumes

```bash
curl -X POST "http://localhost:8000/api/v1/batch/smart-parse" \
  -F "files=@resume1.pdf" \
  -F "files=@resume2.pdf" \
  -F "files=@resume3.pdf"
```

## Check Batch Status

```bash
# Returns job_id from batch request
curl http://localhost:8000/api/v1/batch/status/{job_id}
```

## Force Pipeline (Testing)

```bash
# Force PDF pipeline (fast)
curl -X POST "http://localhost:8000/api/v1/parse/smart?force_pipeline=pdf" \
  -F "file=@resume.pdf"

# Force OCR pipeline (slow, handles scanned PDFs)
curl -X POST "http://localhost:8000/api/v1/parse/smart?force_pipeline=ocr" \
  -F "file=@resume.pdf"
```

## Run Tests

```bash
python test_smart_api.py
```

## View API Docs

```
http://localhost:8000/docs
```

## What Files to Use

- ✅ PDFs (native or scanned)
- ✅ DOCX files
- ❌ Images (not directly, convert to PDF first)
- ❌ HTML (not supported)

## Expected Response

```json
{
  "success": true,
  "filename": "resume.pdf",
  "sections": [
    {"section_name": "Experience", "lines": [...]},
    {"section_name": "Education", "lines": [...]}
  ],
  "metadata": {
    "pipeline_used": "pdf",
    "processing_time": 1.23,
    "num_columns": 2
  }
}
```

## Common Issues

### Server won't start

```bash
# Check if port 8000 is in use
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Use different port
uvicorn src.api.main:app --port 8001
```

### Import errors

```bash
# Install dependencies
pip install -r requirements.txt
```

### Slow OCR

```bash
# Use GPU (if available) or force PDF pipeline
curl -X POST "http://localhost:8000/api/v1/parse/smart?force_pipeline=pdf" \
  -F "file=@resume.pdf"
```

## Performance

- **Native PDF**: ~1 second
- **Scanned PDF (OCR)**: ~2 minutes (CPU), ~10-20s (GPU)
- **DOCX**: ~0.5 seconds

## That's it! 🎉

For more details, see `SMART_PARSER_API.md`
