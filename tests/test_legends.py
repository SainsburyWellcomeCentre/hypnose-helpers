#!/usr/bin/env python
"""Unit tests for `hypnose_helpers.viz.legends` and `use_style(separate_legends=...)`.

Run directly (no pytest needed)::

    python tests/test_legends.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from hypnose_helpers.viz.legends import (  # noqa: E402
    legend_figure, legends_apart, pop_legends, show_apart,
)
from hypnose_helpers.viz.styles import legends_separate, use_style  # noqa: E402


def _figure():
    """Two axes with legends sharing a label, and a figure legend."""
    fig, (top, bottom) = plt.subplots(2)
    top.plot([0, 1], label="a")
    top.plot([1, 0], label="b")
    top.legend()
    bottom.plot([0, 1], label="a")
    bottom.legend()
    line, = bottom.plot([0, 2])
    fig.legend([line], ["c"])
    return fig


def test_use_style_switch():
    use_style("presentation")
    assert legends_separate()
    use_style("nature")
    assert not legends_separate()
    use_style("presentation", separate_legends=False)
    assert not legends_separate()
    use_style("nature", separate_legends=True)
    assert legends_separate()


def test_legends_apart_override():
    use_style("nature")
    assert legends_apart(None) is False
    assert legends_apart(False) is True
    assert legends_apart(True) is False
    use_style("presentation")
    assert legends_apart(None) is True
    assert legends_apart(True) is False


def test_pop_keeps_inline_legends():
    use_style("nature")
    fig = _figure()
    assert pop_legends(fig) == []
    assert all(ax.get_legend() is not None for ax in fig.axes)
    assert len(fig.legends) == 1


def test_pop_removes_and_returns_entries():
    use_style("nature")
    fig = _figure()
    entries = pop_legends(fig, legend=False)
    assert [label for _, label in entries] == ["a", "b", "a", "c"]
    assert all(ax.get_legend() is None for ax in fig.axes)
    assert fig.legends == []


def test_pop_returns_plotted_artists_and_keeps_proxies():
    from matplotlib.container import ErrorbarContainer
    use_style("nature")
    fig, ax = plt.subplots()
    ax.errorbar([0, 1], [0, 1], yerr=0.1, fmt="o", label="e")
    proxy = plt.Line2D([], [], color="k")
    ax.legend(handles=[ax.get_legend_handles_labels()[0][0], proxy], labels=["e", "proxy"])
    (errorbar, _), (kept, label) = pop_legends(fig, legend=False)
    assert isinstance(errorbar, ErrorbarContainer), type(errorbar)
    assert label == "proxy" and kept is not proxy  # the legend's own copy of the proxy


def test_legend_figure_dedupes():
    use_style("nature")
    entries = pop_legends(_figure(), legend=False)
    fig = legend_figure(entries)
    labels = [text.get_text() for text in fig.legends[0].get_texts()]
    assert labels == ["a", "b", "c"]
    fig.canvas.draw()
    assert legend_figure([]) is None


def _png_width(png: bytes) -> int:
    return int.from_bytes(png[16:20], "big")


def test_legend_png_is_print_resolution():
    from hypnose_helpers.viz.legends import _png
    fig = legend_figure(pop_legends(_figure(), legend=False))
    ratio = _png_width(_png(fig, 300)) / _png_width(_png(fig, 100))
    assert abs(ratio - 3) < 0.05, ratio


def _in_notebook(make):
    """``(figure, displayed objects)`` from ``make()`` run under a stand-in IPython, or None
    without IPython."""
    try:
        import IPython.display as ipd
        from IPython.core.interactiveshell import InteractiveShell
    except ImportError:
        print("    (IPython not installed: skipped)")
        return None
    shown, original = [], ipd.display
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # a plain interpreter is not a virtualenv IPython
        InteractiveShell.instance()
    ipd.display = shown.append
    try:
        fig = make()
    finally:
        ipd.display = original
        InteractiveShell.clear_instance()
    return fig, shown


def test_notebook_shows_png_and_closes_the_canvas():
    run = _in_notebook(lambda: legend_figure(pop_legends(_figure(), legend=False)))
    if run is None:
        return
    fig, shown = run
    import IPython.display as ipd
    assert len(shown) == 1 and isinstance(shown[0], ipd.Image)
    assert abs(shown[0].width - _png_width(shown[0].data) / 3) <= 1
    assert not plt.fignum_exists(fig.number)


def test_show_apart_any_figure():
    def make():
        fig, ax = plt.subplots(figsize=(2, 1))
        ax.table(cellText=[["a", "1"]], loc="center")
        ax.axis("off")
        show_apart(fig)
        return fig
    run = _in_notebook(make)
    if run is None:
        return
    fig, shown = run
    assert len(shown) == 1 and shown[0].data[:8] == b"\x89PNG\r\n\x1a\n"
    assert not plt.fignum_exists(fig.number)


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        plt.close("all")
        print(f"ok  {test.__name__}")
    use_style("nature")
    print(f"{len(tests)} passed")
