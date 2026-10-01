#!/usr/bin/env python
"""Unit tests for `hypnose_helpers.viz.plotter`.

Run directly (no pytest needed)::

    python tests/test_plotter.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from hypnose_helpers.viz.plotter import finish_figure, legend_figure  # noqa: E402
from hypnose_helpers.viz.styles import use_style  # noqa: E402


def _figure():
    fig, ax = plt.subplots()
    lines = [ax.plot([0, i], label=label)[0] for i, label in enumerate("abc", 1)]
    ax.legend()
    return fig, lines


def test_defaults_leave_the_figure_as_drawn():
    use_style("nature")
    fig, lines = _figure()
    assert finish_figure(fig) == []
    assert all(line.get_visible() for line in lines)
    assert fig.axes[0].get_legend() is not None


def test_show_then_legend_apart():
    use_style("nature")
    fig, lines = _figure()
    entries = finish_figure(fig, legend=False, show=[3, 2])
    assert [line.get_visible() for line in lines] == [False, True, True]
    assert fig.axes[0].get_legend() is None
    assert [label for _, label in entries] == ["b", "c"]
    legend = legend_figure(entries)
    assert [t.get_text() for t in legend.legends[0].get_texts()] == ["b", "c"]


def test_presentation_sets_legends_apart():
    use_style("presentation")
    fig, _ = _figure()
    assert [label for _, label in finish_figure(fig)] == ["a", "b", "c"]
    fig, _ = _figure()
    assert finish_figure(fig, legend=True) == []


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        plt.close("all")
        print(f"ok  {test.__name__}")
    use_style("nature")
    print(f"{len(tests)} passed")
