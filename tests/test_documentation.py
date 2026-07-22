"""Documentation integrity checks for the GitHub landing page."""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def test_readme_local_links_resolve() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    links = re.findall(r"\[[^]]*\]\(([^)]+)\)", text)
    local = [unquote(link.split("#", 1)[0]) for link in links if not link.startswith(("http://", "https://", "#"))]
    missing = [link for link in local if link and not (ROOT / link).exists()]
    assert not missing, f"Broken README links: {missing}"


def test_readme_discloses_research_scope() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "not an official MIT research publication" in text
    assert "not causal effects" in text
