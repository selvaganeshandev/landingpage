#!/bin/bash
# Start Celery Worker and Beat for LLM Monitor Engine

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   LLM Monitor - Celery Startup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if Redis is running
echo -e "${YELLOW}[1/5] Checking Redis...${NC}"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis is running${NC}"
else
    echo -e "${RED}✗ Redis is not running!${NC}"
    echo -e "${YELLOW}Starting Redis...${NC}"
    sudo systemctl start redis
    sleep 2
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Redis started successfully${NC}"
    else
        echo -e "${RED}✗ Failed to start Redis${NC}"
        echo -e "${YELLOW}Please start Redis manually: sudo systemctl start redis${NC}"
        exit 1
    fi
fi
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE_DIR="$SCRIPT_DIR/engine"

# Try to find Python environment - prefer shared env, fallback to backend venv
if [ -f "/home/hts-005/Documents/python/v3.12/env/bin/python" ]; then
    VENV_PYTHON="/home/hts-005/Documents/python/v3.12/env/bin/python"
elif [ -f "$SCRIPT_DIR/backend/.venv/bin/python3" ]; then
    VENV_PYTHON="$SCRIPT_DIR/backend/.venv/bin/python3"
else
    VENV_PYTHON="python3"
fi

# Check Python environment
echo -e "${YELLOW}[2/5] Checking Python environment...${NC}"
if "$VENV_PYTHON" -c "import sys; print(sys.executable)" > /dev/null 2>&1; then
    PYTHON_PATH=$("$VENV_PYTHON" -c "import sys; print(sys.executable)")
    echo -e "${GREEN}✓ Python environment ready: $PYTHON_PATH${NC}"
else
    echo -e "${RED}✗ Python not found or not working${NC}"
    exit 1
fi
echo ""

# Navigate to engine directory
echo -e "${YELLOW}[3/5] Navigating to engine directory...${NC}"
if [ -d "$ENGINE_DIR" ]; then
    cd "$ENGINE_DIR"
    echo -e "${GREEN}✓ Changed to engine directory${NC}"
else
    echo -e "${RED}✗ Engine directory not found${NC}"
    exit 1
fi
echo ""

# Check Celery installation
echo -e "${YELLOW}[4/5] Checking Celery installation...${NC}"
if "$VENV_PYTHON" -c "import celery" 2> /dev/null; then
    CELERY_VERSION=$("$VENV_PYTHON" -c "import celery; print(celery.__version__)")
    echo -e "${GREEN}✓ Celery $CELERY_VERSION installed${NC}"
else
    echo -e "${RED}✗ Celery not installed${NC}"
    echo -e "${YELLOW}Installing Celery...${NC}"
    "$VENV_PYTHON" -m pip install celery==5.3.4 redis==5.0.1
fi
echo ""

# Start Celery
echo -e "${YELLOW}[5/5] Starting Celery...${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Ask user what to start
echo -e "${YELLOW}What would you like to start?${NC}"
echo "1) Celery Worker only"
echo "2) Celery Beat only"
echo "3) Both Worker and Beat (in background)"
echo "4) Worker with Flower monitoring"
read -p "Enter choice [1-4]: " choice

case $choice in
    1)
        echo -e "${GREEN}Starting Celery Worker (default queue)...${NC}"
        "$VENV_PYTHON" -m celery -A llm_monitor_engine worker -Q celery --loglevel=info
        ;;
    2)
        echo -e "${GREEN}Starting Celery Beat...${NC}"
        "$VENV_PYTHON" -m celery -A llm_monitor_engine beat --loglevel=info
        ;;
    3)
        # SEO ranking tasks are routed to the 'seo' queue (see CELERY_TASK_ROUTES
        # in engine settings). They run on a dedicated worker so user-triggered
        # SEO refreshes aren't blocked by the prompt/competitor analytics backlog
        # on the default queue.
        echo -e "${GREEN}Starting default-queue Celery Worker in background...${NC}"
        nohup "$VENV_PYTHON" -m celery -A llm_monitor_engine worker -Q celery --loglevel=info > /tmp/celery-worker.log 2>&1 &
        WORKER_PID=$!
        sleep 2
        echo -e "${GREEN}Starting SEO-queue Celery Worker in background...${NC}"
        nohup "$VENV_PYTHON" -m celery -A llm_monitor_engine worker -Q seo --concurrency=2 -n seo@%h --loglevel=info > /tmp/celery-seo-worker.log 2>&1 &
        SEO_WORKER_PID=$!
        sleep 2
        echo -e "${GREEN}Starting Celery Beat in background...${NC}"
        nohup "$VENV_PYTHON" -m celery -A llm_monitor_engine beat --loglevel=info > /tmp/celery-beat.log 2>&1 &
        BEAT_PID=$!
        sleep 2
        echo -e "${GREEN}✓ Default Worker started (PID: $WORKER_PID)${NC}"
        echo -e "${GREEN}✓ SEO Worker started (PID: $SEO_WORKER_PID)${NC}"
        echo -e "${GREEN}✓ Celery Beat started (PID: $BEAT_PID)${NC}"
        echo -e "${YELLOW}Default worker log: /tmp/celery-worker.log${NC}"
        echo -e "${YELLOW}SEO worker log: /tmp/celery-seo-worker.log${NC}"
        echo -e "${YELLOW}Beat log: /tmp/celery-beat.log${NC}"
        echo ""
        echo -e "${YELLOW}To stop: pkill -f 'celery.*worker' && pkill -f 'celery.*beat'${NC}"
        ;;
    4)
        # Check if Flower is installed
        if "$VENV_PYTHON" -c "import flower" 2> /dev/null; then
            echo -e "${GREEN}Starting Celery Worker...${NC}"
            nohup "$VENV_PYTHON" -m celery -A llm_monitor_engine worker --loglevel=info > /tmp/celery-worker.log 2>&1 &
            sleep 2
            echo -e "${GREEN}Starting Flower monitoring...${NC}"
            "$VENV_PYTHON" -m celery -A llm_monitor_engine flower --port=5555
        else
            echo -e "${YELLOW}Flower not installed. Installing...${NC}"
            "$VENV_PYTHON" -m pip install flower
            echo -e "${GREEN}Starting Celery Worker...${NC}"
            nohup "$VENV_PYTHON" -m celery -A llm_monitor_engine worker --loglevel=info > /tmp/celery-worker.log 2>&1 &
            sleep 2
            echo -e "${GREEN}Starting Flower monitoring...${NC}"
            "$VENV_PYTHON" -m celery -A llm_monitor_engine flower --port=5555
        fi
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Celery started successfully!${NC}"
echo -e "${GREEN}========================================${NC}"

