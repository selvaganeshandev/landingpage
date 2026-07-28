#!/bin/bash
# Start Django backend with SSL/TLS support

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   LLM Monitor Backend - SSL Server${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Try to find Python environment
if [ -f "/home/hts-005/Documents/python/v3.12/env/bin/python" ]; then
    VENV_PYTHON="/home/hts-005/Documents/python/v3.12/env/bin/python"
elif [ -f "$SCRIPT_DIR/.venv/bin/python3" ]; then
    VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python3"
else
    VENV_PYTHON="python3"
fi

# Check if SSL certificates exist
CERT_DIR="$SCRIPT_DIR/ssl"
CERT_FILE="$CERT_DIR/server.crt"
KEY_FILE="$CERT_DIR/server.key"

if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
    echo -e "${YELLOW}SSL certificates not found.${NC}"
    read -p "Do you want to generate them now? (Y/n): " generate
    if [[ ! $generate =~ ^[Nn]$ ]]; then
        bash "$SCRIPT_DIR/generate_ssl_cert.sh"
    else
        echo -e "${RED}SSL certificates are required. Exiting.${NC}"
        exit 1
    fi
fi

# Load environment variables
if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(cat "$SCRIPT_DIR/.env" | grep -v '^#' | xargs)
fi

# Set SSL paths in environment
export SSL_CERTIFICATE_PATH="$CERT_FILE"
export SSL_PRIVATE_KEY_PATH="$KEY_FILE"
export USE_TLS=True

# Get port from environment or use default
PORT=${PORT:-8000}

echo -e "${YELLOW}Starting Django server with SSL on port $PORT...${NC}"
echo ""
echo -e "${GREEN}Certificate: $CERT_FILE${NC}"
echo -e "${GREEN}Private Key: $KEY_FILE${NC}"
echo ""
echo -e "${YELLOW}Access the server at: https://localhost:$PORT${NC}"
echo -e "${YELLOW}Note: You may see a browser security warning for self-signed certificates.${NC}"
echo ""

# Check if gunicorn is installed
if "$VENV_PYTHON" -c "import gunicorn" 2> /dev/null; then
    echo -e "${GREEN}Using Gunicorn with SSL...${NC}"
    "$VENV_PYTHON" -m gunicorn \
        --bind 0.0.0.0:$PORT \
        --workers 4 \
        --threads 2 \
        --timeout 300 \
        --keyfile "$KEY_FILE" \
        --certfile "$CERT_FILE" \
        --access-logfile - \
        --error-logfile - \
        llm_monitor.wsgi:application
else
    echo -e "${YELLOW}Gunicorn not found. Using Django runserver with SSL wrapper...${NC}"
    echo -e "${YELLOW}Installing django-extensions for SSL support...${NC}"
    "$VENV_PYTHON" -m pip install django-extensions pyOpenSSL > /dev/null 2>&1
    
    # Use runserver_plus for SSL support
    "$VENV_PYTHON" manage.py runserver_plus \
        --cert-file "$CERT_FILE" \
        --key-file "$KEY_FILE" \
        0.0.0.0:$PORT
fi

