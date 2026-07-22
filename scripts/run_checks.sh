#!/usr/bin/env bash
set -euo pipefail

# Run the same static checks and tests used in continuous integration.
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"
.venv/bin/python -m ruff check project_cli.py src tests
.venv/bin/python -m pytest -m "not integration" --cov --cov-report=term-missing
.venv/bin/python project_cli.py validate
