"""Legends set apart from their figures, for slides.

Under ``use_style(..., separate_legends=True)`` -- on by default for the presentation
style -- a plotter that supports it draws its figures without legends and shows their
entries once, in a legend-only figure that is never saved. A plotter supports it by taking
a ``legend`` argument (True: in the figure, False: apart, None: as `use_style` says) and
calling:

- `pop_legends(fig, legend)` -- on each figure before saving it: removes the legends when
  they are set apart, and returns their entries.
- `legend_figure(entries)` -- once, after the figures: one figure holding every distinct
  entry.

`show_apart(fig)` shows any other figure set apart the same way -- a table, a key -- and
closes it, so it is never saved.
"""
from __future__ import annotations

import io

import matplotlib.pyplot as plt
from matplotlib.offsetbox import DrawingArea, OffsetBox, TextArea

from .styles import legends_separate

__all__ = ["LEGEND_DPI", "legend_figure", "legends_apart", "pop_legends", "show_apart"]

# The legend figure is never saved, so what is copied off the notebook is what it shows:
# rendered at print resolution, not the screen's.
LEGEND_DPI = 300

# Pixels per inch the notebook shows the legend at, so it looks the size it would on screen.
_SCREEN_DPI = 100


def legends_apart(legend: bool | None = None) -> bool:
    """Whether legends go apart: ``legend=False`` sets them apart, True keeps them in the
    figure, None follows `use_style`."""
    return legends_separate() if legend is None else not legend


def _handles(leg) -> list:
    """A legend's handles, under the attribute name of either matplotlib generation."""
    handles = getattr(leg, "legend_handles", None)
    return list(handles if handles is not None else leg.legendHandles)


def _rows(leg) -> list:
    """``[(text, artists), ...]``: each legend row's label and every artist of its glyph.

    An errorbar's glyph is several artists (bars, marker line), of which
    `Legend.legend_handles` keeps only the first. Found by walking the legend's boxes for
    a box holding one glyph area and one text area; falls back to the first artist alone.
    """
    rows = []

    def walk(box):
        kids = box.get_children()
        areas = [k for k in kids if isinstance(k, DrawingArea)]
        texts = [k for k in kids if isinstance(k, TextArea)]
        if len(kids) == 2 and len(areas) == 1 and len(texts) == 1:
            rows.append((texts[0].get_children()[0], list(areas[0].get_children())))
            return
        for kid in kids:
            if isinstance(kid, OffsetBox):
                walk(kid)

    for box in leg.get_children():
        if isinstance(box, OffsetBox):
            walk(box)
    if len(rows) != len(leg.get_texts()):
        return [(text, [handle]) for handle, text in zip(_handles(leg), leg.get_texts())]
    return rows


def pop_legends(fig, legend: bool | None = None) -> list:
    """Remove ``fig``'s legends when they are set apart, and return their entries.

    Returns ``[(handle, label), ...]`` from every axes legend and figure legend, in order,
    leaving out rows `series.show_series` hid; empty, with the figure untouched, when
    legends stay in the figure. A handle is the plotted artist carrying the label where
    there is one, so an errorbar keeps its marker in the legend figure; otherwise the
    legend's own (a proxy handle, say).
    """
    if not legends_apart(legend):
        return []
    plotted = {}
    for ax in fig.axes:
        for handle, label in zip(*ax.get_legend_handles_labels()):
            plotted.setdefault(label, handle)
    entries = []
    for leg in [ax.get_legend() for ax in fig.axes] + list(fig.legends):
        if leg is None:
            continue
        entries += [(plotted.get(text.get_text(), handle), text.get_text())
                    for handle, text in zip(_handles(leg), leg.get_texts())
                    if text.get_visible()]
        leg.remove()
    return entries


def legend_figure(entries, fontsize=None, dpi: int = LEGEND_DPI):
    """A figure holding only a legend, one row per distinct label in first-seen order.

    Never saved. In a notebook it is shown as a PNG at ``dpi``, trimmed to the legend, so a
    copy of it is sharp on a slide, and the figure is closed so the screen-resolution
    canvas does not show as well. Returns the figure; None when there are no entries.
    """
    first = {}
    for handle, label in entries:
        first.setdefault(label, handle)
    if not first:
        return None
    fig = plt.figure(figsize=(4.0, 0.4 + 0.35 * len(first)))
    fig.legend(list(first.values()), list(first), loc="center", frameon=False,
               fontsize=fontsize)
    show_apart(fig, dpi)
    return fig


def _png(fig, dpi: int) -> bytes:
    """The figure as PNG bytes at ``dpi``, trimmed to what it draws."""
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=dpi, bbox_inches="tight", pad_inches=0.05,
                facecolor="white")
    return buffer.getvalue()


def show_apart(fig, dpi: int = LEGEND_DPI) -> None:
    """In IPython, show ``fig`` as a ``dpi`` PNG at its screen size, trimmed, and close it.

    For a figure set apart for slides: what is copied off the notebook is print resolution,
    and the closed figure is never saved or shown again. Outside IPython nothing happens.
    """
    try:
        from IPython import get_ipython
        from IPython.display import Image, display
    except ImportError:
        return
    if get_ipython() is None:
        return
    png = _png(fig, dpi)
    width = int.from_bytes(png[16:20], "big")  # the IHDR chunk's pixel width
    display(Image(data=png, width=round(width * _SCREEN_DPI / dpi)))
    plt.close(fig)
