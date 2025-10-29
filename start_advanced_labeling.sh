#!/bin/bash
# Advanced Resume Labeling Tool - Linux/Mac Startup Script

echo "========================================"
echo "Advanced Resume Labeling Tool"
echo "========================================"
echo ""

# Activate virtual environment
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
    echo "Virtual environment activated"
else
    echo "WARNING: Virtual environment not found"
    echo "Run: python -m venv venv"
    exit 1
fi

echo ""
echo "Starting labeling tool..."
echo ""

# Run the tool
python advanced_labeling_tool.py --pdf-dir Resumes --output labeled_dataset.csv
