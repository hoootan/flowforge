#!/bin/bash
# FlowForge Development - Single command startup

set -e

echo "FlowForge Development"
echo "====================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

echo "Starting all services..."
echo ""
echo "Access points (once ready):"
echo "  API Server:  http://localhost:8000"
echo "  API Docs:    http://localhost:8000/docs"
echo "  Dashboard:   http://localhost:3000"
echo ""

docker compose up --build
