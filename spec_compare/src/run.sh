#!/bin/bash
# Local wrapper for the main run script

# Get project root (2 levels up from src)
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../.." && pwd )"

# Call the main run script
bash "$PROJECT_ROOT/run.sh"
