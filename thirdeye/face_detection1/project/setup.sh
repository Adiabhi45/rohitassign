#!/bin/bash
# Production Quick Start Script

set -e  # Exit on error

echo "=========================================="
echo "Face Recognition System - Quick Setup"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "[ERROR] .env file not found!"
    echo "Please create .env file from .env.example:"
    echo "  cp .env.example .env"
    echo "Then edit .env and set your SECRET_KEY"
    echo ""
    echo "Generate a secure SECRET_KEY with:"
    echo "  python3 -c 'import secrets; print(secrets.token_hex(32))'"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "[INFO] Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
echo "[INFO] Creating directories..."
mkdir -p logs output reference_database

# Check if reference images exist
ref_count=$(ls -1 reference_database/*.{jpg,jpeg,png,gif,bmp} 2>/dev/null | wc -l)
if [ $ref_count -eq 0 ]; then
    echo "[WARNING] No reference images found in reference_database/"
    echo "Please add face images to reference_database/ folder"
fi

# Initialize database
echo "[INFO] Initializing database..."
python3 -c "from app import init_db; init_db()"

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "To start the application:"
echo ""
echo "Development mode:"
echo "  python3 app.py"
echo ""
echo "Production mode (with Gunicorn):"
echo "  gunicorn -c gunicorn_config.py app:app"
echo ""
echo "The application will be available at:"
echo "  http://127.0.0.1:5000 (development)"
echo "  http://127.0.0.1:8000 (production)"
echo ""
echo "Default login credentials:"
echo "  Email: admin@facesketch.com"
echo "  OTP will be displayed in console"
echo ""
