#!/usr/bin/env python3
"""Command-line interface for development, validation, and reproducibility.

The CLI is deliberately a thin operational layer over the numbered scientific
scripts. It does not duplicate analytical logic or change scientific defaults.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STAGES = {
    f"{number:02d}": path
    for number, path in enumerate(
        [
            "01_extract_and_inventory.py", "02_validate_raw_data.py", "03_build_ego_graphs.py",
            "04_parse_features.py", "05_construct_sample.py", "06_descriptive_networks.py",
            "07_detect_communities.py", "08_compute_social_similarity.py", "09_compute_cohesion.py",
            "10_compute_brokerage.py", "11_build_node_level_dataset.py", "12_statistical_analysis.py",
            "13_permutation_tests.py", "14_robustness_checks.py", "15_make_figures.py",
            "16_make_tables.py", "17_generate_sample_text.py",
        ],
        start=1,
    )
}


def _run(command: list[str], env: dict[str, str] | None = None) -> int:
    """Run a child command from the repository root and return its exit code."""
    return subprocess.run(command, cwd=ROOT, env=env, check=False).returncode


def command_run(args: argparse.Namespace) -> int:
    """Execute the complete analytical pipeline."""
    env = os.environ.copy()
    if args.fast:
        env["FACEBOOK_ANALYSIS_FAST"] = "1"
    return _run([sys.executable, str(ROOT / "run_project.py")], env=env)


def command_stage(args: argparse.Namespace) -> int:
    """Execute one numbered stage for development or debugging."""
    stage = args.number.zfill(2)
    if stage not in STAGES:
        print(f"Unknown stage {args.number}. Choose 01 through 17.", file=sys.stderr)
        return 2
    return _run([sys.executable, str(ROOT / "src" / STAGES[stage])])


def _load_quality_module():
    spec = importlib.util.spec_from_file_location("quality_checks", ROOT / "src" / "quality_checks.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def command_validate(args: argparse.Namespace) -> int:
    """Validate source data and, when available, generated artifacts."""
    module = _load_quality_module()
    results = module.validate_repository(ROOT, require_artifacts=args.require_artifacts)
    for result in results:
        print(f"[{result.status}] {result.name}: {result.detail}")
    failed = [result for result in results if result.status == "FAIL"]
    print(f"Validation summary: {len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


def command_manifest(_: argparse.Namespace) -> int:
    """Create a checksum manifest for DVC-managed source data."""
    module = _load_quality_module()
    target = module.write_data_manifest(ROOT)
    print(f"Wrote {target.relative_to(ROOT)}")
    return 0


def command_test(args: argparse.Namespace) -> int:
    """Run the automated test suite with optional integration tests."""
    command = [sys.executable, "-m", "pytest"]
    if not args.integration:
        command.extend(["-m", "not integration"])
    if args.coverage:
        command.extend(["--cov", "--cov-report=term-missing"])
    return _run(command)


def command_status(_: argparse.Namespace) -> int:
    """Print concise pipeline and DVC state information."""
    status_file = ROOT / "outputs" / "0_logs" / "pipeline_status.csv"
    audit_file = ROOT / "outputs" / "0_logs" / "final_audit.md"
    print("Pipeline status:")
    if status_file.exists():
        lines = status_file.read_text(encoding="utf-8").splitlines()[1:]
        successes = sum(",success," in line for line in lines)
        print(f"  {successes}/{len(lines)} stages successful")
    else:
        print("  not run locally")
    print(f"Final audit: {'available' if audit_file.exists() else 'not available'}")
    if (ROOT / ".dvc").exists():
        return _run([sys.executable, "-m", "dvc", "status"])
    print("DVC: not initialized")
    return 0


def command_dvc(_: argparse.Namespace) -> int:
    """Reproduce the versioned DVC pipeline."""
    env = os.environ.copy()
    env["PATH"] = str(ROOT / ".venv" / "bin") + os.pathsep + env.get("PATH", "")
    return _run([sys.executable, "-m", "dvc", "repro"], env=env)


def build_parser() -> argparse.ArgumentParser:
    """Build the public CLI parser."""
    parser = argparse.ArgumentParser(
        prog="facebook-graph-analysis",
        description="Operate the Facebook ego-network research pipeline.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="run all 17 analytical stages")
    run_parser.add_argument("--fast", action="store_true", help="use 200 rather than 1,000 permutations")
    run_parser.set_defaults(func=command_run)

    stage_parser = subparsers.add_parser("stage", help="run one stage (01-17)")
    stage_parser.add_argument("number", help="two-digit stage number")
    stage_parser.set_defaults(func=command_stage)

    validate_parser = subparsers.add_parser("validate", help="run data and artifact contracts")
    validate_parser.add_argument("--require-artifacts", action="store_true", help="fail when derived artifacts are absent")
    validate_parser.set_defaults(func=command_validate)

    manifest_parser = subparsers.add_parser("manifest", help="write source-data checksums")
    manifest_parser.set_defaults(func=command_manifest)

    test_parser = subparsers.add_parser("test", help="run automated tests")
    test_parser.add_argument("--integration", action="store_true", help="include tests that inspect generated artifacts")
    test_parser.add_argument("--coverage", action="store_true", help="collect coverage")
    test_parser.set_defaults(func=command_test)

    status_parser = subparsers.add_parser("status", help="show pipeline, audit, and DVC status")
    status_parser.set_defaults(func=command_status)

    dvc_parser = subparsers.add_parser("dvc", help="reproduce through DVC")
    dvc_parser.set_defaults(func=command_dvc)
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point used by both Python and the installed console script."""
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
