# Numbered pipeline stages

The scientific workflow is split into small, restartable stages. Each stage
prints progress, fails on critical errors, and writes deterministic artifacts.

| Stage | Script | Responsibility |
|---:|---|---|
| 00 | `00_config.py` | Paths, seeds, thresholds, and scientific defaults |
| 01 | `01_extract_and_inventory.py` | Safe extraction and source inventory |
| 02 | `02_validate_raw_data.py` | Edge, feature, ego-feature, and circle validation |
| 03 | `03_build_ego_graphs.py` | Full and LCC graph construction |
| 04 | `04_parse_features.py` | Feature dictionary and node vectors |
| 05 | `05_construct_sample.py` | Eligibility flags and samples A--E |
| 06 | `06_descriptive_networks.py` | Structural network statistics |
| 07 | `07_detect_communities.py` | Louvain stability and circle comparison |
| 08 | `08_compute_social_similarity.py` | Edge similarity and node diversity |
| 09 | `09_compute_cohesion.py` | Clustering, embeddedness, and structural holes |
| 10 | `10_compute_brokerage.py` | Betweenness, participation, and connector roles |
| 11 | `11_build_node_level_dataset.py` | Analytical dataset and dictionary |
| 12 | `12_statistical_analysis.py` | Correlations, regressions, and diagnostics |
| 13 | `13_permutation_tests.py` | Attribute permutations and configuration nulls |
| 14 | `14_robustness_checks.py` | Alternative measures, samples, and bootstrap |
| 15 | `15_make_figures.py` | Publication PNG and vector PDF figures |
| 16 | `16_make_tables.py` | CSV, Markdown, and LaTeX tables |
| 17 | `17_generate_sample_text.py` | Verified report facts and interpretation flags |

`pipeline_lib.py` contains shared implementation. `quality_checks.py` contains
reusable contracts for the CLI and CI. `run_all.py` orchestrates the numbered
stages and performs the publication audit.

Run a stage with:

```bash
.venv/bin/python project_cli.py stage 08
```

Run the dependency-aware pipeline with `dvc repro`, or the complete publication
path with `.venv/bin/python project_cli.py run`.
