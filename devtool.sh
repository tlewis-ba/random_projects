#!/bin/bash
# Wrapper for devtool CLI: ensures venv and runs devtool
set -e

VENV=".venv"
PYTHON="$VENV/bin/python"
SCRIPT="devtool/cli.py"

# Create venv if missing
if [ ! -d "$VENV" ]; then
    echo "[devtool.sh] Creating venv..."
    python3 -m venv "$VENV"
    source "$VENV/bin/activate"
    pip install --upgrade pip
    # Add requirements.txt if it exists
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    fi
else
    source "$VENV/bin/activate"
fi

# Run the script
$PYTHON "$SCRIPT" "$@"
