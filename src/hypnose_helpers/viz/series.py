"""Showing a figure's series a few at a time, to build a slide up step by step.

A series is everything in a figure carrying one legend label: every axes artist with that
label (one line per panel, say), plus any artist a plotter ties to it with `tie` -- a band,
error bars or markers drawn without a label of their own. Series are numbered 1, 2, ... in
legend order, or, in a figure without a legend, in the order they were drawn.

- `show_series(fig, show)` -- show only the series in ``show``; None leaves the figure as
  drawn, every series shown; 0 shows none, the first frame of a build-up.
- `show_suffix(show)` -- the save-name suffix of a selection, so each step saves apart.

Hidden artists keep their place, so axis limits and ticks stay the same from step to step,
and a hidden series' legend row stays as a blank, so the legend box does not move.
Unlabelled artists (reference lines, session boundaries, grids) always stay.
"""
from __future__ import annotations

import re

from .legends import _rows

__all__ = ["show_series", "show_suffix", "tie"]

_TIE = "series:"


def tie(artist, label: str):
    """Tie an unlabelled ``artist`` to the series labelled ``label``; returns the artist."""
    artist.set_gid(f"{_TIE}{label}")
    return artist


def _legends(fig) -> list:
    return [leg for leg in [ax.get_legend() for ax in fig.axes] + list(fig.legends)
            if leg is not None]


def _labels(fig) -> list:
    """The figure's series labels in legend order, or in drawing order without a legend."""
    labels = []
    for leg in _legends(fig):
        labels += [text.get_text() for text in leg.get_texts()]
    if not labels:
        for ax in fig.axes:
            labels += ax.get_legend_handles_labels()[1]
    return list(dict.fromkeys(labels))


def _selected(fig, show) -> set:
    """The labels ``show`` names: series numbers (1-based) or labels, in any order; 0 names
    none."""
    labels = _labels(fig)
    chosen = set()
    for item in [show] if isinstance(show, (int, str)) else show:
        if isinstance(item, str):
            if item not in labels:
                raise ValueError(f"no series labelled {item!r}; the series are {labels}")
            chosen.add(item)
        elif int(item) != 0:
            if not 1 <= int(item) <= len(labels):
                raise ValueError(f"series {item} out of range; the series are "
                                 f"{dict(enumerate(labels, 1))}")
            chosen.add(labels[int(item) - 1])
    return chosen


def _flatten(container):
    for part in container:
        if isinstance(part, (tuple, list)):
            yield from _flatten(part)
        elif part is not None:
            yield part


def show_series(fig, show=None) -> None:
    """Show only the series ``show`` names, and their legend rows; None changes nothing.

    ``show`` is a series number, a label, or a list of either, in any order:
    ``[1]``, ``[1, 2]``, ``[3, 1]``, ``["rewards"]``. ``0`` shows no series, only the axes
    and unlabelled artists, as the first frame of a build-up.
    """
    if show is None:
        return
    keep = _selected(fig, show)
    series = set(_labels(fig))

    def visible(label):
        return label not in series or label in keep

    for ax in fig.axes:
        for artist in ax.get_children():
            gid = artist.get_gid() or ""
            label = gid[len(_TIE):] if gid.startswith(_TIE) else artist.get_label()
            if label in series:
                artist.set_visible(visible(label))
        for container in ax.containers:
            if container.get_label() in series:
                for artist in _flatten(container):
                    artist.set_visible(visible(container.get_label()))
    for leg in _legends(fig):
        for text, glyph in _rows(leg):
            shown = visible(text.get_text())
            for artist in glyph:
                artist.set_visible(shown)
            text.set_visible(shown)


def show_suffix(show) -> str:
    """``"_show-1-3"`` for a selection, ``""`` for None; numbers sorted, labels kept."""
    if show is None:
        return ""
    items = [show] if isinstance(show, (int, str)) else list(show)
    if all(not isinstance(item, str) for item in items):
        items = sorted(int(item) for item in items)
    return "_show-" + "-".join(re.sub(r"\W+", "_", str(item)) for item in items)
