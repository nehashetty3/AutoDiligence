#!/bin/bash
echo "Starting AutoDiligence..."
source venv/bin/activate
brew services start postgresql@15 2>/dev/null || true

# Start backend in background
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID)"
sleep 3

# Start frontend
cd frontend && npm start &
FRONTEND_PID=$!
echo "Frontend started (PID: $FRONTEND_PID)"

echo ""
echo "AutoDiligence running at: http://localhost:3000"
echo "API running at: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop"

wait
