.PHONY: help setup validate test test-all lint pipeline pipeline-fast dvc status manifest

PYTHON := .venv/bin/python
CLI := $(PYTHON) project_cli.py

help:
	@echo "setup          Create the environment and install development dependencies"
	@echo "validate       Validate raw data and available artifacts"
	@echo "test           Run CI-safe unit tests"
	@echo "test-all       Run unit and artifact integration tests"
	@echo "lint           Run Ruff static analysis"
	@echo "pipeline       Run the publication pipeline with 1,000 permutations"
	@echo "pipeline-fast  Run the pipeline with 200 permutations"
	@echo "dvc            Reproduce stale DVC stages"
	@echo "status         Show pipeline and DVC status"

setup:
	bash scripts/bootstrap.sh

validate:
	$(CLI) validate

test:
	$(CLI) test --coverage

test-all:
	$(CLI) test --integration --coverage

lint:
	$(PYTHON) -m ruff check project_cli.py src tests

pipeline:
	$(CLI) run

pipeline-fast:
	$(CLI) run --fast

dvc:
	$(CLI) dvc

status:
	$(CLI) status

manifest:
	$(CLI) manifest
