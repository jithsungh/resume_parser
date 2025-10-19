#!/bin/bash
# Installation and Quick Test Script for Robust Pipeline

echo "=========================================="
echo "Robust Resume Parser - Installation"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python --version

if [ $? -ne 0 ]; then
    echo "❌ Python is not installed or not in PATH"
    exit 1
fi

echo "✅ Python found"
echo ""

# Install dependencies
echo "Installing required packages..."
echo "(This may take several minutes)"
echo ""

pip install --upgrade pip

# Install core dependencies
pip install opencv-python>=4.8.0
pip install tqdm>=4.66.0

# Install existing dependencies if not already present
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Package installation failed"
    exit 1
fi

echo ""
echo "✅ All packages installed successfully"
echo ""

# Run a quick test if test file is provided
if [ -z "$1" ]; then
    echo "=========================================="
    echo "Installation Complete!"
    echo "=========================================="
    echo ""
    echo "To test the robust pipeline, run:"
    echo ""
    echo "  python src/ROBUST_pipeline/test_robust.py --pdf <path_to_resume.pdf>"
    echo ""
    echo "Or batch process a folder:"
    echo ""
    echo "  python -m src.ROBUST_pipeline.batch_process \\"
    echo "    --input <resume_folder> \\"
    echo "    --output <output_folder> \\"
    echo "    --workers 4"
    echo ""
    echo "For more information, see:"
    echo "  - src/ROBUST_pipeline/QUICKSTART.md"
    echo "  - src/ROBUST_pipeline/README.md"
    echo ""
else
    echo "=========================================="
    echo "Running Quick Test"
    echo "=========================================="
    echo ""
    echo "Testing on: $1"
    echo ""
    
    python src/ROBUST_pipeline/test_robust.py --pdf "$1"
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Test completed successfully!"
        echo ""
        echo "Check the output above to see:"
        echo "  - Detected sections"
        echo "  - Processing time"
        echo "  - Comparison with standard pipeline"
    else
        echo ""
        echo "⚠️ Test encountered an error"
        echo "Check the error messages above for details"
    fi
fi

echo ""
echo "=========================================="
echo "Next Steps"
echo "=========================================="
echo ""
echo "1. Test on your resume collection:"
echo "   python src/ROBUST_pipeline/test_robust.py --pdf your_resume.pdf"
echo ""
echo "2. Compare with standard pipeline:"
echo "   (Test script runs both automatically)"
echo ""
echo "3. Batch process multiple resumes:"
echo "   python -m src.ROBUST_pipeline.batch_process \\"
echo "     --input freshteams_resume/Automation\\ Testing/ \\"
echo "     --output outputs/robust_results/ \\"
echo "     --workers 4"
echo ""
echo "4. Check documentation:"
echo "   cat src/ROBUST_pipeline/QUICKSTART.md"
echo ""
