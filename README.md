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
│   └── save.py         save_figure(…, fig_dir=…), strip_legends, set_size
├── cli/
│   └── set_data_location.py
└── provenance.py       git commit (+dirty) and package version, for figure metadata
                        and run manifests alike
```

Two design rules the `viz` modules exist to enforce:

1. **Never mutate `rcParams` at import time.** Two repos writing the same keys at module
   scope means whoever imports last silently wins.
2. **`save_figure` takes `fig_dir` as an argument.** A library owned by no dataset must not
   hardcode one dataset's layout and then need a resolver hook to escape it.

## Install

```
pip install -e /path/to/hypnose-helpers
```

Dependencies are deliberately minimal (`numpy`, `pandas`, `matplotlib`, `pyyaml`) and
support Python ≥3.9, so every repo in the family can install it — including those pinned
to 3.9 by pomegranate/somnotate. 

Optional extras: `pdf` (read figure provenance back out of a saved PDF), `test`.

## Status

Skeleton. Populated by restructure_2 Phase 2a — see
`hypnose-behavior-analysis/docs/restructure_2_plan.md` for the extraction inventory.
