#!/bin/bash
# Run the ELO Scenario Lab API server
# Usage: ./run.sh

# Get the directory where this script is located
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Add project root to PYTHONPATH so 'src' is importable
export PYTHONPATH="${DIR}:${PYTHONPATH}"

# Start uvicorn
cd "${DIR}"
python3 -m uvicorn src.api.main:app --reload --port 8000
