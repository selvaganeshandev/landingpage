#!/bin/bash
# Stop All Services for LLM Monitor

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/home/hts-005/Documents/python/v3.12/llm-monitor"
LOG_DIR="$PROJECT_DIR/logs"

# Ports
BACKEND_PORT=8000
ENGINE_PORT=8001
FRONTEND_PORT=8080

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   LLM Monitor - Stop All Services${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to kill process by PID file
kill_by_pid_file() {
    local pid_file=$1
    local service_name=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${YELLOW}Stopping $service_name (PID: $pid)...${NC}"
            kill -9 $pid 2>/dev/null
            rm -f "$pid_file"
            echo -e "${GREEN}✓ $service_name stopped${NC}"
        else
            echo -e "${YELLOW}$service_name process not found (PID: $pid)${NC}"
            rm -f "$pid_file"
        fi
    else
        echo -e "${YELLOW}$service_name PID file not found${NC}"
    fi
}

# Function to kill process on port
kill_port() {
    local port=$1
    local service_name=$2
    local pid=$(lsof -ti:$port 2>/dev/null)
    
    if [ ! -z "$pid" ]; then
        echo -e "${YELLOW}Stopping $service_name on port $port (PID: $pid)...${NC}"
        kill -9 $pid 2>/dev/null
        sleep 1
        echo -e "${GREEN}✓ $service_name stopped${NC}"
    else
        echo -e "${YELLOW}$service_name not running on port $port${NC}"
    fi
}

# Stop services by PID files (if running in background mode)
echo -e "${CYAN}Stopping services by PID files...${NC}"
kill_by_pid_file "$LOG_DIR/backend.pid" "Backend"
kill_by_pid_file "$LOG_DIR/engine.pid" "Engine"
kill_by_pid_file "$LOG_DIR/frontend.pid" "Frontend"
echo ""

# Stop services by port (fallback)
echo -e "${CYAN}Stopping services by port...${NC}"
kill_port $BACKEND_PORT "Backend"
kill_port $ENGINE_PORT "Engine"
kill_port $FRONTEND_PORT "Frontend"
echo ""

# Stop any remaining Django processes
echo -e "${CYAN}Stopping any remaining Django processes...${NC}"
pkill -f "manage.py runserver" 2>/dev/null && echo -e "${GREEN}✓ Django processes stopped${NC}" || echo -e "${YELLOW}No Django processes found${NC}"
echo ""

# Stop any remaining Node/Vite processes
echo -e "${CYAN}Stopping any remaining Node/Vite processes...${NC}"
pkill -f "vite" 2>/dev/null && echo -e "${GREEN}✓ Vite processes stopped${NC}" || echo -e "${YELLOW}No Vite processes found${NC}"
pkill -f "npm run dev" 2>/dev/null && echo -e "${GREEN}✓ npm dev processes stopped${NC}" || echo -e "${YELLOW}No npm dev processes found${NC}"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   All Services Stopped!${NC}"
echo -e "${GREEN}========================================${NC}"

