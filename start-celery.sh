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

# Activate virtual environment
echo -e "${YELLOW}[2/5] Activating virtual environment...${NC}"
VENV_PATH="/home/hts-005/Documents/python/v3.12/env"
if [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
else
    echo -e "${RED}✗ Virtual environment not found at $VENV_PATH${NC}"
    exit 1
fi
echo ""

# Navigate to engine directory
echo -e "${YELLOW}[3/5] Navigating to engine directory...${NC}"
ENGINE_DIR="/home/hts-005/Documents/python/v3.12/llm-monitor/engine"
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
if python -c "import celery" 2> /dev/null; then
    CELERY_VERSION=$(python -c "import celery; print(celery.__version__)")
    echo -e "${GREEN}✓ Celery $CELERY_VERSION installed${NC}"
else
    echo -e "${RED}✗ Celery not installed${NC}"
    echo -e "${YELLOW}Installing Celery...${NC}"
    pip install celery==5.3.4 redis==5.0.1
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
        echo -e "${GREEN}Starting Celery Worker...${NC}"
        celery -A llm_monitor_engine worker --loglevel=info
        ;;
    2)
        echo -e "${GREEN}Starting Celery Beat...${NC}"
        celery -A llm_monitor_engine beat --loglevel=info
        ;;
    3)
        echo -e "${GREEN}Starting Celery Worker in background...${NC}"
        celery -A llm_monitor_engine worker --loglevel=info --logfile=/tmp/celery-worker.log --detach
        sleep 2
        echo -e "${GREEN}Starting Celery Beat in background...${NC}"
        celery -A llm_monitor_engine beat --loglevel=info --logfile=/tmp/celery-beat.log --detach
        sleep 2
        echo -e "${GREEN}✓ Celery Worker and Beat started in background${NC}"
        echo -e "${YELLOW}Worker log: /tmp/celery-worker.log${NC}"
        echo -e "${YELLOW}Beat log: /tmp/celery-beat.log${NC}"
        echo ""
        echo -e "${YELLOW}To stop: pkill -f 'celery worker' && pkill -f 'celery beat'${NC}"
        ;;
    4)
        # Check if Flower is installed
        if python -c "import flower" 2> /dev/null; then
            echo -e "${GREEN}Starting Celery Worker...${NC}"
            celery -A llm_monitor_engine worker --loglevel=info --detach --logfile=/tmp/celery-worker.log
            sleep 2
            echo -e "${GREEN}Starting Flower monitoring...${NC}"
            celery -A llm_monitor_engine flower --port=5555
        else
            echo -e "${YELLOW}Flower not installed. Installing...${NC}"
            pip install flower
            echo -e "${GREEN}Starting Celery Worker...${NC}"
            celery -A llm_monitor_engine worker --loglevel=info --detach --logfile=/tmp/celery-worker.log
            sleep 2
            echo -e "${GREEN}Starting Flower monitoring...${NC}"
            celery -A llm_monitor_engine flower --port=5555
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

