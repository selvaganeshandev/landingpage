#!/bin/bash

# Report Email Test - Comprehensive Test Script
# Sends all 4 report types to sarvanan@appkodes.com

echo "=============================================="
echo "  Report Email System - Comprehensive Test"
echo "=============================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Python path
PYTHON_PATH="/home/hts-005/Documents/python/v3.12/env/bin/python"

# Change to backend directory
cd /home/hts-005/Documents/python/v3.12/llm-monitor/backend

echo -e "${YELLOW}Using Python: $PYTHON_PATH${NC}"

# Step 1: Seed report templates
echo ""
echo -e "${YELLOW}Step 1: Seeding report templates...${NC}"
echo "----------------------------------------------"
$PYTHON_PATH seed_report_templates.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Templates seeded successfully${NC}"
else
    echo -e "${RED}✗ Failed to seed templates${NC}"
    exit 1
fi

# Step 2: Run the email test
echo ""
echo -e "${YELLOW}Step 2: Generating and sending test emails...${NC}"
echo "----------------------------------------------"
cd ../engine
$PYTHON_PATH test_report_emails.py

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Test completed successfully!${NC}"
    echo ""
    echo "=============================================="
    echo "  📧 CHECK YOUR EMAIL"
    echo "=============================================="
    echo "Recipient: sarvanan@appkodes.com"
    echo ""
    echo "You should receive 4 emails:"
    echo "  1. Executive Dashboard Report"
    echo "  2. Detailed Analytics Report"
    echo "  3. Competitor Focus Report"
    echo "  4. Content Strategy Report"
    echo ""
    echo "Each email will have the report attached as PDF"
    echo "=============================================="
else
    echo ""
    echo -e "${RED}✗ Test failed${NC}"
    echo "Check the error messages above"
    exit 1
fi
