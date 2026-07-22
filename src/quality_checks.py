"""Reusable data contracts for local development and continuous integration."""
from __future__ import annotations

import gzip
import hashlib
import json
import tarfile
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ValidationResult:
    """One machine-readable repository validation result."""

    name: str
    status: str
    detail: str


def sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Return a streaming SHA-256 digest without loading a file into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_raw_data(root: Path) -> list[ValidationResult]:
    """Validate existence, compression, and expected contents of source data."""
    raw = root / "data_raw"
    facebook_tar = raw / "facebook.tar.gz"
    combined = raw / "facebook_combined.txt.gz"
    results: list[ValidationResult] = []
    for path in (facebook_tar, combined):
        results.append(ValidationResult(f"raw_exists:{path.name}", "PASS" if path.is_file() else "FAIL", str(path)))
    if facebook_tar.is_file():
        try:
            with tarfile.open(facebook_tar, "r:gz") as archive:
                names = archive.getnames()
            ego_edges = [name for name in names if name.endswith(".edges")]
            ok = len(ego_edges) == 10 and "facebook/0.feat" in names
            results.append(ValidationResult("archive_contract", "PASS" if ok else "FAIL", f"{len(ego_edges)} ego edge files"))
        except tarfile.TarError as exc:
            results.append(ValidationResult("archive_contract", "FAIL", str(exc)))
    if combined.is_file():
        try:
            with gzip.open(combined, "rt", encoding="utf-8") as handle:
                first = handle.readline().split()
            ok = len(first) == 2 and all(value.isdigit() for value in first)
            results.append(ValidationResult("combined_edge_schema", "PASS" if ok else "FAIL", f"first record={first}"))
        except (OSError, UnicodeError) as exc:
            results.append(ValidationResult("combined_edge_schema", "FAIL", str(exc)))
    return results


def validate_artifacts(root: Path, require_artifacts: bool = False) -> list[ValidationResult]:
    """Validate analytical schema, ranges, uniqueness, and final audit state."""
    path = root / "data_processed" / "analytic" / "node_level_analysis.parquet"
    if not path.exists():
        status = "FAIL" if require_artifacts else "SKIP"
        return [ValidationResult("analysis_artifact", status, "run the pipeline or dvc pull")]
    frame = pd.read_parquet(path)
    required = {
        "ego_id", "node_id", "degree", "similarity_jaccard_mean", "diversity_complement",
        "clustering", "betweenness", "participation_coefficient", "eligible_main_regression",
    }
    results = [ValidationResult("analysis_schema", "PASS" if required <= set(frame) else "FAIL", f"{len(frame.columns)} columns")]
    duplicate_count = int(frame.duplicated(["ego_id", "node_id"]).sum())
    results.append(ValidationResult("analysis_primary_key", "PASS" if duplicate_count == 0 else "FAIL", f"duplicates={duplicate_count}"))
    for column in ["similarity_jaccard_mean", "diversity_complement", "clustering", "betweenness", "participation_coefficient"]:
        values = frame[column].dropna()
        valid = bool(((values >= -1e-12) & (values <= 1 + 1e-12)).all())
        results.append(ValidationResult(f"range:{column}", "PASS" if valid else "FAIL", f"[{values.min():.6g}, {values.max():.6g}]"))
    degree = frame["degree"].dropna().to_numpy()
    valid_degree = bool((degree >= 0).all() and np.allclose(degree % 1, 0))
    results.append(ValidationResult("range:degree", "PASS" if valid_degree else "FAIL", f"[{degree.min():.0f}, {degree.max():.0f}]"))
    audit = root / "outputs" / "0_logs" / "final_audit.md"
    if audit.exists():
        passed = "Critical status: PASS" in audit.read_text(encoding="utf-8")
        results.append(ValidationResult("pipeline_audit", "PASS" if passed else "FAIL", str(audit.relative_to(root))))
    elif require_artifacts:
        results.append(ValidationResult("pipeline_audit", "FAIL", "missing final_audit.md"))
    return results


def validate_repository(root: Path, require_artifacts: bool = False) -> list[ValidationResult]:
    """Run source-data and derived-artifact contracts."""
    return validate_raw_data(root) + validate_artifacts(root, require_artifacts=require_artifacts)


def write_data_manifest(root: Path) -> Path:
    """Write checksums and sizes for DVC-managed source files."""
    records = []
    for path in sorted((root / "data_raw").glob("*")):
        if path.is_file() and path.suffix in {".gz", ".txt"}:
            records.append({"path":str(path.relative_to(root)), "bytes":path.stat().st_size, "sha256":sha256(path)})
    target = root / "data_manifest.json"
    target.write_text(json.dumps({"schema_version":"1.0", "files":records}, indent=2) + "\n", encoding="utf-8")
    return target


def results_as_dicts(results: list[ValidationResult]) -> list[dict[str, str]]:
    """Serialize validation results for monitoring integrations."""
    return [asdict(result) for result in results]
