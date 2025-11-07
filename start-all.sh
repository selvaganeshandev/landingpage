#!/bin/bash
# Start All Services for LLM Monitor
# This script starts: Backend (Django), Engine (Django), Frontend (Vite)

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

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
BACKEND_LOG="$LOG_DIR/backend.log"
ENGINE_LOG="$LOG_DIR/engine.log"
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
echo -e "${YELLOW}[1/5] Checking ports...${NC}"
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

# Activate virtual environment
echo -e "${YELLOW}[2/5] Activating virtual environment...${NC}"
if [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
else
    echo -e "${RED}✗ Virtual environment not found at $VENV_PATH${NC}"
    exit 1
fi
echo ""

# Check Python path
if [ ! -f "$PYTHON_PATH" ]; then
    echo -e "${RED}✗ Python not found at $PYTHON_PATH${NC}"
    exit 1
fi

# Ask user for startup mode
echo -e "${CYAN}Startup Mode:${NC}"
echo "1) Foreground (all services in current terminal - Ctrl+C to stop all)"
echo "2) Background (all services in background - use stop script to stop)"
echo "3) Separate terminals (opens new terminal windows for each service)"
read -p "Enter choice [1-3] (default: 2): " mode
mode=${mode:-2}

echo ""
echo -e "${YELLOW}[3/5] Starting Backend (Django on port $BACKEND_PORT)...${NC}"
cd "$BACKEND_DIR"
if [ "$mode" == "3" ]; then
    # Open in new terminal
    gnome-terminal --title="Backend (Port $BACKEND_PORT)" -- bash -c "source $VENV_PATH/bin/activate && cd $BACKEND_DIR && $PYTHON_PATH manage.py runserver $BACKEND_PORT; exec bash"
    echo -e "${GREEN}✓ Backend started in new terminal${NC}"
elif [ "$mode" == "2" ]; then
    # Background mode
    nohup $PYTHON_PATH manage.py runserver $BACKEND_PORT > "$BACKEND_LOG" 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > "$LOG_DIR/backend.pid"
    echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID, Log: $BACKEND_LOG)${NC}"
else
    # Foreground mode - will be started in background and then we'll wait
    $PYTHON_PATH manage.py runserver $BACKEND_PORT > "$BACKEND_LOG" 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > "$LOG_DIR/backend.pid"
    echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"
fi
sleep 2

echo ""
echo -e "${YELLOW}[4/5] Starting Engine (Django on port $ENGINE_PORT)...${NC}"
cd "$ENGINE_DIR"
if [ "$mode" == "3" ]; then
    # Open in new terminal
    gnome-terminal --title="Engine (Port $ENGINE_PORT)" -- bash -c "source $VENV_PATH/bin/activate && cd $ENGINE_DIR && $PYTHON_PATH manage.py runserver $ENGINE_PORT; exec bash"
    echo -e "${GREEN}✓ Engine started in new terminal${NC}"
elif [ "$mode" == "2" ]; then
    # Background mode
    nohup $PYTHON_PATH manage.py runserver $ENGINE_PORT > "$ENGINE_LOG" 2>&1 &
    ENGINE_PID=$!
    echo $ENGINE_PID > "$LOG_DIR/engine.pid"
    echo -e "${GREEN}✓ Engine started (PID: $ENGINE_PID, Log: $ENGINE_LOG)${NC}"
else
    # Foreground mode
    $PYTHON_PATH manage.py runserver $ENGINE_PORT > "$ENGINE_LOG" 2>&1 &
    ENGINE_PID=$!
    echo $ENGINE_PID > "$LOG_DIR/engine.pid"
    echo -e "${GREEN}✓ Engine started (PID: $ENGINE_PID)${NC}"
fi
sleep 2

echo ""
echo -e "${YELLOW}[5/5] Starting Frontend (Vite on port $FRONTEND_PORT)...${NC}"
cd "$FRONTEND_DIR"
if [ "$mode" == "3" ]; then
    # Open in new terminal
    gnome-terminal --title="Frontend (Port $FRONTEND_PORT)" -- bash -c "cd $FRONTEND_DIR && npm run dev; exec bash"
    echo -e "${GREEN}✓ Frontend started in new terminal${NC}"
elif [ "$mode" == "2" ]; then
    # Background mode
    nohup npm run dev > "$FRONTEND_LOG" 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "$LOG_DIR/frontend.pid"
    echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID, Log: $FRONTEND_LOG)${NC}"
else
    # Foreground mode
    npm run dev > "$FRONTEND_LOG" 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "$LOG_DIR/frontend.pid"
    echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"
fi
sleep 2

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

if [ "$mode" == "2" ]; then
    echo -e "${CYAN}Log Files:${NC}"
    echo -e "  Backend:  $BACKEND_LOG"
    echo -e "  Engine:   $ENGINE_LOG"
    echo -e "  Frontend: $FRONTEND_LOG"
    echo ""
    echo -e "${YELLOW}To stop all services, run:${NC}"
    echo -e "  ${CYAN}./stop-all.sh${NC}"
    echo ""
    echo -e "${YELLOW}To view logs:${NC}"
    echo -e "  ${CYAN}tail -f $BACKEND_LOG${NC}"
    echo -e "  ${CYAN}tail -f $ENGINE_LOG${NC}"
    echo -e "  ${CYAN}tail -f $FRONTEND_LOG${NC}"
elif [ "$mode" == "1" ]; then
    echo -e "${YELLOW}All services running in foreground. Press Ctrl+C to stop all.${NC}"
    echo ""
    # Wait for all background processes
    wait
fi

