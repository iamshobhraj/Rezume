#!/bin/bash

# Resume Intelligence Engine Startup Script
# Starts the FastAPI backend and Vite frontend services concurrently.

# Exit immediately if a command exits with a non-zero status
set -e

# Store the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to handle shutdown of background processes
cleanup() {
    echo ""
    echo "========================================="
    echo "Stopping all services..."
    echo "========================================="
    
    # Send SIGTERM to the process group or the specific PIDs
    if [ -n "$BACKEND_PID" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    exit 0
}

# Trap Ctrl+C (SIGINT) and SIGTERM to clean up background processes
trap cleanup SIGINT SIGTERM

echo "========================================="
# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: 'uv' command not found. Please install uv (https://github.com/astral-sh/uv) or run manually."
    exit 1
fi

# Check if node/npm is installed
if ! command -v npm &> /dev/null; then
    echo "Error: 'npm' command not found. Please install Node.js/npm."
    exit 1
fi

# 1. Initialize Backend
echo "Setting up Backend..."
cd "$PROJECT_ROOT/backend"
if [ ! -d ".venv" ]; then
    echo ".venv not found in backend, syncing dependencies with 'uv sync'..."
    uv sync
fi

# Start Backend
echo "Starting Backend on http://localhost:8000..."
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to be ready before starting frontend
echo "Waiting for backend to start..."
python3 -c "
import socket
import time
for _ in range(60):
    try:
        s = socket.socket()
        s.connect(('127.0.0.1', 8000))
        s.close()
        break
    except Exception:
        time.sleep(0.5)
"

# 2. Initialize Frontend
echo "Setting up Frontend..."
cd "$PROJECT_ROOT/frontend"
if [ ! -d "node_modules" ]; then
    echo "node_modules not found in frontend, installing dependencies with 'npm install'..."
    npm install
fi

# Start Frontend
echo "Starting Frontend on http://localhost:5173..."
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!

cd "$PROJECT_ROOT"

echo "========================================="
echo "Both services are running successfully!"
echo "- Backend:  http://localhost:8000 (API)"
echo "- Frontend: http://localhost:5173"
echo "Press Ctrl+C to stop both services."
echo "========================================="

# Wait for background processes to finish (keeps the script running)
wait $BACKEND_PID $FRONTEND_PID
