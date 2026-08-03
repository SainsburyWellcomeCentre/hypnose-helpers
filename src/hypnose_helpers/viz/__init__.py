"""Figure styling and saving, owned by no dataset.

Planned modules (populated during restructure_2 Phase 2a):

    styles.py  nature_style, poster_style, presentation_style, use_style, ensure_style
    save.py    save_figure(fig, name, *, fig_dir, ...), strip_legends, set_size,
               nice_x_locator

Two rules this package exists to enforce:

1. **Never mutate rcParams at import.** Two repos doing that at module scope means
   whoever imports last wins. Export the styles and an explicit ``use_style()`` /
   ``ensure_style()``, applied at figure-creation time.
2. **``save_figure`` takes ``fig_dir`` as a plain argument.** A library owned by no
   dataset must not hardcode one dataset's layout and then need a resolver hook to
   escape it -- each consumer resolves its own destination and passes it in.
"""
