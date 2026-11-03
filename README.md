# hypnose-helpers

Modality-agnostic utilities shared across the Hypnose repos. Import package:
`hypnose_helpers`.

| repo | package | role |
|---|---|---|
| hypnose-behavior-analysis | `hypnose_behavior` | behavioural analysis |
| hypnose-somnotate | `hypnose_somnotate` | EEG sleep scoring |
| hypnose-eeg-analysis | `hypnose_eeg` | EEG analysis (coming) |
| **hypnose-helpers** | `hypnose_helpers` | **this repo** — shared, modality-agnostic |

## What belongs here

One test decides it:

> **Does it know what the data *is*, or only where it lives and what format it's in?**
>
> Knows the data (harp streams, odors, trials, EDF channels, sleep stages) → **modality repo**
> Knows only layout/format (`sub-XXX/` dirs, parquet-vs-CSV, JSON, figure styles) → **here**

Equivalently: *would this need to change if you added a third modality?* If yes, it is not
a helper.

**Hard constraint: this package imports nothing from the rest of the family.** The
dependency runs strictly one way. Break that and you get an import cycle the first time
someone is in a hurry.

## Layout

```
src/hypnose_helpers/
├── io/
│   ├── paths.py        data-location profiles (get_rawdata_root, set_active, …)
│   ├── layout.py       sub-XXX_id-*/ses-YY_date-YYYYMMDD walking; find_sessions, session_index
│   ├── selectors.py    forgiving subject/date parsing (66 / "066" / "sub-066" / "66,67")
│   ├── serialize.py    generic JSON / DataFrame normalisation
│   └── tables.py       parquet-vs-CSV dispatch
├── viz/
│   ├── styles.py       nature / poster / presentation styles, use_style, ensure_style
│   ├── save.py         save_figure(…, fig_dir=…), strip_legends, set_size; saves through backstamp
│   ├── plotter.py      the plotter convention: finish_figure, legend_figure, show_suffix, tie
│   ├── legends.py      legends set apart from their figures, for slides
│   └── series.py       a figure's series shown a few at a time, for build-up slides
└── cli/
    ├── set_data_location.py
    └── selector_args.py  add_selector_args: shared -s/--sub/--subjids, -d/--date(s), --ses… flags
```

Two design rules the `viz` modules exist to enforce:

1. **Never mutate `rcParams` at import time.** Two repos writing the same keys at module
   scope means whoever imports last silently wins.
2. **`save_figure` takes `fig_dir` as an argument.** A library owned by no dataset must not
   hardcode one dataset's layout and then need a resolver hook to escape it.

## Plotter convention

Every plotting function in the family takes `legend=None` and `show=None` and finishes
each figure with `viz.plotter`, so a figure can be reshaped for slides without the function
knowing how:

- `legend` -- True keeps the legend in the figure; False sets it apart in one legend-only
  figure, shown and never saved; None follows `use_style`, which sets legends apart under
  the presentation style (`use_style(..., separate_legends=...)` overrides).
- `show` -- the series to draw, by legend number or label in any order (`[1]`, `[1, 2]`,
  `[3, 1]`), to build a slide up step by step; `0` draws none (the first frame), None draws
  them all.

```python
entries += finish_figure(fig, legend, show)        # each figure, before saving
save_figure(fig, f"name{show_suffix(show)}", ...)  # each step saves apart
legend_figure(entries)                             # once, after the figures
```

Draw every series with a label, in a fixed order: legend order is the numbering. An
artist that belongs to a series without its label (a band, error bars) is tied to it with
`tie(artist, label)`. The full pattern is in `viz/plotter.py`. Any other key a figure
sets apart with its legend (a score table, say) is drawn in its own figure and passed to
`show_apart(fig)`, which shows it like the legend figure and closes it, never saved.

## Figure provenance

Every figure saved through `save_figure` carries a record of how it was made, inside the
PDF: the commit, the plotting function, every parameter, and the subjects and dates.
[backstamp](https://github.com/Joschua21/backstamp) writes and reads it.

- **Install:** it comes with this package. Outside the Hypnose repos: `pip install backstamp`.
- **Save:** `save_figure` here and in each repo's `io/save.py` already writes the record.
  For a figure saved any other way, call `backstamp.save` inside the plotting function:

  ```python
  import backstamp

  def plot_latency(subjids, dates, window=50):
      fig, ax = plt.subplots()
      ...
      backstamp.save(fig, "latency", fig_dir=fig_dir, inputs={"subject": subjids, "date": dates})
  ```

  To keep your own `savefig`, pass `metadata=backstamp.metadata(inputs=...)`, also from
  inside the plotting function.
- **`inputs=`** records the data that went in, in any format:
  - values or lists: `{"subject": [66, "sub-067"], "date": ["20261002", "03oct2026"]}`
  - a date range as a pair: `{"date": ("20251124", "20251130")}`
  - each subject's own dates: `{"subject": {66: ("20251124", "20251130"), 67: "20260101"}}`
  - parameter names, copied from the call: `inputs=["subjids", "dates"]`

  Use the keys `subject`, `date` and `session`: `backstamp ls` filters on them.
- **Read:** `backstamp show figure.pdf` prints the record; `backstamp show` alone waits for
  figures dragged into the terminal. It also reads the figures inside Keynote and
  PowerPoint decks, by slide, and pdfLaTeX papers, by page.
  - `backstamp ls figures/ --subject 66` lists a folder's figures.
  - `backstamp show --reproduce figure.pdf` prints the commands that make it again.
  - In Python: `backstamp.read(path)`.
- **Strip before publishing:** `backstamp strip paper.pdf` writes `paper_stripped.pdf`
  without the records, for a journal or a preprint; the original is unchanged. A paper
  compiled with pdfLaTeX carries every included figure's record: repo, parameters, inputs.

Two rules:

- A function that wraps `save_figure` passes
  `provenance=backstamp.provenance.provenance(skip_modules=(__name__,))`, as each repo's
  `io/save.py` does, or every record names the wrapper instead of the plotter.
- Don't reassign a parameter before saving: values are recorded when the figure is saved.

What the record holds, and which routes it survives: [backstamp's
README](https://github.com/Joschua21/backstamp#readme).

## Install

```
pip install -e /path/to/hypnose-helpers
```

Dependencies are deliberately minimal (`numpy`, `pandas`, `matplotlib`, `pyyaml`,
`backstamp` from PyPI) and support Python ≥3.9. 

Optional extras: `test`.

## Status

Skeleton. Populated by restructure_2 Phase 2a — see
`hypnose-behavior-analysis/docs/restructure_2_plan.md` for the extraction inventory.
