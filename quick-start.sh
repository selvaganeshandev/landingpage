#!/bin/bash
# Quick Start - Start all services in background mode without prompts

# Configuration
PROJECT_DIR="/home/hts-005/Documents/python/v3.12/llm-monitor"
PYTHON_PATH="/home/hts-005/Documents/python/v3.12/env/bin/python"
VENV_PATH="/home/hts-005/Documents/python/v3.12/env"
BACKEND_DIR="$PROJECT_DIR/backend"
ENGINE_DIR="$PROJECT_DIR/engine"
FRONTEND_DIR="$PROJECT_DIR/frontend"

# Ports
BACKEND_PORT=8000
ENGINE_PORT=8001
FRONTEND_PORT=8080

# Log files
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# Kill existing processes on ports
lsof -ti:$BACKEND_PORT | xargs kill -9 2>/dev/null
lsof -ti:$ENGINE_PORT | xargs kill -9 2>/dev/null
lsof -ti:$FRONTEND_PORT | xargs kill -9 2>/dev/null

# Start Backend
cd "$BACKEND_DIR"
nohup $PYTHON_PATH manage.py runserver $BACKEND_PORT > "$LOG_DIR/backend.log" 2>&1 &
echo $! > "$LOG_DIR/backend.pid"
echo "✓ Backend started on port $BACKEND_PORT"

# Start Engine
cd "$ENGINE_DIR"
nohup $PYTHON_PATH manage.py runserver $ENGINE_PORT > "$LOG_DIR/engine.log" 2>&1 &
echo $! > "$LOG_DIR/engine.pid"
echo "✓ Engine started on port $ENGINE_PORT"

# Start Frontend
cd "$FRONTEND_DIR"
nohup npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
echo $! > "$LOG_DIR/frontend.pid"
echo "✓ Frontend started on port $FRONTEND_PORT"

echo ""
echo "=========================================="
echo "All services started!"
echo "=========================================="
echo "Backend:  http://localhost:$BACKEND_PORT"
echo "Engine:   http://localhost:$ENGINE_PORT"
echo "Frontend: http://localhost:$FRONTEND_PORT"
echo ""
echo "Logs: $LOG_DIR/"
echo "Stop: ./stop-all.sh"

