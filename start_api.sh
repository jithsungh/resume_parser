#!/bin/bash

# Resume Parser API - Startup Script

echo "======================================"
echo "Resume Parser API - Server Startup"
echo "======================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Creating one..."
    python -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/Update dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Download spaCy model if needed
echo "🔍 Checking spaCy model..."
python -m spacy download en_core_web_sm 2>/dev/null || echo "✅ spaCy model already installed"

# Check if model exists
if [ ! -d "ml_model" ]; then
    echo "⚠️  WARNING: ML model not found at ./ml_model"
    echo "   Please ensure your trained model is in the ml_model directory"
    echo ""
fi

# Set default environment variables if .env doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating default .env file..."
    cat > .env << EOF
# Resume Parser API Configuration
MODEL_PATH=./ml_model
HOST=0.0.0.0
PORT=8000
RELOAD=True
MAX_BATCH_SIZE=100
WORKER_THREADS=4
LOG_LEVEL=INFO
EOF
    echo "✅ .env file created"
fi

echo ""
echo "======================================"
echo "🚀 Starting FastAPI Server"
echo "======================================"
echo ""

# Start the server
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
