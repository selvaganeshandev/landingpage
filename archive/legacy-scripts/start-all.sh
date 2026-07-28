#!/bin/bash
# Start All Services for LLM Monitor (macOS)
# This script starts: Backend (Django), Engine (Django), Celery, Frontend (Vite)

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$SCRIPT_DIR"
VENV_PYTHON="$PROJECT_DIR/backend/.venv/bin/python3"
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
BACKEND_LOG="$LOG_DIR/backend.log"
ENGINE_LOG="$LOG_DIR/engine.log"
CELERY_WORKER_LOG="$LOG_DIR/celery-worker.log"
CELERY_BEAT_LOG="$LOG_DIR/celery-beat.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   LLM Monitor - All Services Startup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to kill process on a port
kill_port() {
    local port=$1
    local pid=$(lsof -ti:$port)
    if [ ! -z "$pid" ]; then
        echo -e "${YELLOW}Killing process on port $port (PID: $pid)...${NC}"
        kill -9 $pid 2>/dev/null
        sleep 1
    fi
}

# Check and clean ports
echo -e "${YELLOW}[1/7] Checking ports...${NC}"
if check_port $BACKEND_PORT; then
    echo -e "${YELLOW}Port $BACKEND_PORT is in use. Cleaning up...${NC}"
    kill_port $BACKEND_PORT
fi
if check_port $ENGINE_PORT; then
    echo -e "${YELLOW}Port $ENGINE_PORT is in use. Cleaning up...${NC}"
    kill_port $ENGINE_PORT
fi
if check_port $FRONTEND_PORT; then
    echo -e "${YELLOW}Port $FRONTEND_PORT is in use. Cleaning up...${NC}"
    kill_port $FRONTEND_PORT
fi
echo -e "${GREEN}✓ Ports checked${NC}"
echo ""

# Check Redis
echo -e "${YELLOW}[2/7] Checking Redis...${NC}"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis is running${NC}"
else
    echo -e "${YELLOW}Starting Redis...${NC}"
    brew services start redis
    sleep 2
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Redis started${NC}"
    else
        echo -e "${RED}✗ Failed to start Redis${NC}"
        exit 1
    fi
fi
echo ""

# Check Python and venv
echo -e "${YELLOW}[3/7] Checking Python environment...${NC}"
if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "${RED}✗ Virtual environment not found at $VENV_PYTHON${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python environment ready${NC}"
echo ""

# Start Backend
echo -e "${YELLOW}[4/7] Starting Backend (Django on port $BACKEND_PORT)...${NC}"
cd "$BACKEND_DIR"
nohup "$VENV_PYTHON" manage.py runserver $BACKEND_PORT > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$LOG_DIR/backend.pid"
echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"
sleep 2

# Start Engine
echo ""
echo -e "${YELLOW}[5/7] Starting Engine (Django on port $ENGINE_PORT)...${NC}"
cd "$ENGINE_DIR"
nohup "$VENV_PYTHON" manage.py runserver $ENGINE_PORT > "$ENGINE_LOG" 2>&1 &
ENGINE_PID=$!
echo $ENGINE_PID > "$LOG_DIR/engine.pid"
echo -e "${GREEN}✓ Engine started (PID: $ENGINE_PID)${NC}"
sleep 2

# Start Celery Worker and Beat
echo ""
echo -e "${YELLOW}[6/7] Starting Celery Worker and Beat...${NC}"
cd "$ENGINE_DIR"

# Kill any existing celery processes
pkill -f 'celery.*worker' 2>/dev/null
pkill -f 'celery.*beat' 2>/dev/null
sleep 1

# Start Celery Worker
nohup "$VENV_PYTHON" -m celery -A llm_monitor_engine worker --loglevel=info > "$CELERY_WORKER_LOG" 2>&1 &
CELERY_WORKER_PID=$!
echo $CELERY_WORKER_PID > "$LOG_DIR/celery-worker.pid"
echo -e "${GREEN}✓ Celery Worker started (PID: $CELERY_WORKER_PID)${NC}"
sleep 2

# Start Celery Beat
nohup "$VENV_PYTHON" -m celery -A llm_monitor_engine beat --loglevel=info > "$CELERY_BEAT_LOG" 2>&1 &
CELERY_BEAT_PID=$!
echo $CELERY_BEAT_PID > "$LOG_DIR/celery-beat.pid"
echo -e "${GREEN}✓ Celery Beat started (PID: $CELERY_BEAT_PID)${NC}"
sleep 2

# Start Frontend
echo ""
echo -e "${YELLOW}[7/7] Starting Frontend (Vite on port $FRONTEND_PORT)...${NC}"
cd "$FRONTEND_DIR"
nohup npm run dev > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$LOG_DIR/frontend.pid"
echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"
sleep 3

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   All Services Started Successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${CYAN}Service URLs:${NC}"
echo -e "  Backend:  ${GREEN}http://localhost:$BACKEND_PORT${NC}"
echo -e "  Engine:   ${GREEN}http://localhost:$ENGINE_PORT${NC}"
echo -e "  Frontend: ${GREEN}http://localhost:$FRONTEND_PORT${NC}"
echo ""
echo -e "${CYAN}Log Files:${NC}"
echo -e "  Backend:       $BACKEND_LOG"
echo -e "  Engine:        $ENGINE_LOG"
echo -e "  Celery Worker: $CELERY_WORKER_LOG"
echo -e "  Celery Beat:   $CELERY_BEAT_LOG"
echo -e "  Frontend:      $FRONTEND_LOG"
echo ""
echo -e "${YELLOW}To stop all services, run:${NC}"
echo -e "  ${CYAN}./stop-all.sh${NC}"
echo ""
echo -e "${YELLOW}To view logs:${NC}"
echo -e "  ${CYAN}tail -f $BACKEND_LOG${NC}"
echo -e "  ${CYAN}tail -f $ENGINE_LOG${NC}"
echo -e "  ${CYAN}tail -f $CELERY_WORKER_LOG${NC}"
echo -e "  ${CYAN}tail -f $FRONTEND_LOG${NC}"
echo ""
