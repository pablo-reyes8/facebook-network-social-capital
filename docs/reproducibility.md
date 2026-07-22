# Reproducibility guide

## Standard setup

```bash
git clone <repository-url>
cd facebook-ego-network-analysis
bash scripts/bootstrap.sh
dvc pull                 # after a project remote is configured
make validate
make pipeline
```

## Fast development mode

`make pipeline-fast` uses 200 permutations and is intended only for debugging.
It must not be used to refresh publication results.

## Exact publication configuration

- random seed: 7745;
- Louvain resolution: 1.0;
- Louvain stability runs: 20 per ego-network;
- permutation tests: 1,000;
- configuration-model replications: 20 per ego-network;
- bootstrap replications: 500;
- robust regression covariance: HC3;
- ego-network fixed effects in adjusted pooled models.

The complete configuration is written to
`outputs/0_logs/config_used.json`. Dependency versions are written to
`outputs/0_logs/package_versions.txt`.

## Reproducing only one stage

```bash
.venv/bin/python project_cli.py stage 08
```

This is useful for development but does not resolve dependencies. Use
`dvc repro` for dependency-aware execution.

## Verification

```bash
make lint
make test-all
.venv/bin/python project_cli.py validate --require-artifacts
```

A successful publication run must finish with
`Critical status: PASS` in `outputs/0_logs/final_audit.md`.
