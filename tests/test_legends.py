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

from hypnose_helpers.viz.legends import legend_figure, legends_apart, pop_legends  # noqa: E402
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


def test_notebook_shows_png_and_closes_the_canvas():
    try:
        import IPython.display as ipd
        from IPython.core.interactiveshell import InteractiveShell
    except ImportError:
        print("    (IPython not installed: skipped)")
        return
    shown, original = [], ipd.display
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # a plain interpreter is not a virtualenv IPython
        InteractiveShell.instance()
    ipd.display = shown.append
    try:
        fig = legend_figure(pop_legends(_figure(), legend=False))
    finally:
        ipd.display = original
        InteractiveShell.clear_instance()
    assert len(shown) == 1 and isinstance(shown[0], ipd.Image)
    assert abs(shown[0].width - _png_width(shown[0].data) / 3) <= 1
    assert not plt.fignum_exists(fig.number)


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        plt.close("all")
        print(f"ok  {test.__name__}")
    use_style("nature")
    print(f"{len(tests)} passed")
