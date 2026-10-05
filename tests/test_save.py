#!/usr/bin/env python
"""Unit tests for `hypnose_helpers.viz.save`'s presentation tick caps.

Run directly (no pytest needed)::

    python tests/test_save.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import LogLocator, MaxNLocator  # noqa: E402

from hypnose_helpers.viz.save import save_figure  # noqa: E402
from hypnose_helpers.viz.styles import use_style  # noqa: E402


def test_presentation_caps_linear_axes_only():
    use_style("presentation")
    fig, (linear, logged) = plt.subplots(2)
    linear.plot([0, 3000], [0, 3000])
    logged.plot([0, 3000], [0.5, 3000])
    logged.set_yscale("log")
    with tempfile.TemporaryDirectory() as tmp:
        save_figure(fig, "caps", fig_dir=tmp)
    assert isinstance(linear.yaxis.get_major_locator(), MaxNLocator)
    assert isinstance(logged.yaxis.get_major_locator(), LogLocator)
    ticks = [t for t in logged.get_yticks() if 0.5 <= t <= 3000]
    assert all(t > 0 for t in ticks) and len(ticks) <= 5, ticks


def test_tickless_axes_stay_tickless():
    use_style("presentation")
    fig, ax = plt.subplots()
    mesh = ax.pcolormesh([[0, 1], [1, 0]])
    bar = fig.colorbar(mesh, ax=ax, location="top")
    with tempfile.TemporaryDirectory() as tmp:
        save_figure(fig, "tickless", fig_dir=tmp)
    assert list(bar.ax.get_yticks()) == []


def test_titles_false_saves_untitled_and_restores():
    use_style("nature")
    fig, (top, bottom) = plt.subplots(2)
    top.set_title("top")
    bottom.set_title("left", loc="left")
    fig.suptitle("figure")
    texts = [top.title, bottom._left_title, fig._suptitle]
    at_save = []
    save = fig.savefig
    fig.savefig = lambda *a, **k: (at_save.append([t.get_visible() for t in texts]),
                                   save(*a, **k))
    with tempfile.TemporaryDirectory() as tmp:
        save_figure(fig, "titled", fig_dir=tmp)
        save_figure(fig, "untitled", fig_dir=tmp, titles=False)
    assert at_save == [[True, True, True], [False, False, False]], at_save
    assert all(t.get_visible() for t in texts)


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        plt.close("all")
        print(f"ok  {test.__name__}")
    use_style("nature")
    print(f"{len(tests)} passed")
