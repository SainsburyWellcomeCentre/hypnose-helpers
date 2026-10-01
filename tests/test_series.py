#!/usr/bin/env python
"""Unit tests for `hypnose_helpers.viz.series`.

Run directly (no pytest needed)::

    python tests/test_series.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from hypnose_helpers.viz.legends import pop_legends  # noqa: E402
from hypnose_helpers.viz.series import show_series, show_suffix, tie  # noqa: E402


def _figure():
    """Series a, b (with a tied band), c (error bars) in two panels, a reference line."""
    fig, (top, bottom) = plt.subplots(2)
    parts = {
        "a": [top.plot([0, 1], label="a")[0], bottom.plot([0, 2], label="a")[0]],
        "b": [top.plot([1, 0], label="b")[0],
              tie(top.fill_between([0, 1], [0, 0], [1, 1]), "b")],
        "c": list(top.errorbar([0, 1], [0.5, 0.5], yerr=0.1, label="c").lines[0:1]),
    }
    reference = top.axhline(0.5)
    top.legend()
    return fig, parts, reference


def _shown(parts):
    return {label: all(a.get_visible() for a in artists) for label, artists in parts.items()}


def test_none_changes_nothing():
    fig, parts, reference = _figure()
    show_series(fig, None)
    assert _shown(parts) == {"a": True, "b": True, "c": True}
    assert reference.get_visible()


def test_numbers_in_any_order():
    fig, parts, reference = _figure()
    limits = fig.axes[0].get_ylim()
    show_series(fig, [3, 1])
    assert _shown(parts) == {"a": True, "b": False, "c": True}
    assert reference.get_visible()
    assert fig.axes[0].get_ylim() == limits
    rows = {t.get_text(): t.get_visible() for t in fig.axes[0].get_legend().get_texts()}
    assert rows == {"a": True, "b": False, "c": True}


def test_labels_and_single_values():
    fig, parts, _ = _figure()
    show_series(fig, "b")
    assert _shown(parts) == {"a": False, "b": True, "c": False}
    fig, parts, _ = _figure()
    show_series(fig, [2])
    assert _shown(parts) == {"a": False, "b": True, "c": False}


def test_bad_selection_raises():
    for bad in ([4], [0], ["missing"]):
        fig, _, _ = _figure()
        try:
            show_series(fig, bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad} did not raise")


def test_pop_legends_skips_hidden_rows():
    fig, _, _ = _figure()
    show_series(fig, [1, 3])
    assert [label for _, label in pop_legends(fig, legend=False)] == ["a", "c"]


def test_suffix():
    assert show_suffix(None) == ""
    assert show_suffix([3, 1]) == "_show-1-3"
    assert show_suffix(2) == "_show-2"
    assert show_suffix(["rewards", "excess correct"]) == "_show-rewards-excess_correct"


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        plt.close("all")
        print(f"ok  {test.__name__}")
    print(f"{len(tests)} passed")
