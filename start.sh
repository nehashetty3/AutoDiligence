#!/bin/bash
set -e

MODE="${1:-dev}"

if [ "$MODE" = "docker" ]; then
    echo "Starting AutoDiligence with Docker Compose..."
    docker compose up --build -d
    echo ""
    echo "AutoDiligence is running at: http://localhost"
    echo "API health check: http://localhost/health"
    exit 0
fi

echo "Starting AutoDiligence in local development mode..."
source venv/bin/activate
brew services start postgresql@15 2>/dev/null || true

python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID)"
sleep 3

cd frontend
npm start &
FRONTEND_PID=$!
cd ..
echo "Frontend started (PID: $FRONTEND_PID)"

echo ""
echo "Frontend: http://localhost:3000"
echo "Backend:  http://localhost:8000"
echo ""
echo "Use './start.sh docker' for the production-style Docker stack."

wait
