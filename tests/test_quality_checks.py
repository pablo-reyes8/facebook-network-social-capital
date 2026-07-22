"""Unit tests for source-data contracts and checksum manifests."""
from __future__ import annotations

import gzip
import io
import json
import tarfile

from quality_checks import sha256, validate_raw_data, write_data_manifest


def _synthetic_raw_data(root) -> None:
    raw = root / "data_raw"
    raw.mkdir()
    with gzip.open(raw / "facebook_combined.txt.gz", "wt", encoding="utf-8") as handle:
        handle.write("1 2\n")
    with tarfile.open(raw / "facebook.tar.gz", "w:gz") as archive:
        for ego in range(10):
            for suffix in ["edges", "feat", "egofeat", "featnames", "circles"]:
                name = f"facebook/{ego}.{suffix}"
                data = b"1 2\n" if suffix == "edges" else b"0\n"
                info = tarfile.TarInfo(name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))


def test_sha256_is_stable(tmp_path) -> None:
    path = tmp_path / "value.txt"
    path.write_text("network science\n", encoding="utf-8")
    assert sha256(path) == "5bc9fa8dc90dfcd2aafc132c8d7c67b9598c193574dd0633263378e73e42c358"


def test_raw_contract_accepts_expected_archive(tmp_path) -> None:
    _synthetic_raw_data(tmp_path)
    results = validate_raw_data(tmp_path)
    assert results
    assert all(result.status == "PASS" for result in results)


def test_manifest_records_checksums(tmp_path) -> None:
    _synthetic_raw_data(tmp_path)
    target = write_data_manifest(tmp_path)
    manifest = json.loads(target.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "1.0"
    assert {record["path"] for record in manifest["files"]} == {
        "data_raw/facebook.tar.gz", "data_raw/facebook_combined.txt.gz"
    }
    assert all(len(record["sha256"]) == 64 for record in manifest["files"])
