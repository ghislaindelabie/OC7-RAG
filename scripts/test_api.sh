#!/bin/bash
# Quick API test script for OC7-RAG
# Tests health, system info, and ask endpoints
#
# Usage:
#   ./scripts/test_api.sh                    # Test localhost:8000
#   ./scripts/test_api.sh http://server:8000 # Test specific URL

set -e

API_URL="${1:-http://localhost:8000}"

echo "🧪 Testing OC7-RAG API at $API_URL"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test 1: Health check
echo "1️⃣  Health check..."
if curl -sf "$API_URL/health" > /dev/null; then
    echo -e "${GREEN}✓ Health endpoint responding${NC}"
    curl -s "$API_URL/health" | python3 -m json.tool 2>/dev/null || echo "Response OK"
else
    echo -e "${RED}✗ Health endpoint failed${NC}"
    exit 1
fi
echo ""

# Test 2: System info
echo "2️⃣  System info..."
if curl -sf "$API_URL/api/v1/rag/info" > /dev/null; then
    echo -e "${GREEN}✓ Info endpoint responding${NC}"
    curl -s "$API_URL/api/v1/rag/info" | python3 -m json.tool 2>/dev/null | head -15
else
    echo -e "${RED}✗ Info endpoint failed${NC}"
    exit 1
fi
echo ""

# Test 3: Ask a question
echo "3️⃣  Ask a question..."
RESPONSE=$(curl -s -X POST "$API_URL/api/v1/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Quels concerts à Annecy?", "rag_method": "basic"}')

if [ $? -eq 0 ] && echo "$RESPONSE" | grep -q "answer"; then
    echo -e "${GREEN}✓ Ask endpoint responding${NC}"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null | head -20
else
    echo -e "${RED}✗ Ask endpoint failed${NC}"
    echo "Response: $RESPONSE"
    exit 1
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ All tests passed!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "API is ready to use at $API_URL"
echo "  - Web interface: $API_URL/"
echo "  - API docs: $API_URL/docs"
