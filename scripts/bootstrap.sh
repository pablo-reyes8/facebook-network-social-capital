#!/usr/bin/env bash
set -euo pipefail

# Create an isolated development environment and install runtime, test, and DVC tooling.
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"

echo "Environment ready. Run: .venv/bin/facebook-graph-analysis validate"
