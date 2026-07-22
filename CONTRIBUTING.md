# Contributing

## Development workflow

1. Create a focused branch from `main`.
2. Run `bash scripts/bootstrap.sh` once.
3. Make the smallest coherent code, test, contract, and documentation change.
4. Run `make lint`, `make test`, and `make validate`.
5. For analytical changes, run `make pipeline-fast` during development and the
   full `make pipeline` before requesting review.
6. Update `dvc.lock` whenever source data, dependencies, or generated outputs
   change.

## Pull-request requirements

- Explain whether the change affects data, sample membership, measures,
  inference, figures, or only operations/documentation.
- Include tests for new logic and retain unexpected statistical results.
- Do not manually edit generated CSV, Parquet, PDF, PNG, or LaTeX files.
- Do not weaken contracts simply to pass CI.
- Never commit DVC credentials, access tokens, or direct identifiers.
- Analytical claims must remain associational unless the research design
  changes materially and supports causal identification.

## Style

Use clear function names and docstrings for public or analytical functions.
Ruff is the source of truth for static checks. Keep figures free of internal
titles so captions remain controlled by the research document.
