#!/bin/bash

# ResumeAnalyser-Azure - Local Development Script

echo "==================================="
echo "ResumeAnalyser-Azure - Local Setup"
echo "==================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.12+"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "Python version: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found!"
    echo "Please create .env file from .env.example and add your credentials"
    exit 1
fi

# Initialize database
echo "Initializing database..."
python migrations/init_db.py

# Run the application
echo ""
echo "==================================="
echo "Starting Flask application..."
echo "Access the app at: http://localhost:5000"
echo "==================================="
echo ""

python app.py