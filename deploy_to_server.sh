#!/bin/bash
# Manual deployment wrapper - calls the core deploy.sh script
# This ensures consistency with CI/CD deployments

set -e

echo "============================================================"
echo "OC7 RAG API - Manual Deployment"
echo "============================================================"
echo ""

# Get server info
if [ -z "$1" ]; then
    echo "Usage: ./deploy_to_server.sh SERVER_IP [USER]"
    echo "Example: ./deploy_to_server.sh 192.168.1.100 myuser"
    echo ""
    read -p "Enter server IP or hostname: " SERVER_IP
else
    SERVER_IP=$1
fi

# Get username
if [ -z "$2" ]; then
    read -p "Enter SSH user (default: $(whoami)): " SSH_USER
    SSH_USER=${SSH_USER:-$(whoami)}
else
    SSH_USER=$2
fi

# Get Mistral API key
if [ -z "$MISTRAL_API_KEY" ]; then
    echo ""
    echo "Mistral API key not found in environment."
    read -p "Enter MISTRAL_API_KEY (or press Enter to skip): " MISTRAL_API_KEY
fi

# Export environment variables for deploy.sh
export DEPLOY_HOST="$SERVER_IP"
export DEPLOY_USER="$SSH_USER"
export MISTRAL_API_KEY="$MISTRAL_API_KEY"
export DEPLOY_DIR="~/oc7-rag"

echo ""
echo "Configuration:"
echo "  Host: $DEPLOY_HOST"
echo "  User: $DEPLOY_USER"
echo "  Directory: $DEPLOY_DIR"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled"
    exit 0
fi

# Call the core deployment script
./scripts/deploy.sh

