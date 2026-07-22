"""Unit tests for deterministic graph and statistical helpers."""
from __future__ import annotations

import numpy as np

from pipeline_lib import _entropy, _partial_slope, read_edges


def test_entropy_boundaries() -> None:
    assert _entropy([]) != _entropy([])  # NaN for an undefined neighborhood.
    assert _entropy(["a", "a", "a"]) == 0.0
    assert np.isclose(_entropy(["a", "b", "c", "d"]), 1.0)


def test_read_edges_deduplicates_orientation_and_self_loops(tmp_path) -> None:
    path = tmp_path / "network.edges"
    path.write_text("1 2\n2 1\n2 2\n2 3\n", encoding="utf-8")
    edges, invalid, duplicates = read_edges(path)
    assert edges == [(1, 2), (2, 3)]
    assert duplicates == 1
    assert invalid == [(3, "2 2", "self_loop")]


def test_partial_slope_recovers_linear_effect() -> None:
    degree = np.tile(np.arange(1, 11), 2)
    ego = np.repeat([0, 1], 10)
    x = np.linspace(-1, 1, 20)
    y = 2.5 * x + 0.3 * np.log1p(degree) + ego
    assert np.isclose(_partial_slope(y, x, degree, ego), 2.5)
