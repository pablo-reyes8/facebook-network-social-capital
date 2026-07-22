#!/usr/bin/env bash
set -euo pipefail

# Reproduce all analytical artifacts using the project CLI.
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"
.venv/bin/python project_cli.py run "$@"
