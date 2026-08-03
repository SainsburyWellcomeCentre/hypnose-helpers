"""Figure styles shared across the Hypnose repos.

Moved verbatim from hypnose-behavior-analysis `io/save.py` (restructure_2 Phase 2a) so
every repo plotting Hypnose data produces the same look.

**This module does not touch `rcParams` at import.** It exports the style builders and an
explicit `use_style()`; consumers decide when to apply. Two packages mutating global
rcParams at module scope means whoever imports last silently wins -- which is how
hypnose-somnotate's vendored configuration.py and this module used to collide.
"""
from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt
from cycler import cycler


def nature_style() -> dict:
    """
    Return rcParams dict for 'nature-style' figures.
    """
    return {
        # Font
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 8,
        "mathtext.fontset": "dejavusans",
        "mathtext.default": "regular",

        # Axes
        "axes.linewidth": 0.8,
        "axes.labelsize": 20,
        "axes.titlesize": 9,
        "axes.labelpad": 3,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,          # ensure no grid
        "axes.facecolor": "white",
        "axes.formatter.useoffset": False,

        # Lines
        "lines.linewidth": 1.0,
        "lines.markersize": 4,
        "lines.markeredgewidth": 0.8,

        # Ticks
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "xtick.major.size": 6,
        "ytick.major.size": 6,
        "xtick.minor.visible": False,
        "ytick.minor.visible": False,
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,

        # Legend
        "legend.frameon": False,
        "legend.fontsize": 7,
        "legend.handlelength": 1.2,
        "legend.handletextpad": 0.4,

        # Color cycle
        "axes.prop_cycle": cycler(color=[
            "#E64B35", "#4DBBD5", "#00A087",
            "#3C5488", "#F39B7F", "#8491B4",
            "#91D1C2", "#DC0000", "#7E6148"
        ]),

        # Figure (keep display compact; saving uses explicit dpi)
        "figure.dpi": 110,
        "savefig.dpi": 600,
        "figure.facecolor": "white",

        # PDF/SVG
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",

        "image.composite_image": False,
    }


def poster_style() -> dict:
    """
    Return rcParams dict for poster figures.

    Same typographic family and color cycle as nature_style(), but with:
    - titles hidden (axes.titlesize = 0)
    - larger fonts for axis labels, ticks, legend
    - thicker spines, ticks, and lines for visibility at viewing distance
    - 600 dpi for both display and save
    """
    return {
        # Font
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 22,
        "font.weight": "bold",       # bold tick labels (no per-tick weight rcParam exists)
        "mathtext.fontset": "dejavusans",
        "mathtext.default": "regular",

        # Axes
        "axes.linewidth": 3.5,
        "axes.labelsize": 36,
        "axes.labelweight": "bold",
        "axes.titlesize": 0,         # no per-axes titles on posters
        "axes.titleweight": "bold",
        "axes.titlepad": 0,
        "axes.labelpad": 6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
        "axes.facecolor": "white",
        "axes.formatter.useoffset": False,

        # Figure-level title (suptitle) — also suppressed for posters
        "figure.titlesize": 0,
        "figure.titleweight": "bold",

        # Lines
        #"lines.linewidth": 2.5,
        #"lines.markersize": 8,
        #"lines.markeredgewidth": 1.5,

        "lines.linewidth": 1.0,
        "lines.markersize": 4,
        "lines.markeredgewidth": 0.8,

        # Ticks
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.width": 2.0,
        "ytick.major.width": 2.0,
        "xtick.major.size": 12,
        "ytick.major.size": 12,
        "xtick.minor.visible": False,
        "ytick.minor.visible": False,
        "xtick.labelsize": 28,
        "ytick.labelsize": 28,

        # Legend — off by default. Auto-added legends (e.g. from seaborn) become
        # invisible via fontsize=0; add legends manually with an explicit fontsize
        # kwarg, e.g. ax.legend(fontsize=18, frameon=False), when you want one.
        "legend.frameon": False,
        "legend.fontsize": 10,

        # Color cycle (matches nature_style for consistency across figure sets)
        "axes.prop_cycle": cycler(color=[
            "#E64B35", "#4DBBD5", "#00A087",
            "#3C5488", "#F39B7F", "#8491B4",
            "#91D1C2", "#DC0000", "#7E6148"
        ]),

        # Figure
        "figure.dpi": 110,
        "savefig.dpi": 600,
        "figure.facecolor": "white",

        # PDF/SVG
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",

        "image.composite_image": False,
    }


# Distinctive rcParam values that identify the presentation style at save time
# (used so the y-tick cap works no matter how the style was applied — via
# use_presentation_style() OR a bare mpl.rcParams.update(presentation_style())).
_PRES_AXES_LABELSIZE = 24
_PRES_TICK_LABELSIZE = 18
_PRES_AXES_LINEWIDTH = 2.0
# Boxplot-style figures get even bigger x-tick labels (the category positions
# are the most important thing to read). Applied by save_figure(boxplot=True).
_PRES_XTICK_BOXPLOT_LABELSIZE = 28

# Number of y-ticks the presentation style caps to (no rcParam exists for tick
# count, so save_figure enforces it per-axes). Configurable via
# use_presentation_style(max_yticks=...).
_PRESENTATION_MAX_YTICKS = 4
# Same idea for x-ticks: cap a numeric x-axis to a few nicely rounded values
# (5, 10, 15, ... rather than 7, 14, 21). Categorical x-axes (explicit string
# tick labels, e.g. boxplot/violin/position plots) are left untouched.
# Configurable via use_presentation_style(max_xticks=...).
_PRESENTATION_MAX_XTICKS = 5


def presentation_style() -> dict:
    """Return rcParams dict for 'presentation' figures (projector-friendly).

    Same as nature_style(), but tuned for readability on a big projector:
    - bigger, bold tick labels (x and y)
    - bigger, bold axis labels
    - thicker axis lines and ticks

    The y-axis tick count is also capped (default 4). That has no rcParam
    equivalent, so it is enforced per-axes by save_figure whenever this style is
    active — detected from the rcParams below — so both
    ``mpl.rcParams.update(presentation_style())`` and
    ``use_presentation_style()`` get the cap.
    """
    style = nature_style()
    style.update({
        # Bold fonts throughout. There is no per-tick weight rcParam, so bolding
        # the global font weight is what makes tick labels bold.
        "font.weight": "bold",

        # Axis labels: bigger + bold
        "axes.labelsize": _PRES_AXES_LABELSIZE,
        "axes.labelweight": "bold",

        # Tick labels: bigger (bold comes from font.weight above)
        "xtick.labelsize": _PRES_TICK_LABELSIZE,
        "ytick.labelsize": _PRES_TICK_LABELSIZE,

        # Thicker axis lines and ticks
        "axes.linewidth": _PRES_AXES_LINEWIDTH,
        "xtick.major.width": 2.0,
        "ytick.major.width": 2.0,
        "xtick.major.size": 8,
        "ytick.major.size": 8,
    })
    return style


def _presentation_active() -> bool:
    """True when the presentation style is the active matplotlib style."""
    try:
        return (
            float(mpl.rcParams.get("axes.labelsize", 0)) == float(_PRES_AXES_LABELSIZE)
            and float(mpl.rcParams.get("xtick.labelsize", 0)) == float(_PRES_TICK_LABELSIZE)
            and float(mpl.rcParams.get("axes.linewidth", 0)) == float(_PRES_AXES_LINEWIDTH)
        )
    except (TypeError, ValueError):
        return False


# Registry of named styles so `use_style("nature")` (etc.) resolves to a builder.
_STYLE_BUILDERS = {
    "nature": nature_style,
    "poster": poster_style,
    "presentation": presentation_style,
}


def _resolve_style(style) -> dict:
    """Resolve a style spec to an rcParams dict.

    Accepts a style builder callable (e.g. ``nature_style``), a name string
    (``"nature"``, ``"poster"``, ``"presentation"``, with or without a
    ``_style`` suffix), or an rcParams dict.
    """
    if callable(style):
        return dict(style())
    if isinstance(style, dict):
        return dict(style)
    if isinstance(style, str):
        key = style.lower().removesuffix("_style")
        if key in _STYLE_BUILDERS:
            return dict(_STYLE_BUILDERS[key]())
        raise ValueError(
            f"Unknown style {style!r}; known styles: {sorted(set(_STYLE_BUILDERS))}"
        )
    raise TypeError(f"style must be a callable, dict, or name string, got {type(style)!r}")


def use_style(style="nature", max_yticks: int = 4, max_xticks: int = 5) -> None:
    """Activate a figure style globally and set the tick caps.

    Call once at the top of a notebook (``use_style()`` for the default nature style,
    ``use_style("presentation")`` or ``use_style(nature_style)`` for others), so every
    figure created afterwards — including in other projects that import this — picks up
    the style. ``style`` accepts a style builder callable, a name string, or an rcParams
    dict; add new named styles by registering them in ``_STYLE_BUILDERS``.

    The tick caps only take effect under the presentation style: save_figure detects it
    and caps y-ticks (to ``max_yticks``) and numeric x-ticks (to ``max_xticks``).
    """
    global _PRESENTATION_MAX_YTICKS, _PRESENTATION_MAX_XTICKS
    _PRESENTATION_MAX_YTICKS = max_yticks
    _PRESENTATION_MAX_XTICKS = max_xticks
    mpl.rcParams.update(_resolve_style(style))


def use_presentation_style(max_yticks: int = 4, max_xticks: int = 5) -> None:
    """Deprecated alias for ``use_style("presentation", ...)``; kept for existing callers."""
    use_style("presentation", max_yticks=max_yticks, max_xticks=max_xticks)


def nice_x_locator(max_ticks: int | None = None):
    """A locator giving a few nicely-rounded *integer* x-ticks (5, 10, 15, ...
    rather than 3, 6, 9, or fractional values for small ranges).

    Numeric x-axes that would otherwise set one tick per session/day should use
    this so the *displayed* figure already matches the presentation save-time
    x-tick cap (which uses the same settings). ``max_ticks`` defaults to the
    presentation x-tick cap.
    """
    from matplotlib.ticker import MaxNLocator
    n = max_ticks if max_ticks is not None else _PRESENTATION_MAX_XTICKS
    return MaxNLocator(nbins=n or 5, steps=[1, 2, 2.5, 5, 10], integer=True)
