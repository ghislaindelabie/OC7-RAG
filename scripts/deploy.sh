#!/bin/bash
# Core deployment script - used by both manual deployment and CI/CD
# This ensures consistency between manual and automated deployments
#
# Usage: ./scripts/deploy.sh
# Environment variables required:
#   DEPLOY_HOST - Server hostname or IP
#   DEPLOY_USER - SSH user (default: current user)
#   MISTRAL_API_KEY - Mistral API key
#   DEPLOY_DIR - Target directory on server (default: ~/oc7-rag)

set -e  # Exit on error

# Configuration
DEPLOY_HOST=${DEPLOY_HOST:-""}
DEPLOY_USER=${DEPLOY_USER:-$(whoami)}
DEPLOY_DIR=${DEPLOY_DIR:-"~/oc7-rag"}
MISTRAL_API_KEY=${MISTRAL_API_KEY:-""}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%H:%M:%S')]${NC} $1"
}

# Validate environment
if [ -z "$DEPLOY_HOST" ]; then
    error "DEPLOY_HOST environment variable not set"
    exit 1
fi

log "Deploying to: $DEPLOY_USER@$DEPLOY_HOST:$DEPLOY_DIR"

# Step 1: Test SSH connection
log "Testing SSH connection..."
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$DEPLOY_USER@$DEPLOY_HOST" exit 2>/dev/null; then
    error "Cannot connect to $DEPLOY_USER@$DEPLOY_HOST"
    error "Make sure SSH key authentication is set up"
    exit 1
fi
log "✓ SSH connection successful"

# Step 2: Deploy files via rsync
log "Syncing files to server..."
rsync -avz --delete \
    --exclude='.git/' \
    --exclude='__pycache__/' \
    --exclude='.pytest_cache/' \
    --exclude='*.pyc' \
    --exclude='venv/' \
    --exclude='.venv/' \
    --exclude='data/raw/*' \
    --exclude='data/index/*' \
    --exclude='.env' \
    --exclude='.env.local' \
    --exclude='*.log' \
    --exclude='api.pid' \
    ./ "$DEPLOY_USER@$DEPLOY_HOST:$DEPLOY_DIR/"

log "✓ Files synced"

# Step 3: Setup environment and deploy on server
log "Setting up environment on server..."
ssh "$DEPLOY_USER@$DEPLOY_HOST" bash << ENDSSH
set -e

cd $DEPLOY_DIR

# Check Python version
PYTHON_VERSION=\$(python3 --version 2>&1 | awk '{print \$2}')
echo "Python version: \$PYTHON_VERSION"

# Verify Python >= 3.11
PYTHON_MAJOR=\$(echo \$PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=\$(echo \$PYTHON_VERSION | cut -d. -f2)
if [ "\$PYTHON_MAJOR" -lt 3 ] || ([ "\$PYTHON_MAJOR" -eq 3 ] && [ "\$PYTHON_MINOR" -lt 11 ]); then
    echo "Error: Python 3.11+ required, found \$PYTHON_VERSION"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate and upgrade pip
source venv/bin/activate
pip install --upgrade pip --quiet

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt --quiet

echo "✓ Dependencies installed"

# Stop old API if running
if [ -f api.pid ]; then
    OLD_PID=\$(cat api.pid)
    if kill -0 \$OLD_PID 2>/dev/null; then
        echo "Stopping old API (PID: \$OLD_PID)..."
        kill \$OLD_PID
        sleep 2
        # Force kill if still running
        kill -0 \$OLD_PID 2>/dev/null && kill -9 \$OLD_PID || true
    fi
    rm -f api.pid
fi

# Create .env file if MISTRAL_API_KEY is provided
if [ -n "$MISTRAL_API_KEY" ]; then
    cat > .env << ENVEOF
MISTRAL_API_KEY=$MISTRAL_API_KEY
ENVEOF
    echo "✓ Environment variables configured"
else
    echo "Warning: No MISTRAL_API_KEY provided"
fi

# Start API
echo "Starting API..."
nohup python scripts/run_api.py > api.log 2>&1 &
NEW_PID=\$!
echo \$NEW_PID > api.pid

# Wait for startup
sleep 3

# Verify API is running
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✓ API started successfully (PID: \$NEW_PID)"
    curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || true
else
    echo "✗ API failed to start"
    tail -20 api.log
    exit 1
fi
ENDSSH

log "✓ Deployment complete"

# Step 4: Verify from outside
log "Verifying external access..."
sleep 2
if curl -sf "http://$DEPLOY_HOST:8000/health" > /dev/null 2>&1; then
    log "✓ API accessible from outside"
else
    warn "⚠ Cannot access API from outside (firewall?)"
    warn "  Try: curl http://$DEPLOY_HOST:8000/health"
fi

# Summary
echo ""
log "============================================================"
log "✓ Deployment successful!"
log "============================================================"
echo ""
echo "API URL:      http://$DEPLOY_HOST:8000"
echo "Health:       http://$DEPLOY_HOST:8000/health"
echo "Swagger docs: http://$DEPLOY_HOST:8000/docs"
echo ""
echo "View logs:    ssh $DEPLOY_USER@$DEPLOY_HOST 'tail -f $DEPLOY_DIR/api.log'"
echo "Stop API:     ssh $DEPLOY_USER@$DEPLOY_HOST 'kill \$(cat $DEPLOY_DIR/api.pid)'"
echo ""

