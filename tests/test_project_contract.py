"""Repository configuration tests that do not require analytical data."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from quality_checks import validate_repository

ROOT = Path(__file__).resolve().parents[1]


def test_data_contract_is_versioned_and_complete() -> None:
    contract = json.loads((ROOT / "config" / "data_contracts.json").read_text(encoding="utf-8"))
    assert contract["schema_version"] == "1.0"
    assert contract["unit_of_analysis"] == ["ego_id", "node_id"]
    assert "participation_coefficient" in contract["required_analysis_columns"]


def test_all_numbered_stages_exist() -> None:
    stages = sorted((ROOT / "src").glob("[0-9][0-9]_*.py"))
    assert [path.name[:2] for path in stages] == [f"{number:02d}" for number in range(18)]


@pytest.mark.integration
def test_current_repository_artifacts_pass_contracts() -> None:
    results = validate_repository(ROOT, require_artifacts=True)
    failures = [result for result in results if result.status == "FAIL"]
    assert not failures, failures
