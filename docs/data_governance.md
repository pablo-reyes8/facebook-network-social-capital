# Data governance

## Source and stewardship

The analysis uses the SNAP `ego-Facebook` dataset described by McAuley and
Leskovec (2012). The repository maintainer is responsible for retaining source
attribution, respecting the dataset's distribution terms, and ensuring that
GitHub releases do not introduce unrelated Facebook or Twitter data.

## Classification

- Node identifiers and profile features are anonymized.
- The project contains no names, email addresses, access tokens, or direct
  personal identifiers.
- Anonymization does not eliminate all re-identification risk. Node-level data
  should be used only for research and educational purposes.
- The `twitter/` directory is explicitly outside the analytical scope and is
  excluded from repository tracking.

## Lineage

`data_raw/` contains immutable archives. `data_processed/` and `outputs/` are
derived exclusively through `dvc.yaml` and the numbered Python stages. The
lineage is:

```text
source archive -> extracted ego files -> validated graphs/features
-> node and edge measures -> inference -> publication artifacts
```

## Retention and change control

- Never overwrite a raw source file under an existing DVC hash.
- Add new snapshots as new DVC versions and describe their provenance.
- Keep raw data out of normal Git history.
- Do not manually edit analytical Parquet or CSV outputs.
- Review changes to sample counts, missingness, and metric ranges before merge.

## Access and secrets

A future cloud DVC remote should use repository or organization secrets. Never
commit credentials to `.dvc/config`; use `.dvc/config.local` or CI secrets.

## Known limitations

The data are cross-sectional, ego-centered, anonymized, and not representative
of all Facebook users. Some node IDs occur in multiple ego-networks. Friendship
ties do not measure relationship strength, and detected communities are
structural partitions rather than verified social groups.
