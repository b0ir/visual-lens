#!/bin/bash
echo "Starting VisualLens Development Servers..."

# Start Backend
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start Frontend
cd ../frontend
npm run dev -- --port 3000 &
FRONTEND_PID=$!

echo "================================================="
echo "🚀 VisualLens is running!"
echo "📡 Backend (FastAPI): http://localhost:8000"
echo "🖥️  Frontend (React):  http://localhost:3000"
echo "⚠️  Press Ctrl+C to stop both servers."
echo "================================================="

# Trap Ctrl+C to kill both background processes
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT TERM
wait
