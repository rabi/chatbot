#!/usr/bin/env bash

set -euo pipefail

# Install tox in the current Python environment if not already installed
if ! command -v tox &> /dev/null; then
    echo "tox not found. Installing tox..."
    python3 -m pip install --upgrade pip
    python3 -m pip install tox
else
    echo "tox is already installed: $(tox --version)"
fi
