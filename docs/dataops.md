# DataOps lifecycle

This project applies a lightweight DataOps lifecycle appropriate for an
academic, batch-oriented analysis. There is no production service deployment;
"deployment" means producing a versioned, reviewable research release.

## 1. Planning

**Research contract.** The primary question, hypotheses, measures, exclusion
rules, and non-causal interpretation boundary are defined before model fitting
in `notes/checkpoint_proyecto_grafos_facebook.md` and
`notes/instrucciones_pipeline_proyecto_grafos_facebook.md`.

**Data contract.** `config/data_contracts.json` defines required source files,
the analytical primary key, mandatory variables, valid ranges, and privacy
classification.

**Acceptance criteria.** A release requires all 17 stages to succeed, all
mandatory outputs to exist, a unique node--ego key, valid metric ranges, 1,000
publication permutations, and a passing final audit.

## 2. Development

- Work occurs in an isolated Python environment.
- Numbered scripts keep analytical stages independently debuggable.
- `project_cli.py` and the Makefile provide stable operational commands.
- Source archives are immutable and tracked with DVC.
- Derived data are never edited manually; they are recreated by the pipeline.
- Random seeds and package versions are recorded with every full run.
- Feature comparisons remain within ego-network to respect the data model.

Recommended development loop:

```bash
make setup
make validate
make test
make pipeline-fast
```

## 3. Automated testing

The test pyramid contains:

1. **Unit tests:** graph parsing, entropy, partial regression, hashing, and CLI
   behavior using synthetic inputs.
2. **Data-contract tests:** archive structure, compression, schema, ranges,
   uniqueness, and sample consistency.
3. **Artifact integration tests:** validate the current analytical dataset and
   publication audit when DVC outputs are available.
4. **Static analysis:** Ruff catches imports, undefined variables, and common
   Python errors.
5. **Continuous integration:** GitHub Actions runs linting and CI-safe tests on
   supported Python versions without requiring the DVC dataset.

## 4. Deployment as a research release

There is no online inference service. A release consists of:

- a Git tag and GitHub release;
- the report PDF and selected README figures;
- Git-tracked code, tests, configuration, and documentation;
- DVC pointers plus a configured remote for source and derived artifacts;
- a passing audit, data manifest, and recorded dependency versions.

Before tagging a release:

```bash
make lint
make test-all
make pipeline
make status
dvc push
```

## 5. Monitoring and governance

Monitoring is intentionally lightweight because this is a static research
dataset rather than a continuously refreshed product.

- `project_cli.py validate` detects missing or corrupted archives and schema or
  range violations.
- DVC checksums detect unreviewed data changes.
- `outputs/0_logs/final_audit.*` captures publication-time quality status.
- `outputs/0_logs/runtime_summary.csv` allows runtime regression monitoring.
- GitHub branch protection should require the CI workflow before merging.
- Any future dataset refresh must receive a new DVC version and rerun the full
  pipeline; results must not silently overwrite a published release.

## Incident and change policy

If a contract fails, do not weaken the contract to make CI green. Determine
whether the cause is corrupted input, an intentional schema change, or a code
regression. Intentional changes require updating the contract, documentation,
tests, DVC lock file, and research interpretation in the same pull request.
