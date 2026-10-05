"""The plotter convention: what every plotting function does with the figures it draws.

Every plotting function in the family takes ``legend`` and ``show`` and makes the calls
below, so `use_style` and the caller can reshape its figures for slides without the function
knowing how::

    def plot_something(..., legend=None, show=None, save=False):
        figures, entries = {}, []
        for ...:                                            # each figure it draws
            fig = ...                                       # drawn whole, legend included
            entries += finish_figure(fig, legend, show)     # before saving
            if save:
                save_figure(fig, f"something{show_suffix(show)}", ...)
        legend_figure(entries)                              # once, after the figures
        return figures

- ``legend`` -- True: in the figure; False: set apart in one legend-only figure, shown and
  never saved; None: as `use_style` says, apart under the presentation style.
- ``show`` -- the series to draw, by legend number or label in any order, to build a slide
  up step by step; 0 draws none (the first frame), None draws them all. `show_suffix` keeps
  each step's file apart.

Draw every series with a label, in a fixed order: legend order is the numbering ``show``
uses. An artist that belongs to a series without carrying its label (a band, error bars,
markers) is tied to it with `tie` when it is drawn.
"""
from __future__ import annotations

from .legends import legend_figure, pop_legends
from .series import show_series, show_suffix, tie

__all__ = ["finish_figure", "legend_figure", "show_suffix", "tie"]


def finish_figure(fig, legend: bool | None = None, show=None) -> list:
    """Apply ``show`` and ``legend`` to a drawn figure, before it is saved.

    Hides the series ``show`` leaves out, then sets the legends apart when ``legend`` (or
    `use_style`) says so, and returns their entries for `legend_figure` -- in that order,
    so the legend figure lists only the series shown. With both None under a style that
    keeps legends in the figure, the figure is left as drawn and the list is empty.
    """
    show_series(fig, show)
    return pop_legends(fig, legend)
