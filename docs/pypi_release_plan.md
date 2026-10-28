# PyPI release plan: backstamp, figure provenance as a standalone package

The goal is to move figure provenance out of `hypnose-helpers` into **`backstamp`**, a standalone
package that anyone can `pip install`. `hypnose-helpers` keeps everything that knows the Hypnose
layout, plus the figure styles, and becomes a consumer of `backstamp`. Measured on `83dfc95`.

**Scope:**
- In: recording how a figure was made inside the PDF, and reading it back.
- Out: figure styles (Q3) and the regression harness. The harness stays in
  `hypnose-behavior/src/hypnose_behavior/qc/` and is not packaged: most labs already test with
  pytest, and a golden master only helps once a pipeline's results are trusted.

**Design principle:** `backstamp` is designed to be as good as possible on its own.
`hypnose-helpers` adapts to it, not the other way round.
- backstamp's code, tests and docs never mention Hypnose or `hypnose-helpers`.
- The reader reads records written by backstamp only. A figure saved by `hypnose-helpers`
  before the move is read with a `hypnose-helpers` checkout from that time (`83dfc95`).

**Doc style:** bullets, one fact each, no prose around the point.

---

## Progress

| Phase | What | Estimate | Status |
| --- | --- | --- | --- |
| 0 | Settle the open decisions; create the GitHub repo and envs | ½ h (maintainer) | done |
| 1 | Extract unchanged, with shims in `hypnose-helpers`; publish `0.0.1` | 1 day | done |
| 2 | Make provenance general: any inputs, every parameter, `metadata()` | 2–3 days | done |
| 3 | Reader: `Record`, `backstamp show` with drag and drop, `backstamp ls` | 1–1½ days | done |
| 4 | Survival test: where the metadata survives | ½ day + ~1 h (maintainer) | done |
| 4b | Reader: figures inside decks and LaTeX PDFs, `--slide`, `--page` | ½–1 day | — |
| 4c | `backstamp strip`: a copy without the record, for publishing | ½ day | — |
| 5 | Lab rollout: move consumers to `backstamp`, remove shims | ½ day | — |
| 6 | Public release: docs, CI, PyPI | 1–2 days | — |

- After Phase 5, the package is usable inside the lab via `pip install backstamp` or
  `pip install git+https://…`.
- Phases 1–5 take about 6–8 days. Phase 6 brings the total to about 2 weeks.
- Use the package across the Hypnose repos for a few weeks between Phase 5 and Phase 6. The API
  is cheap to change until outside users depend on it.
- Items under "Optional, after the first release" are not part of any phase.

---

## Why

- The record is stored inside the figure file itself and can be read back without installing
  anything else. A PDF emailed on its own still carries its commit, its calling function, every
  parameter and its data scope.
- Lab feedback (talk, 2026-10): people would use it if it
  - takes subjects, dates, date ranges and subject → date-range mappings in any format;
  - saves every parameter (window sizes, normalisation factors…), not a sample;
  - works as the save call, or as metadata inside their own saver;
  - reads a figure back by drag and drop, showing commit, function and parameters.
- Prior art: Sumatra, recipy and DVC track provenance, but they need a database, a log or a
  workflow system. The new part is provenance stored in the file, with no other dependency.

## Inventory

| File | Lines | Fate |
| --- | ---: | --- |
| `provenance.py` | 303 | → `backstamp/provenance.py` (standard library only) |
| `viz/metadata.py` | 219 | → `backstamp/metadata.py` |
| `viz/save.py` | 241 | split: the save itself (`savefig` + metadata + Type 42 fonts) → `backstamp/save.py`; filename tags, presentation tick caps, `titles=`, `clear_legends`, `strip_legends`, `set_size` stay as the `hypnose-helpers` wrapper |
| `viz/styles.py`, `viz/legends.py`, `viz/series.py`, `viz/plotter.py` | 671 | stay (Q3) |
| `io/*`, `cli/*` | 1 300 | stay; untouched |
| `tests/test_provenance.py` | 371 | → `backstamp/tests/` |
| `tests/test_save.py` | 74 | stays: it tests the presentation tick caps |

- `provenance.py` and `metadata.py` import nothing from `io/`, `cli/` or `styles`.
- `save.py` depends on `styles` only through the presentation tick caps, which stay in the
  wrapper. `backstamp` therefore needs nothing from `hypnose-helpers`.

### Consumers outside this repo

| File | Uses |
| --- | --- |
| `hypnose-behavior/src/hypnose_behavior/io/save.py` | `save_figure` (the wrapper), `read_figure_metadata`, `provenance` |
| `hypnose-behavior/src/hypnose_behavior/io/save_results.py` | `provenance` (written into `manifest.json`) |
| `hypnose-behavior/src/hypnose_behavior/qc/figure_provenance.py` | `provenance`, module path `hypnose_helpers.provenance` |
| `hypnose-somnotate/src/hypnose_somnotate/io/save.py` | `save_figure` (the wrapper), `read_figure_metadata`, `provenance` |

- Style consumers (`qc/plot_regression.py`, `hypnose_somnotate/io/style.py`) and
  `hypnose-sleap` are unaffected.
- **Gate for every phase:** `hypnose-behavior`'s `qc/figure_provenance.py`, which checks that a
  saved figure's record names the plotter that drew it. Run it in the `hypnose-behavior` env
  pinned by `qc/fixtures/env.json`. `hypnose-helpers`' `tests/test_save.py` covers the wrapper.

---

## Decisions

### Q1: Name — decided

- **`backstamp`**, the maker's mark on the underside of porcelain.
- Free on PyPI and TestPyPI as of 2026-10-25.
- PyPI has no reservation. A name is claimed by the first upload. A pending Trusted Publisher
  "does **not** create a project or reserve a project's name until it is actually used to
  publish" (docs.pypi.org).
- So: publish a real, working `0.0.1` at the end of Phase 1, the extracted code marked as a
  pre-release. No empty placeholder: PyPI discourages those, and PEP 541 covers reclaiming them.

### Q2: Where the repo lives

- **Phases 1–5: `github.com/Joschua21/backstamp`.** Public, so lab members can `pip install`
  without a token. Default branch `main`, holding one commit: the `LICENSE`.
- **At release: transfer to `SainsburyWellcomeCentre/backstamp`.** The maintainer checks with
  the SWC org once the package is ready. GitHub redirects the old URL after a transfer, for `git`
  and `pip` too. The PyPI Trusted Publisher must then point at the new owner.
- **Licence: BSD-3-Clause**, as SWC's code projects use (`movement`, `brainglobe-atlasapi`,
  `brainreg`, `aeon_mecha`; checked 2026-10-25). The `LICENSE` names the maintainer as copyright
  holder.
- Open for SWC: who holds the copyright (the maintainer or UCL/SWC). That decides the copyright
  line, and who may relicense later versions. Versions already published keep their licence.
- Local checkout: `~/repos/harris_lab/backstamp`, outside `hypnose/`, because the package knows
  nothing about Hypnose.

### Q3: Styles stay out — decided

- `backstamp` is provenance only. Styles and the slide helpers (`legends`, `series`, `plotter`)
  stay in `hypnose-helpers`.
- They solve a different problem, and people who want one don't need the other.
- `hypnose-helpers`' `save_figure` applies the presentation tick caps, then calls
  `backstamp.save`.

### Q4: What the record stores about the code

- **Add:** `repo` (`git remote get-url origin`, with any credentials removed), `branch`,
  `python`, `backstamp` version, and `diff_sha` (hash of `git diff HEAD`) when dirty.
- **Add:** a `"schema": 1` field so later readers can tell record versions apart.
- **Keep:** `created_at`, `commit`, `version`, `function`, `module`, `file`, `lineno`, `chain`.
- **Do not store** the absolute `path`. It leaks usernames and directory layout into figures
  that get sent out. `file` is enough.

### Q5: Inputs and parameters — decided

- **`inputs=`** records what data went in. Keys are free-form. Values are stored as given, in any
  format: `40`, `"mouseA"`, `"20261002"`, `"03oct2026"`.
- Accepted forms:
  - a dict of values or lists: `{"subject": [40, "mouseA"], "date": ["20261002", "03oct2026"]}`
  - date ranges, as a `(start, end)` pair or as text: `("20251124", "20251130")`,
    `"20251124-20251130"`. A tuple of two is stored as the text `"start/end"`, since JSON
    has no tuple; a list of two stays two values.
  - mappings, e.g. subject → date range: `{"subject": {40: ("20251124", "20251130"), 41: …}}`.
    JSON turns keys into text, so `40` is read back as `"40"`.
  - a list of parameter names: `inputs=["subjids", "dates"]` copies those parameters in full from
    the call, keyed by the parameter names. A name the function doesn't have gives a warning.
- **One way to declare data.** `save` has no separate `subjids=` or `dates=` arguments; subjects
  and dates go through `inputs=` like any other data. The `hypnose-helpers` wrapper passes
  `inputs={"subject": subjids, "date": dates}`.
- **Recommended keys:** `subject`, `date`, `session`. Any key works, but these three get a short
  form in the Title summary and their own `ls` filters (`--subject`, `--date`, `--session`), so
  they mean the same thing in every lab.
  - A mapping under a recommended key maps each of its values to the next level: under
    `subject`, each subject to its dates (a value, a list or a range), or to a dict of further
    keys (`{"session": [1, 2]}`).
  - The list form keeps parameter names as keys. Pass a dict to use the recommended keys.
- **Values, not names.** Inputs and parameters are recorded by value. `plot(subjids=ab_data)`
  stores the contents of `ab_data`, never the name. Checked on 2026-10-25 with the current frame
  capture.
- **`params`** stores every parameter of the calling function, in full:
  - numbers, strings, booleans, `None`, paths, and lists, tuples, sets and dicts of these, at
    any length and depth. numpy scalars become plain numbers.
  - data objects are summarised as their type and shape: `<DataFrame 50x2>`, `<ndarray (3, 4)
    float64>`. So are matplotlib objects and any other object.
  - the limits of 15 parameters, 10 items per list and 80 characters per string go.

### Q6: Record size — decided

- Cap (`MAX_BLOB`): **30,000 characters.**
- This keeps a margin below 32,767 bytes, the string length in the PDF specification's
  implementation limits. Phase 4: `pypdf` and Preview show a 29,996-character record in
  full. Acrobat's Document Properties shows only its first ~2,000 characters, but saving in
  Acrobat keeps all of it.
- Over the cap: the save still succeeds. A `UserWarning` names the figure and the record size, and
  says the data summaries were dropped, so the caller can trim inputs or parameters.
- Still over after that: parameters are cut, largest first, and the warning lists which.
  The code fields (Q4) are never cut.
- A record that large points to a figure that needs a different kind of record.

### Q7: Filename convention — decided

- `{save_name}_sub-XXX_date-…pdf` is the Hypnose convention. It should not be the package's
  default.
- **Decided:**
  - The package defaults to `{name}.pdf`.
  - `filename=` accepts a callable `(name, inputs) -> str`.
  - The `hypnose-helpers` wrapper passes its own, so Hypnose file names don't change.
- This also removes the `int(s):03d` crash on non-numeric IDs (`save.py:165`) from the package.

### Q8: Python floor — decided

- **Decided: `backstamp` supports `>=3.9`**, for users still on 3.9. It costs only the
  `packages_distributions` fallback in `package_version`, which already exists.
- No Hypnose repo needs 3.9 (2026-10-28): `hypnose-somnotate` runs on 3.12.
- Python 3.9 has been end-of-life since 2025-10. Raise the floor once keeping it costs real
  work, e.g. a dependency drops 3.9 or the code needs 3.10 syntax.

### Q9: Public names — decided

- **Decided:** `backstamp.save`, `backstamp.metadata`, `backstamp.read`; command line
  `backstamp show`, `backstamp ls`.
- `save` is the name the talk used; `read` and `show` are the usual Python and CLI names.

### Q10: Paths and private data — decided

- **Paths are reduced by default.** `paths=` on `save` and `metadata`:

  | `paths=` | `/Users/me/data/sub-040/trials.parquet` is stored as |
  | --- | --- |
  | `"name"` (default) | `trials.parquet` |
  | `"full"` | the full path |
  | `"hide"` | `<path>` |

- A path is a `Path` object, or a string holding an absolute path (`/…`, `~/…`, `C:\…`).
  Relative strings such as `"figures/"` are kept as they are: a slash alone can't tell a path
  from a label.
- It applies to `params` and `inputs` alike, so `fig_dir` and data paths are both covered.
- **`redact=["token", …]`** drops the named parameters from the record. Each is listed as
  `<redacted>`, so the reader can see that it existed.
- **`backstamp.configure(paths=…, redact=…)`** sets both once per process, so a project doesn't
  repeat them in every call. `paths=` on a call overrides it; `redact=` on a call adds to it,
  so a configured name is always redacted.

---

## Target API

```python
import backstamp

def plot_accuracy(subjids, dates, window=50, norm=1.0):
    fig, ax = plt.subplots()                     # pyplot, seaborn or pandas
    ...
    backstamp.save(fig, "accuracy", fig_dir="figures/", inputs={"subject": subjids, "date": dates})

# inputs in any form
inputs=["subjids", "dates"]                      # copy these parameters in full
inputs={"subject": [40, "mouseA"], "date": ["20261002", "03oct2026"]}
inputs={"subject": {40: ("20251124", "20251130"), 41: ("20260101", "20260115")}}

# paths and private data (Q10)
backstamp.configure(paths="name", redact=["token"])   # once per project; "name" is the default
backstamp.save(fig, "accuracy", paths="full")          # override per call

# or keep your own saver
fig.savefig("figures/accuracy.pdf", metadata=backstamp.metadata(inputs=["subjids", "dates"]))

rec = backstamp.read(path)                       # -> Record
rec.status                                       # "ok" | "unstamped" | "unreadable" | "missing"
rec.commit, rec.repo, rec.call, rec.inputs
rec.reproduce()                                  # clone, checkout and call, as text
rec.to_dict()
```

```text
$ backstamp show
Drop a figure here or paste its path, then Enter (Ctrl-D to quit):

$ backstamp show figures/accuracy.pdf
accuracy  subject=40,45  date=20251124–20260203
made by   hypnose_behavior.visualization.accuracy:plot_accuracy (accuracy.py:212)
commit    a1b2c3d-dirty  on main  github.com/SainsburyWellcomeCentre/hypnose-behavior
params    subjids=[40, 45]  dates=[…]  window=50  norm=1.0
created   2026-10-05T14:02:11+01:00  python 3.12.13  backstamp 0.2.0

$ backstamp show --json figures/accuracy.pdf
$ backstamp show --reproduce figures/accuracy.pdf

$ backstamp ls figures/ --dirty --subject 40
name          function        commit         inputs                  created
accuracy      plot_accuracy   a1b2c3d-dirty  subject=40,45 date=2…   2026-10-05
...
```

---

## Phases

Each phase is one chat. Read this plan fresh at the start, and tick the Progress table at the end.
Each phase brings `backstamp`'s README up to what it adds, written for an end user: the problem
first, current behaviour only.

### Phase 0: Decisions (maintainer)

- All decisions are settled except two for SWC (Q2): the copyright holder and the transfer,
  both at release.
- Repo: `github.com/Joschua21/backstamp`, public, with the BSD-3-Clause `LICENSE` (Q2).
- PyPI account: `jgeuter`. Two-factor authentication is on (mandatory for uploads).
- Envs:
  - `backstamp` (Python 3.12): development, plus `matplotlib`, `pytest`, `build`, `twine`.
    3.12 matches `hypnose-behavior` and `hypnose-somnotate`, and gets the matplotlib users have:
    matplotlib 3.10+ needs Python 3.10+.
  - `backstamp-py39` (Python 3.9): runs the tests on the floor version (Q8) until Phase 6's
    CI does it.
  - `pypdf` is a dependency (Phase 1), so the editable install brings it into each env.

### Phase 1: Extract unchanged

- Clone `github.com/Joschua21/backstamp` to `~/repos/harris_lab/backstamp` and build the
  package there: a `src/` layout and `pyproject.toml`. Dependencies: `matplotlib` and `pypdf`.
  A PDF re-saved by another tool may not keep the info dictionary as the uncompressed literal
  string the stdlib parser relies on, and Phases 3–4 read exactly those files.
- The maintainer installs it in editable mode (`pip install -e`) into `backstamp`,
  `backstamp-py39`, and the envs that use `hypnose-helpers`: `hypnose`, `hypnose-behavior`,
  `hypnose-somnotate`.
- Move `provenance.py` and `metadata.py` **unchanged** apart from import paths. `_SKIP_MODULES`
  becomes `backstamp.*`.
- Split `save.py` as in the Inventory, moving code only. The `hypnose-helpers` wrapper keeps
  `save_figure`'s current signature and calls `backstamp.save`.
- `backstamp.save` takes `filename=` as a string; the wrapper passes the Hypnose file name.
- The wrapper passes its own module name in `skip_modules`, or every record names the wrapper
  instead of the plotting function.
- Turn `hypnose_helpers/provenance.py` and `hypnose_helpers/viz/metadata.py` into shims that
  replace themselves in `sys.modules` with the `backstamp` module. Every current import keeps
  working, private names included, and so does setting `MAX_CHAIN` through the old name (the
  gate's `--break-chain` probe). A star re-export would set a copy.
- `hypnose-helpers` gains the dependency `backstamp @ git+https://…@v0.0.1`.
- Move `test_provenance.py`; it passes in both `backstamp` and `backstamp-py39`. All
  `hypnose-helpers` tests pass.
- **Check:** `qc/figure_provenance.py` stays GREEN.
- Publish `0.0.1` to PyPI. This claims the name (Q1).
  - `python -m build`, then `twine upload dist/*`, as `jgeuter`.
  - The first upload needs an account-wide API token: a project-scoped one can only be made once
    the project exists. Delete it after the upload.
  - Later uploads use a project-scoped token until Phase 6 sets up the Trusted Publisher.

### Phase 2: Make provenance general

- Add the Q4 fields. Drop `path`.
- Add `inputs=` in every Q5 form. `Title` is built from `inputs`, mappings included, with the
  short form for the recommended keys, and kept to one line.
- Store `params` in full (Q5).
- Add `paths=`, `redact=` and `backstamp.configure()` (Q10).
- Add the record-size cap and its warnings (Q6).
- Add `backstamp.metadata(...)`: the same record as a dict for `fig.savefig(..., metadata=…)`
  or `PdfPages(..., metadata=…)`. It must be called inside the plotting function, like `save`.
- `save` and `metadata` accept a figure, an axes object (what `pandas.plot` returns) or a seaborn
  grid (what `relplot`/`catplot` return). Anything else raises a `TypeError` naming what to pass.
- `filename=` also takes a callable (Q7).
- A `backstamp.metadata()` function shadows the `backstamp/metadata.py` module, as
  `backstamp.save` already shadows `backstamp/save.py` (`import backstamp.save as m` gives the
  function). Rename the modules (e.g. `_pdf.py`, `_save.py`) and update `_SKIP_MODULES` and
  the shims to match.
- `Creator` becomes `backstamp <version>` when the caller's package version is unknown, in place
  of `"hypnose"`.
- **Backward compatibility:** the reader still parses every existing Hypnose PDF (no `schema`
  key, `subjids`/`dates` at top level). Add a fixture PDF saved by `83dfc95` to the tests.
- **Tests:**
  - one per Q5 form: numeric and text IDs, text dates, ranges, mappings, named parameters, an
    unknown name
  - a variable passed in (`subjids=ab_data`) recorded by its contents
  - a parameter set of long lists and nested dicts stored in full
  - a record over 30,000 characters giving the warning
  - each `paths=` setting on `Path` objects, absolute strings and relative strings; `redact=`;
    `configure()` overridden by a per-call argument
- **Check:** `qc/figure_provenance.py`. The new fields are an intended output change, so update
  it in the same commit and confirm only those fields moved.

### Phase 3: Reader

The current `read_figure_metadata` was built to check that saving worked, not for someone
holding an unknown figure:

- It returns `{}` for a missing file, an unreadable PDF and an unstamped PDF alike.
- It returns a flat dict with `_title` and `_creator` mixed in with the record fields.
- It needs Python; there is no command-line entry point.
- It reads one file at a time, so "which figures in this folder…" questions need a script.

Build:

- `backstamp.read(path) -> Record`, never raising:
  - `.status`: `ok`, `unstamped`, `unreadable` or `missing`.
  - Fields: `.commit`, `.dirty`, `.repo`, `.branch`, `.call` (function, module, file, line,
    chain, params), `.inputs`, `.created`, `.versions`, `.title`.
  - `.reproduce()`: `git clone`, `git checkout <commit>` and the recorded call with every
    parameter, as text. Warns when the commit is `-dirty`, since the checked-out code is not what
    ran.
  - `.to_dict()`, a readable `__str__` for the terminal, and `_repr_html_` for Jupyter.
- `Record` reads records written by backstamp (design principle). Any JSON object in
  `Subject` is a record, `schema` or not, since `save(provenance=...)` embeds a dict as given.
  Any other `Subject` is another program's: `unstamped`.
- `backstamp show <files, folders or globs>`: one readable block per figure. `--json` and
  `--reproduce` flags.
- **Drag and drop:** `backstamp show` with no path waits for one. Each figure dropped into the
  terminal, or path pasted, is read on Enter; Ctrl-D or an empty line quits.
  - Clean up what terminals paste: backslash-escaped spaces (Terminal, iTerm), single quotes
    (VS Code), double quotes (Windows Terminal), a trailing space.
  - A dropped path also works as an argument: `backstamp show ` + drop + Enter.
- `backstamp ls <folder>`: one row per figure, recursive. Filters: `--dirty`,
  `--function NAME`, `--input KEY=VALUE`, `--subject`, `--date`, `--session`, `--commit SHA`,
  `--unstamped`.
  - `--input` matches values as text, including inside mappings.
  - Whole numbers match by value: `--subject 40` finds `"040"`. All other text matches exactly.
  - A date inside a stored range matches only for `YYYYMMDD` and ISO dates. Other formats match
    exact text only.
- `backstamp` drops `read_figure_metadata`. `hypnose-helpers`' `viz/metadata.py` becomes a
  plain module defining it as `read(path).to_dict()`, until Phase 5.
- Read with `pypdf` only; drop the stdlib fallback parser (`_read_info_stdlib`, `_unescape`).
- Silence pypdf's logger while reading. A junk file logs `invalid pdf header` and `EOF marker
  not found` to stderr; it should give `unreadable`, quietly.
- `[project.scripts]` adds the `backstamp` command once each env re-runs `pip install -e`;
  `python -m backstamp` works without it.
- **Tests:** all four statuses, records saved by `save` and by `save(provenance=...)`, and
  pasted paths with spaces, quotes and non-ASCII names. The Phase 2 fixture PDF is removed
  with the unversioned reader.

### Phase 4: Survival test

Measure where the metadata survives before deciding whether anything needs fixing. The
expectation, unverified: it survives byte-for-byte copies and is lost whenever something
redraws the figure.

- Make a test set with `backstamp.save`:
  - a small figure, a figure with a near-30,000-character record, and a figure with non-ASCII
    text in its title and inputs.
- Check the 30,000-character record reads back in Preview, Acrobat and `pypdf` (Q6).
- Add `scripts/survival_check.py <original> <returned>…`. For each returned file it reports:
  - byte-identical or not
  - record intact, partly kept (which fields), or lost
  - for `.pptx` and `.key` files (zip containers): whether the original PDF is stored inside,
    and whether its record is intact.
- The maintainer runs the GUI rows and drops the returned files into one folder per route,
  `~/backstamp-survival/returned/<route>/`, next to the test set in `originals/`. The script
  reads the route from the folder and fills the table.
- Q6: `pypdf` and Preview show the 29,996-character record of `large.pdf` in full. Acrobat's
  Document Properties shows the first 1,999 characters only; Acrobat's save keeps it whole.
- Found on the way: a tree dirty from untracked files alone stored `diff_sha` of an empty
  diff, the same for every such figure. `diff_sha` is now left out then. Gate GREEN.
- Results, measured 2026-10-28 on macOS 27.0.1:
  - Each row held for all three figures: record size and non-ASCII text made no difference.
  - "Intact" means `backstamp show` reads the full record, `Title` and `Creator` included.
  - In a deck, the record is intact inside the stored PDF, but `backstamp show` does not
    look inside `.key` or `.pptx` files until Phase 4b.
  - Acrobat and Illustrator also copy `Subject` into XMP `dc:description`, which backstamp
    does not read.

| Route | Result |
| --- | --- |
| Finder copy / move | byte-identical, record intact (also `cp`, `mv`) |
| Dropbox / OneDrive / Google Drive, upload then download | byte-identical, record intact. Dropbox and OneDrive download several files as a zip |
| git commit then clone | byte-identical, record intact |
| Slack upload, recipient downloads | byte-identical, record intact |
| Email attachment (Outlook), recipient saves | byte-identical, record intact |
| Open in Preview, close without saving | byte-identical, record intact |
| Annotate in Preview, save | rewritten, record intact |
| Open in Acrobat, save | rewritten, record intact |
| Open in Illustrator / Inkscape, save as PDF | Illustrator 30.8: `Subject` kept, so the record reads in full; `Title` becomes the file name, `Creator` Illustrator. Inkscape 1.4.3 (internal import): lost |
| Drag into Keynote, save; record of the PDF stored inside the `.key` | stored byte-identical under `Data/`, record intact |
| Drag into Mac PowerPoint, save; record of the PDF stored inside the `.pptx` | stored byte-identical, wrapped in an EMF under `ppt/media/`, record intact |
| Copy-paste out of Keynote / PowerPoint into another deck | stored byte-identical in the new deck, record intact (both) |
| Copy-paste out of Keynote / PowerPoint into Preview ("New from Clipboard") | PowerPoint: rewritten, record intact. Keynote: lost |
| Export the deck to PDF | lost (Keynote and PowerPoint) |
| Print to PDF | lost (from Preview) |
| Overleaf: `\includegraphics`, compile, download | lost from the info dictionary; pdfTeX keeps each figure's, record included, as `/PTEX.InfoDict` on the included page |

- The filled table goes into the README in Phase 6 as "What the metadata survives".
- **Fixes are out of scope for this phase.** They are discussed after the test, with the
  results in hand. Options raised on 2026-10-05 (a visible ID, a save log, image matching,
  invisible text in the PDF) were not taken up.

### Phase 4b: Figures inside decks and LaTeX PDFs

Phase 4 found the record intact inside Keynote and PowerPoint decks, and inside PDFs
compiled with pdfLaTeX, where `read` does not look. Read it there.

- `backstamp show deck.key` lists every figure's record, by slide; `backstamp show paper.pdf`
  by page. `--slide 5` and `--page 3` keep the figures on that slide or page; both repeat.
- `backstamp.read_all(path) -> list[Record]`: one `Record` per figure; a plain PDF gives one.
  - `Record` gains `where`: the slide or page, and the file the figure was stored or
    included as, e.g. `{"slide": 5, "file": "small-9092.pdf"}`.
  - `read` keeps one `Record` per file: `unreadable` for a deck, `unstamped` for a LaTeX
    PDF whose own info dictionary holds no record.
  - `ls` lists the figures inside decks and LaTeX PDFs as rows of their own
    (`deck.key slide 5`); its filters apply to them.
  - A figure on several slides is one stored file: listed on each.
- Where the records are, checked 2026-10-28 on the Phase 4 files:
  - `.key` (zip or package folder): the PDFs under `Data/`, named `<name>-<data ID>.pdf`.
    `Index/*.iwa` is snappy-compressed protobuf, readable without Apple's schema. The show
    (message type 2) lists the slide nodes (type 4) in slide order; each node points to its
    slide; the `.iwa` file holding the slide object lists the data IDs of its images. The
    `.iwa` file names do not follow the slide IDs. Snappy needs a small pure-Python decoder,
    not a dependency.
  - `.pptx`: the PDFs under `ppt/media/`, bare or wrapped in an EMF, cut out from `%PDF-` to
    the last `%%EOF`. The slide is the `ppt/slides/slideN.xml` whose `.rels` names the media
    file; the slide order is `ppt/presentation.xml`'s slide list, not `N`.
  - pdfLaTeX: `/PTEX.InfoDict` on each page's form XObjects, with `/PTEX.FileName`.
- Checked on 5-slide Keynote and Mac PowerPoint decks (one figure each on slides 1–3, all
  three on 4 and 5), and on copies with slide 3 moved to first: every figure on its slide.
- Unchecked: skipped and nested Keynote slides, Windows PowerPoint, LuaLaTeX and XeLaTeX.
- A deck whose slide order cannot be read lists its figures without slide numbers, and
  `show` says so.
- Fixtures: those four decks, in `~/backstamp-survival/returned/` as `keynote-slides`,
  `keynote-reordered`, `powerpoint-slides` and `powerpoint-reordered`. Build the LaTeX case
  with pypdf.
- **Tests:** each source, `--slide` and `--page`, a figure on two slides, a deck whose index
  cannot be read, the `ls` rows. On Python 3.9 too (Q8).

### Phase 4c: Strip the record before publishing

The record is for the people who made the figure. A figure sent to a journal, or a paper
posted as a preprint, need not carry it (see Risks).

- `backstamp strip <files, folders or globs>` writes a copy without the record: `fig.pdf` →
  `fig_stripped.pdf`, next to it. The original is never changed. With no path it waits for
  one, as `show` does, so a figure can be dropped into the terminal.
- `backstamp.strip(path, out=None) -> Path`: the same in Python.
- It removes what `read_all` (Phase 4b) finds, and nothing else:
  - the record in `Subject`, with backstamp's `Title` and `Creator`
  - each `/PTEX.InfoDict` holding a record, in a PDF compiled with pdfLaTeX
  - XMP `dc:description` holding a record, where Acrobat and Illustrator copy it (Phase 4)
- The rest of the PDF stays: a paper's own `Title`, its pages, links and outline. pypdf
  writes the copy, cloning the document.
- It then checks the copy: `read_all` finds nothing, and no record text is left anywhere in
  the file, compressed streams included (the search in `scripts/survival_check.py`). Text
  left over fails the command, naming where it is.
- A PDF without a record gets no copy; `strip` says so.
- Decks are not stripped: PowerPoint's EMF wrapper would need rewriting, and Keynote's index
  may hold checksums of its files. `strip` names the figures in a deck that hold records, and
  says to strip them before adding them, or to share the deck as an exported PDF, which
  holds none (Phase 4).
- Name: `strip`, as in ImageMagick's `-strip`. `unstamp`, matching the `unstamped` status,
  is the alternative.
- **Tests:** a saved figure, a pdfLaTeX-style PDF built with pypdf, a record in XMP, a PDF
  without a record, a deck, the check finding leftover text, the original unchanged.

### Phase 5: Lab rollout

- Move the consumers listed in the Inventory to `backstamp` imports.
- `hypnose-behavior` and `hypnose-somnotate` keep their own `io/save.py` wrappers. Only the
  import lines change.
- backstamp has no `read_figure_metadata`. Its re-exports become `backstamp.read`, which
  returns a `Record` (`.to_dict()` for a dict).
- The `hypnose-somnotate` env has neither `hypnose-helpers` nor `backstamp` installed. Install
  both before its imports change.
- Remove the shims from `hypnose-helpers`. Bump it to `0.2.0`.
- Tag and publish `backstamp 0.1.0`. Consumers pin to it.
- Add a "Figure provenance" section to the lab README or wiki: install, `backstamp.save`,
  `inputs=`, `backstamp show`.

### Phase 6: Public release

- Complete the README for an outside reader:
  - a 10-line quick start
  - the forms `inputs=` takes
  - what is recorded and what is not (see Risks)
  - what the metadata survives (the Phase 4 table)
  - that a paper compiled with pdfLaTeX carries every figure's record (see Risks)
  - a screenshot of `backstamp show`
- Set up GitHub Actions: tests on Python 3.9–3.13 on Linux, macOS and Windows. Git-dependent
  tests run against a temporary repo created in the test.
- Publish through a Trusted Publisher (no API token stored), TestPyPI first.
- Write a `CHANGELOG.md` and tag `v0.2.0` or later; the first public version follows the lab
  trial.
- Transfer the repo to SWC if Q2 says so.

---

## Optional, after the first release

- **Finder right-click "Show provenance":** a macOS Quick Action, installed per user in
  `~/Library/Services`, that runs `backstamp show` on the selected file and shows the result.
  - It needs the full path to the `backstamp` command in its conda env, since Finder doesn't see
    the shell's `PATH`.
  - macOS only: Windows would need its own context-menu entry, Linux one per file manager.
  - Could ship later as `backstamp install-finder-action`. Terminal drag and drop (Phase 3)
    covers the need for now.
- **Spotlight search:** put the function and commit into the PDF `Keywords` field, which
  Spotlight indexes. Untested.
- **PNG and SVG metadata:** matplotlib takes arbitrary text keys for both, so reading and writing
  work the same as for PDF.
- **Survival fixes**, if the Phase 4 results call for any.

---

## Risks

- **Rebuilding a figure depends on how the code is written.** Data objects are stored as their
  shape, not their values. The record identifies the data only when the plotting function
  receives IDs and loads the data itself. State this in the README as the convention to follow.
- **Frame-walking is fragile.** `function` is the nearest frame that isn't skipped. Wrappers
  must pass `skip_modules` or an explicit `provenance=`. This already caused trouble once, and
  `chain` exists because of it.
- **Stale `dist-info`.** If an old distribution is still installed next to the new one,
  `packages_distributions()` lists both and `version` can be wrong. This is already recorded in
  `hypnose-behavior` `DECISIONS.md` §19. The `backstamp` README should cover it too.
- **Values are taken when `save` runs, not when the function was called.** A parameter
  reassigned inside the function (`window = window * 2`, `dates = dates[1:]`) is recorded with
  its new value. Checked on 2026-10-25: `window=50` was recorded as `100`. The README states the
  rule: don't reassign parameters before saving. A decorator that captures at call time is
  possible if this bites.
- **Private data in the record.** With every parameter stored in full, anything passed to a
  plotting function ends up in the PDF. Paths are reduced to their file name by default and
  named parameters can be redacted (Q10). Names and other text in ordinary strings are still
  stored; the README says so.
- **The record travels into papers.** pdfLaTeX copies each included figure's info dictionary
  into the compiled PDF as `/PTEX.InfoDict` (Phase 4), so a paper or preprint compiled that
  way carries every figure's record: repo, parameters, inputs. The README says so, with two
  ways out: `\pdfsuppressptexinfo=-1` in the preamble (unverified), or `backstamp strip` on
  the compiled PDF (Phase 4c).
