#!/bin/bash
# Restart Services for LLM Monitor (macOS)
# Usage: ./restart.sh [backend|engine|celery|frontend|all]

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

# Function to restart backend
restart_backend() {
    echo -e "${BLUE}Restarting Backend...${NC}"
    kill_port $BACKEND_PORT
    cd "$BACKEND_DIR"
    nohup "$VENV_PYTHON" manage.py runserver $BACKEND_PORT > "$BACKEND_LOG" 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > "$LOG_DIR/backend.pid"
    sleep 2
    echo -e "${GREEN}✓ Backend restarted (PID: $BACKEND_PID) - http://localhost:$BACKEND_PORT${NC}"
}

# Function to restart engine
restart_engine() {
    echo -e "${BLUE}Restarting Engine...${NC}"
    kill_port $ENGINE_PORT
    cd "$ENGINE_DIR"
    nohup "$VENV_PYTHON" manage.py runserver $ENGINE_PORT > "$ENGINE_LOG" 2>&1 &
    ENGINE_PID=$!
    echo $ENGINE_PID > "$LOG_DIR/engine.pid"
    sleep 2
    echo -e "${GREEN}✓ Engine restarted (PID: $ENGINE_PID) - http://localhost:$ENGINE_PORT${NC}"
}

# Function to restart celery
restart_celery() {
    echo -e "${BLUE}Restarting Celery...${NC}"
    pkill -f 'celery.*worker' 2>/dev/null
    pkill -f 'celery.*beat' 2>/dev/null
    sleep 1

    cd "$ENGINE_DIR"

    # Start Celery Worker
    nohup "$VENV_PYTHON" -m celery -A llm_monitor_engine worker --loglevel=info > "$CELERY_WORKER_LOG" 2>&1 &
    CELERY_WORKER_PID=$!
    echo $CELERY_WORKER_PID > "$LOG_DIR/celery-worker.pid"
    echo -e "${GREEN}✓ Celery Worker restarted (PID: $CELERY_WORKER_PID)${NC}"
    sleep 2

    # Start Celery Beat
    nohup "$VENV_PYTHON" -m celery -A llm_monitor_engine beat --loglevel=info > "$CELERY_BEAT_LOG" 2>&1 &
    CELERY_BEAT_PID=$!
    echo $CELERY_BEAT_PID > "$LOG_DIR/celery-beat.pid"
    echo -e "${GREEN}✓ Celery Beat restarted (PID: $CELERY_BEAT_PID)${NC}"
}

# Function to restart frontend
restart_frontend() {
    echo -e "${BLUE}Restarting Frontend...${NC}"
    kill_port $FRONTEND_PORT
    cd "$FRONTEND_DIR"
    nohup npm run dev > "$FRONTEND_LOG" 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "$LOG_DIR/frontend.pid"
    sleep 3
    echo -e "${GREEN}✓ Frontend restarted (PID: $FRONTEND_PID) - http://localhost:$FRONTEND_PORT${NC}"
}

# Function to show menu
show_menu() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}   LLM Monitor - Restart Services${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo -e "Select service to restart:"
    echo -e "  ${CYAN}1${NC}) Backend  (Django - port $BACKEND_PORT)"
    echo -e "  ${CYAN}2${NC}) Engine   (Django - port $ENGINE_PORT)"
    echo -e "  ${CYAN}3${NC}) Celery   (Worker + Beat)"
    echo -e "  ${CYAN}4${NC}) Frontend (Vite - port $FRONTEND_PORT)"
    echo -e "  ${CYAN}5${NC}) All services"
    echo -e "  ${CYAN}q${NC}) Quit"
    echo ""
}

# Function to handle selection
handle_selection() {
    local choice=$1
    case $choice in
        1|backend)
            restart_backend
            ;;
        2|engine)
            restart_engine
            ;;
        3|celery)
            restart_celery
            ;;
        4|frontend)
            restart_frontend
            ;;
        5|all)
            restart_backend
            echo ""
            restart_engine
            echo ""
            restart_celery
            echo ""
            restart_frontend
            ;;
        q|quit)
            echo -e "${YELLOW}Bye!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option: $choice${NC}"
            return 1
            ;;
    esac
}

# Main
if [ ! -z "$1" ]; then
    # Argument provided, restart directly
    handle_selection "$1"
else
    # Interactive mode
    while true; do
        show_menu
        read -p "Enter choice [1-5, q]: " choice
        echo ""
        handle_selection "$choice"
        if [ $? -eq 0 ]; then
            echo ""
            read -p "Press Enter to continue..."
            echo ""
        fi
    done
fi
