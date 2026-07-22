#!/usr/bin/env bash
set -euo pipefail

# Restore DVC inputs when a remote is configured and reproduce stale stages.
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"
export PATH="$PROJECT_ROOT/.venv/bin:$PATH"
.venv/bin/python -m dvc pull || {
  echo "DVC pull skipped: configure a project remote or keep local source data." >&2
}
.venv/bin/python -m dvc repro
