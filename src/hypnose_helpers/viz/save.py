"""Saving figures, and the small utilities around it.

Moved from hypnose-behavior-analysis `io/save.py` (restructure_2 Phase 2a).

`save_figure` takes **`fig_dir` as a required argument**: a library owned by no dataset
must not hardcode one dataset's derivatives layout and then need a resolver hook to
escape it. Each consumer resolves its own destination and passes it in. `subjids`/`dates`
are used only to build the filename tags.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl

from .styles import _presentation_active, nice_x_locator, _PRESENTATION_MAX_YTICKS, \
    _PRESENTATION_MAX_XTICKS, _PRES_XTICK_BOXPLOT_LABELSIZE
from .metadata import build_pdf_metadata, filter_metadata


# --------------------------------------
# Size Presets
# --------------------------------------

def set_size(fig, width="single", aspect=0.75):

    if width == "single":
        w = 3.5
    elif width == "double":
        w = 7.2
    else:
        w = width  

    h = w * aspect
    fig.set_size_inches(w, h)


# --------------------------------------
# Save Utility
# --------------------------------------


def _coerce_list(val):
    if val is None:
        return []
    if isinstance(val, (list, tuple, set)):
        return list(val)
    return [val]


def _unique_sorted(items):
    try:
        return sorted(set(items))
    except Exception:
        return list(dict.fromkeys(items))


def _format_span(items, prefix: str) -> str:
    """Format subject/date identifiers into compact spans.

    - One item: prefix-<item>
    - Two items: prefix-<a>_<b>
    - Three or more: prefix-<first>-<last>
    """
    vals = _unique_sorted(items)
    if not vals:
        return ""
    if len(vals) == 1:
        return f"{prefix}-{vals[0]}"
    if len(vals) == 2:
        return f"{prefix}-{vals[0]}_{vals[1]}"
    return f"{prefix}-{vals[0]}-{vals[-1]}"


def strip_legends(fig_or_ax) -> int:
    """Remove every legend on the figure (or a single axes).

    Use this when you want a guaranteed legend-free figure regardless of what
    upstream plotting calls (seaborn, pandas .plot, etc.) auto-added.
    Call this just before saving or showing. Returns the number of legends removed.
    """
    if isinstance(fig_or_ax, mpl.figure.Figure):
        axes_iter = list(fig_or_ax.axes)
    elif isinstance(fig_or_ax, mpl.axes.Axes):
        axes_iter = [fig_or_ax]
    else:
        raise TypeError(f"Expected Figure or Axes, got {type(fig_or_ax).__name__}")
    removed = 0
    for ax in axes_iter:
        leg = ax.get_legend()
        if leg is not None:
            leg.remove()
            removed += 1
    return removed


def save_figure(
    fig: mpl.figure.Figure,
    save_name: str,
    *,
    fig_dir,
    subjids=None,
    dates=None,
    subdir=None,
    dpi: int = 600,
    bbox_inches=None,
    clear_legends: bool = False,
    boxplot: bool = False,
    provenance=None,
    metadata=None,
):
    """Save a matplotlib figure as PDF into `fig_dir`, with its provenance embedded.

    `fig_dir` is required and is where the file lands -- this module knows nothing about
    any dataset's derivatives layout. `subjids`/`dates` only build the filename tags, so
    a consumer that resolves its own directory still gets the shared naming convention.

    Parameters
    ----------
    fig_dir : str | Path
        Destination directory. Created if absent.
    subdir : str | Path | None
        Optional subdirectory inside `fig_dir` (e.g. "movement_figures"), normalised to a
        relative segment so it cannot traverse upwards.
    boxplot : bool
        Mark this as a categorical-x figure: under the presentation style its x-tick
        labels are enlarged, since the positions are the most important thing to read.
    provenance : dict | None
        A `hypnose_helpers.provenance.provenance()` record to embed. Omitted, the calling
        frame is inspected instead. Pass it explicitly whenever a wrapper sits between
        the real plotting function and this call, or frame-walking will name the wrapper
        -- see `capture_call`.
    metadata : dict | None
        Extra PDF info-dictionary entries. Keys outside the PDF standard set are dropped
        (matplotlib would warn and discard them anyway).

    Recover it later with `hypnose_helpers.viz.metadata.read_figure_metadata(path)`.
    """
    if fig is None:
        raise ValueError("fig cannot be None")
    if not save_name:
        raise ValueError("save_name must be non-empty")

    subj_list = _coerce_list(subjids)
    date_list = _coerce_list(dates)

    subj_tag = _format_span([f"{int(s):03d}" for s in subj_list], "sub") if subj_list else "sub-unknown"
    date_tag = _format_span([int(d) if str(d).isdigit() else d for d in date_list], "date") if date_list else "date-unknown"

    filename = f"{save_name}_{subj_tag}_{date_tag}.pdf"

    fig_dir = Path(fig_dir)
    if subdir:
        # Normalize to a relative path segment and avoid absolute traversal
        subdir_path = Path(str(subdir).strip()).as_posix().strip("./")
        if subdir_path:
            fig_dir = fig_dir / subdir_path
    fig_dir.mkdir(parents=True, exist_ok=True)

    out_path = fig_dir / filename

    if clear_legends:
        strip_legends(fig)

    # presentation style: cap y-ticks (and numeric x-ticks) to a few round
    # values (no rcParam for this), and, for boxplot-style figures, enlarge the
    # x-tick labels.
    if _presentation_active():
        from matplotlib.ticker import MaxNLocator, FixedLocator, FixedFormatter
        for _ax in fig.axes:
            if _PRESENTATION_MAX_YTICKS:
                _ax.yaxis.set_major_locator(
                    MaxNLocator(nbins=_PRESENTATION_MAX_YTICKS, steps=[1, 2, 2.5, 5, 10])
                )
            if _PRESENTATION_MAX_XTICKS:
                # Only touch a *numeric* x-axis: skip categorical axes (explicit string
                # labels / fixed ticks), which set a FixedFormatter/FixedLocator.
                _x_categorical = (
                    isinstance(_ax.xaxis.get_major_formatter(), FixedFormatter)
                    or isinstance(_ax.xaxis.get_major_locator(), FixedLocator)
                )
                if not _x_categorical:
                    _ax.xaxis.set_major_locator(nice_x_locator())
            if boxplot:
                _ax.tick_params(axis="x", labelsize=_PRES_XTICK_BOXPLOT_LABELSIZE)
            _ax.figure.canvas.draw_idle()

    bbox = bbox_inches if bbox_inches is not None else "tight"

    # Provenance is attached to real work, so it must never be the reason a save fails:
    # a broken frame walk or an unreadable git tree costs the metadata, not the figure.
    try:
        info = build_pdf_metadata(
            save_name, subjids=subjids, dates=dates, provenance=provenance,
        )
        info.update(metadata or {})
        info = filter_metadata(info)
    except Exception:
        info = filter_metadata(metadata or {})

    # Type 42 (TrueType) keeps PDF text editable/searchable; matplotlib's default of
    # Type 3 does not, and journals reject it. Every style dict sets this, but a caller
    # that applied no style would otherwise silently emit Type 3 -- so enforce it here,
    # scoped, rather than relying on a global mutation somewhere upstream.
    with mpl.rc_context({"pdf.fonttype": 42, "ps.fonttype": 42}):
        fig.savefig(out_path, bbox_inches=bbox, dpi=dpi, metadata=info)

    return out_path
