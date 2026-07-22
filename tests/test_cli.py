"""Tests for stable command-line behavior."""
from __future__ import annotations

import project_cli


def test_parser_exposes_operational_commands() -> None:
    parser = project_cli.build_parser()
    help_text = parser.format_help()
    for command in ["run", "stage", "validate", "manifest", "test", "status", "dvc"]:
        assert command in help_text


def test_invalid_stage_returns_usage_error(capsys) -> None:
    result = project_cli.main(["stage", "99"])
    assert result == 2
    assert "Choose 01 through 17" in capsys.readouterr().err


def test_fast_run_sets_environment(monkeypatch) -> None:
    captured = {}

    def fake_run(command, env=None):
        captured["command"] = command
        captured["env"] = env
        return 0

    monkeypatch.setattr(project_cli, "_run", fake_run)
    assert project_cli.main(["run", "--fast"]) == 0
    assert captured["env"]["FACEBOOK_ANALYSIS_FAST"] == "1"
