@echo off
REM Advanced Resume Labeling Tool - Windows Startup Script

echo ========================================
echo Advanced Resume Labeling Tool
echo ========================================
echo.

REM Activate virtual environment
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo Virtual environment activated
) else (
    echo WARNING: Virtual environment not found
    echo Run: python -m venv venv
    pause
    exit /b 1
)

echo.
echo Starting labeling tool...
echo.

REM Run the tool
python advanced_labeling_tool.py --pdf-dir Resumes --output labeled_dataset.csv

pause
