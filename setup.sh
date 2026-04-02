#!/bin/bash
echo "============================================"
echo "  AutoDiligence — Setup Script"
echo "============================================"

# Check Python
if ! command -v python3.11 &> /dev/null; then
    echo "ERROR: Python 3.11 not found. Run: brew install python@3.11"
    exit 1
fi

# Check PostgreSQL
if ! command -v psql &> /dev/null; then
    echo "ERROR: PostgreSQL not found. Run: brew install postgresql@15"
    exit 1
fi

# Create venv if not exists
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

echo "Setting up database..."
brew services start postgresql@15 2>/dev/null || true
sleep 2
createdb ma_diligence 2>/dev/null || echo "Database already exists"
python backend/database/schema.py

echo "Training ML models..."
cd backend && python -m models.model_trainer && cd ..

echo "Installing frontend dependencies..."
cd frontend && npm install -q && cd ..

echo ""
echo "============================================"
echo "  Setup Complete!"
echo "============================================"
echo ""
echo "Before starting, make sure your .env file has:"
echo "  - OPENAI_API_KEY"
echo "  - NEWS_API_KEY"
echo "  - PINECONE_API_KEY"
echo ""
echo "To start the application:"
echo "  Terminal 1: source venv/bin/activate && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"
echo "  Terminal 2: cd frontend && npm start"
echo ""
echo "Open: http://localhost:3000"
