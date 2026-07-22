# Architecture

## Design goals

The repository separates immutable source data, reproducible transformation
code, cached analytical artifacts, publication outputs, and operational
metadata. Scientific decisions remain in `src/00_config.py`; operational entry
points call the same numbered scripts rather than reimplementing analysis.

```text
SNAP archives (DVC)
        |
        v
01--05 ingestion, validation, graphs, features, samples
        |
        v
06--11 network measures and node-level analytical dataset
        |
        v
12--14 statistical inference, null models, robustness
        |
        v
15--17 figures, tables, and report-ready facts
        |
        v
automated audit + manifest + data contracts
```

## Directory responsibilities

| Path | Responsibility | Versioning policy |
|---|---|---|
| `data_raw/` | Immutable Facebook source archives | DVC |
| `data_processed/` | Reconstructable graph and analytical artifacts | DVC pipeline output |
| `src/` | Numbered scientific stages and shared functions | Git |
| `tests/` | Unit, contract, CLI, and artifact tests | Git |
| `outputs/` | Logs, evidence, figures, tables, report inputs | DVC pipeline output |
| `docs/` | Architecture, DataOps, governance, and assets | Git |
| `notes/` | Original analytical specifications and detailed output guide | Git |
| `.github/workflows/` | Continuous integration | Git |

## Reproducibility boundaries

- The combined Facebook graph is inventory context; social comparisons use
  separate ego-networks because anonymized feature columns are ego-specific.
- Randomized algorithms use seed 7745. Each permutation also stores its seed.
- DVC binds source checksums, code dependencies, and generated artifacts.
- The full pipeline is the publication path. Fast mode exists only for local
  development and uses 200 rather than 1,000 permutations.
