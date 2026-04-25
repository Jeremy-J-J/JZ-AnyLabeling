#!/bin/bash
# X-AnyLabeling Web Service Startup Script

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$SCRIPT_DIR/venv_web"

cd "$PROJECT_DIR"

# Check for virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Install dependencies
echo "Installing dependencies..."
"$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"

echo "=============================================="
echo "  JZ-AnyLabeling Web Service"
echo "=============================================="
echo ""
echo "Starting server at http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""

# Use venv Python directly to avoid PATH issues
"$VENV_DIR/bin/python" -m uvicorn web_service.main:app --host 0.0.0.0 --port 8000 --reload
