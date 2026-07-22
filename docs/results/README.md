# Curated result snapshots

These small files are Git-tracked snapshots used by the repository landing
page and code review. Their authoritative generated counterparts live under
`outputs/` and are versioned as DVC pipeline outputs.

| Snapshot | Authoritative generated file |
|---|---|
| `final_audit.md` | `outputs/0_logs/final_audit.md` |
| `sample_definition.md` | `outputs/2_sample_definition/sample_definition.md` |
| `regression_main.csv` | `outputs/9_main_results/regression_main.csv` |
| `empirical_pvalues.csv` | `outputs/10_null_models/empirical_pvalues.csv` |
| `robustness_summary.csv` | `outputs/11_robustness/robustness_summary.csv` |
| `results_key_numbers.md` | `outputs/14_report_inputs/results_key_numbers.md` |

Refresh snapshots only after a successful full publication run and review the
diff before committing. They are documentation, not inputs to the pipeline.
