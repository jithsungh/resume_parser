@echo off
REM Resume Parser API - Windows Startup Script

echo ======================================
echo Resume Parser API - Server Startup
echo ======================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo WARNING: Virtual environment not found. Creating one...
    python -m venv venv
    echo Virtual environment created
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install/Update dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Download spaCy model if needed
echo Checking spaCy model...
python -m spacy download en_core_web_sm

REM Check if model exists
if not exist "ml_model\" (
    echo WARNING: ML model not found at .\ml_model
    echo    Please ensure your trained model is in the ml_model directory
    echo.
)

REM Set default environment variables if .env doesn't exist
if not exist ".env" (
    echo Creating default .env file...
    (
        echo # Resume Parser API Configuration
        echo MODEL_PATH=./ml_model
        echo HOST=0.0.0.0
        echo PORT=8000
        echo RELOAD=True
        echo MAX_BATCH_SIZE=100
        echo WORKER_THREADS=4
        echo LOG_LEVEL=INFO
    ) > .env
    echo .env file created
)

echo.
echo ======================================
echo Starting FastAPI Server
echo ======================================
echo.

REM Start the server
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
