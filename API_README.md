# Resume Parser API

Advanced Resume Parsing API with Named Entity Recognition (NER) and Section Segmentation capabilities.

## 🌟 Features

- **Single Resume Parsing**: Parse individual resume files (PDF, DOCX, TXT)
- **Batch Processing**: Process multiple resumes asynchronously with progress tracking
- **NER Extraction**: Extract named entities (companies, roles, dates, technologies)
- **Section Segmentation**: Identify and extract resume sections
- **Contact Extraction**: Fast extraction of contact information
- **Async Workflows**: Non-blocking asynchronous processing
- **RESTful API**: Clean, well-documented REST endpoints
- **Interactive Docs**: Swagger UI and ReDoc documentation

## 📋 Extracted Information

- **Contact Info**: Name, Email, Mobile, Location
- **Experience**: Total years of experience
- **Role**: Primary/Current role
- **Work History**:
  - Company names
  - Job titles
  - Employment dates
  - Duration
  - Skills/Technologies used

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Trained NER model (in `./ml_model` directory)

### Installation

1. **Clone the repository**:
```bash
cd resume_parser
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Download spaCy model**:
```bash
python -m spacy download en_core_web_sm
```

5. **Configure environment** (optional):
```bash
cp .env.example .env
# Edit .env with your settings
```

### Running the Server

**Option 1: Using the startup script**:
```bash
bash start_api.sh
```

**Option 2: Direct uvicorn command**:
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Option 3: Using Python**:
```bash
python -m src.api.main
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/v1/health

## 📚 API Endpoints

### Health Check
```http
GET /api/v1/health
```
Check service status and model availability.

### Single Resume Parsing
```http
POST /api/v1/parse/single
Content-Type: multipart/form-data

file: <resume_file>
```
Parse a single resume file and extract all information.

**Example using curl**:
```bash
curl -X POST "http://localhost:8000/api/v1/parse/single" \
  -F "file=@/path/to/resume.pdf"
```

### Parse from Text
```http
POST /api/v1/parse/text
Content-Type: application/json

{
  "text": "resume text content...",
  "filename": "optional_filename.txt"
}
```

### NER Entity Extraction
```http
POST /api/v1/ner/extract?text=your_text_here
```
Extract named entities with confidence scores.

### Section Segmentation
```http
POST /api/v1/sections/segment
Content-Type: multipart/form-data

file: <resume_file>
```
or
```http
POST /api/v1/sections/segment
Content-Type: application/json

{
  "text": "resume text...",
  "filename": "optional.txt"
}
```

### Contact Information Extraction
```http
POST /api/v1/contact/extract
Content-Type: multipart/form-data

file: <resume_file>
```

### Batch Processing
```http
POST /api/v1/batch/parse
Content-Type: multipart/form-data

files: [<file1>, <file2>, ...]
```
Returns a `job_id` for tracking.

### Check Batch Status
```http
GET /api/v1/batch/status/{job_id}
```

## 🔧 Configuration

Edit `.env` file or set environment variables:

```env
# Model Settings
MODEL_PATH=./ml_model

# Server Settings
HOST=0.0.0.0
PORT=8000
RELOAD=True

# Processing Settings
MAX_BATCH_SIZE=100
MAX_FILE_SIZE_MB=10
WORKER_THREADS=4

# Logging
LOG_LEVEL=INFO
```

## 📦 Project Structure

```
resume_parser/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI app entry point
│   │   ├── routes.py        # API endpoints
│   │   ├── service.py       # Business logic
│   │   ├── models.py        # Pydantic models
│   │   └── config.py        # Configuration
│   ├── core/
│   │   ├── complete_resume_parser.py
│   │   ├── name_location_extractor.py
│   │   ├── section_splitter.py
│   │   └── ...
│   └── PDF_pipeline/
│       └── ...
├── ml_model/                # Trained NER model
├── requirements.txt
├── start_api.sh            # Startup script
└── .env.example            # Example configuration
```

## 🧪 Testing

### Using Python Client
```python
import requests

# Parse single resume
with open('resume.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/v1/parse/single',
        files={'file': f}
    )
    result = response.json()
    print(result)

# Extract entities
response = requests.post(
    'http://localhost:8000/api/v1/ner/extract',
    params={'text': 'John Doe worked at Google as Software Engineer'}
)
entities = response.json()
print(entities)
```

### Using cURL
```bash
# Health check
curl http://localhost:8000/api/v1/health

# Parse resume
curl -X POST "http://localhost:8000/api/v1/parse/single" \
  -F "file=@resume.pdf"

# Extract entities
curl -X POST "http://localhost:8000/api/v1/ner/extract?text=Sample%20text"

# Batch processing
curl -X POST "http://localhost:8000/api/v1/batch/parse" \
  -F "files=@resume1.pdf" \
  -F "files=@resume2.pdf"
```

## 🐳 Docker Deployment (Optional)

Create `Dockerfile`:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t resume-parser-api .
docker run -p 8000:8000 -v $(pwd)/ml_model:/app/ml_model resume-parser-api
```

## 📊 Response Examples

### Parse Single Resume Response
```json
{
  "name": "John Doe",
  "email": "john.doe@email.com",
  "mobile": "+919876543210",
  "location": "Bangalore, India",
  "total_experience_years": 5.2,
  "primary_role": "Senior Software Engineer",
  "experiences": [
    {
      "company_name": "Tech Corp",
      "role": "Senior Software Engineer",
      "from_date": "Jan 2020",
      "to_date": "Present",
      "duration_months": 45,
      "skills": ["Python", "FastAPI", "Docker", "AWS"]
    }
  ],
  "filename": "resume.pdf",
  "processing_time_seconds": 2.34
}
```

### NER Entities Response
```json
{
  "entities": [
    {
      "word": "Google",
      "entity_group": "COMPANY",
      "score": 0.95,
      "start": 20,
      "end": 26
    },
    {
      "word": "Software Engineer",
      "entity_group": "ROLE",
      "score": 0.92,
      "start": 30,
      "end": 47
    }
  ],
  "text_analyzed": "John Doe worked at Google as Software Engineer",
  "entity_count": 2,
  "processing_time_seconds": 0.45
}
```

## 🔒 Production Considerations

1. **CORS**: Update CORS settings in `.env` for production domains
2. **Authentication**: Add API key or OAuth authentication
3. **Rate Limiting**: Implement rate limiting for public APIs
4. **File Storage**: Use cloud storage (S3, GCS) for uploaded files
5. **Job Queue**: Use Redis/Celery for better batch job management
6. **Monitoring**: Add logging, metrics (Prometheus), and tracing
7. **HTTPS**: Deploy behind nginx/Apache with SSL certificate

## 🐛 Troubleshooting

**Model not found**:
- Ensure `ml_model` directory exists with trained model files
- Check `MODEL_PATH` in `.env`

**spaCy errors**:
- Install model: `python -m spacy download en_core_web_sm`

**Import errors**:
- Ensure all dependencies: `pip install -r requirements.txt`

**Port already in use**:
- Change port in `.env` or use: `uvicorn src.api.main:app --port 8001`

## 📝 License

MIT License

## 🤝 Contributing

Contributions welcome! Please open an issue or submit a pull request.

## 📧 Support

For issues and questions, please open a GitHub issue.
