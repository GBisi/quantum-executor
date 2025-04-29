#!/usr/bin/env bash

# Build documentation
# Usage: ./scripts/build-docs.sh

set -euo pipefail

echo "Building HTML documentation..."
sphinx-build -b html -W docs docs/_build/html

echo "Done. Output available at: docs/_build/html/index.html"
