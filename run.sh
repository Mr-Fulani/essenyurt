#!/bin/bash
# Script to run/restart the Specification Comparison Tool

# Get project root (where the script is located)
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_BIN="$PROJECT_ROOT/venv/bin/python3"

# 1. Kill any existing instances of main.py to allow restart
echo "Closing previous windows..."
pkill -9 -f "main.py" 2>/dev/null
pkill -9 -f "Python" 2>/dev/null
sleep 1

# 2. Check if venv exists
if [ ! -f "$PYTHON_BIN" ]; then
    echo "Error: Virtual environment not found at $PROJECT_ROOT/venv"
    echo "Please make sure the venv is created in the project root."
    exit 1
fi

# 3. Change directory to src and run the app
cd "$PROJECT_ROOT/spec_compare/src"
echo "Starting Specification Comparison Tool..."
"$PYTHON_BIN" main.py &
echo "Done."
