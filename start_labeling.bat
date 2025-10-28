@echo off
REM Quick Start Script for Resume Labeling System (Windows)

echo.
echo 🚀 Resume Labeling System - Quick Start
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\" if not exist ".venv\" (
    echo ⚠️  No virtual environment found.
    echo Creating virtual environment...
    python -m venv venv
    echo ✓ Virtual environment created
    echo.
)

REM Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

echo 📦 Installing/Updating dependencies...
pip install -q streamlit PyMuPDF pandas numpy pillow

echo.
echo ✓ Dependencies installed
echo.

REM Test feature extraction first
echo 🧪 Testing feature extraction...
python test_labeling.py

echo.
echo ========================================
echo 🎯 Starting Streamlit Labeling App...
echo ========================================
echo.
echo 📝 Instructions:
echo   1. Open http://localhost:8501 in your browser
echo   2. Configure PDF directory in sidebar (default: ./freshteams_resume/Resumes)
echo   3. Review PDF and click Type 1/2/3 to label
echo   4. Progress is auto-saved to dataset.csv
echo   5. Press Ctrl+C to stop
echo.
echo Starting in 3 seconds...
timeout /t 3 /nobreak > nul

streamlit run label_resumes.py --server.port 8501
