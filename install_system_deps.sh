#!/bin/bash
# Install system dependencies for OpenCV on Linux

echo "Installing system dependencies for resume parser..."

# Detect OS
if [ -f /etc/redhat-release ]; then
    # RHEL/CentOS/Fedora/Amazon Linux
    echo "Detected RHEL-based system"
    sudo yum install -y mesa-libGL
elif [ -f /etc/debian_version ]; then
    # Debian/Ubuntu
    echo "Detected Debian-based system"
    sudo apt-get update
    sudo apt-get install -y libgl1-mesa-glx libglib2.0-0
else
    echo "Unknown OS. Please install OpenGL libraries manually:"
    echo "  RHEL/CentOS/Amazon Linux: sudo yum install mesa-libGL"
    echo "  Ubuntu/Debian: sudo apt-get install libgl1-mesa-glx"
    exit 1
fi

echo "✅ System dependencies installed successfully!"
echo "Now you can start the API server:"
echo "  python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
