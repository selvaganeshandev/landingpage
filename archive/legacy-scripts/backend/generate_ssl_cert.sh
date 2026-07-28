#!/bin/bash
# Generate self-signed SSL certificate for development

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   SSL Certificate Generator${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERT_DIR="$SCRIPT_DIR/ssl"
CERT_FILE="$CERT_DIR/server.crt"
KEY_FILE="$CERT_DIR/server.key"

# Create ssl directory if it doesn't exist
mkdir -p "$CERT_DIR"

# Check if certificates already exist
if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
    echo -e "${YELLOW}SSL certificates already exist.${NC}"
    read -p "Do you want to regenerate them? (y/N): " regenerate
    if [[ ! $regenerate =~ ^[Yy]$ ]]; then
        echo "Keeping existing certificates."
        exit 0
    fi
fi

echo -e "${YELLOW}Generating self-signed SSL certificate...${NC}"
echo ""

# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -keyout "$KEY_FILE" -out "$CERT_FILE" \
    -days 365 -nodes \
    -subj "/C=US/ST=State/L=City/O=LLM Monitor/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,DNS:*.localhost,IP:127.0.0.1"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ SSL certificate generated successfully!${NC}"
    echo ""
    echo "Certificate files:"
    echo "  Certificate: $CERT_FILE"
    echo "  Private Key: $KEY_FILE"
    echo ""
    echo -e "${YELLOW}Note: This is a self-signed certificate for development only.${NC}"
    echo -e "${YELLOW}Your browser will show a security warning. This is normal for self-signed certificates.${NC}"
    echo ""
    echo "To use these certificates, set in your .env file:"
    echo "  SSL_CERTIFICATE_PATH=$CERT_FILE"
    echo "  SSL_PRIVATE_KEY_PATH=$KEY_FILE"
    echo "  USE_TLS=True"
else
    echo ""
    echo -e "${RED}✗ Failed to generate SSL certificate${NC}"
    exit 1
fi

