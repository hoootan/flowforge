#!/bin/bash
# Run the FlowForge Demo Application

cd "$(dirname "$0")"

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e "../flowforge/packages/flowforge-sdk[ai,fastapi]"
else
    source .venv/bin/activate
fi

echo "Starting FlowForge Demo..."
python src/app.py
