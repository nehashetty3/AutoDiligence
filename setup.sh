#!/bin/bash
set -e

echo "============================================"
echo "  AutoDiligence — Setup Script"
echo "============================================"

MODE="${1:-local}"

if [ "$MODE" = "docker" ]; then
    if ! command -v docker > /dev/null; then
        echo "ERROR: Docker is required for docker setup."
        exit 1
    fi

    if [ ! -f ".env" ]; then
        cp .env.example .env
        echo "Created .env from .env.example"
        echo "Fill in your real API keys before deploying."
    fi

    echo "Docker setup complete."
    echo "Run './start.sh docker' to build and start the production stack."
    exit 0
fi

if ! command -v python3.11 > /dev/null; then
    echo "ERROR: Python 3.11 not found. Run: brew install python@3.11"
    exit 1
fi

if ! command -v psql > /dev/null; then
    echo "ERROR: PostgreSQL not found. Run: brew install postgresql@15"
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3.11 -m venv venv
fi

source venv/bin/activate

echo "Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "Downloading spaCy model..."
python -m spacy download en_core_web_lg -q

echo "Setting up local database..."
brew services start postgresql@15 2>/dev/null || true
sleep 2
createdb ma_diligence 2>/dev/null || echo "Database already exists"
python backend/database/schema.py

echo "Installing frontend dependencies..."
cd frontend
npm install -q
cd ..

echo ""
echo "============================================"
echo "  Setup Complete!"
echo "============================================"
echo ""
echo "Local development:"
echo "  ./start.sh"
echo ""
echo "Production-style Docker setup:"
echo "  ./setup.sh docker"
echo "  ./start.sh docker"
echo ""
echo "Frontend: http://localhost:3000"
echo "API:      http://localhost:8000"
