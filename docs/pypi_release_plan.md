# PyPI release plan: figure provenance and styles as a standalone package

The goal is to move figure provenance and figure styles out of `hypnose-helpers` into a standalone
package that anyone can `pip install`. `hypnose-helpers` keeps everything that knows the Hypnose
layout and becomes a consumer of the new package. Measured on `83dfc95`.

The preliminary name used throughout is **`backstamp`** (see Q1).

**Doc style:** bullets, one fact each, no prose around the point.

---

## Progress

| Phase | What | Estimate | Status |
| --- | --- | --- | --- |
| 0 | Settle Q1–Q6 | ½ h (Joschua) | open |
| 1 | Extract unchanged, with shims in `hypnose-helpers` | 1 day | — |
| 2 | Make provenance general | 1–1½ days | — |
| 3 | New reader: `Record`, `backstamp show`, `backstamp ls` | 1 day | — |
| 4 | Survival test: where the metadata survives | ½ day + ~1 h (Joschua) | — |
| 5 | Make styles general | 1 day | — |
| 6 | Lab rollout: move consumers to `backstamp`, remove shims | ½ day | — |
| 7 | Public release: docs, CI, PyPI | 1–2 days | — |

- After Phase 6, the package is usable inside the lab via `pip install git+https://…`.
- PyPI is needed only at Phase 7.
- Phases 1–6 take about 5–6 days. Phase 7 brings the total to about 1½ weeks.
- Use the package across the Hypnose repos for a few weeks between Phase 6 and Phase 7. The API
  is cheap to change until outside users depend on it.
- Items under "Optional, after the first release" are not part of any phase.

---

## Why

- **Provenance:** the record is stored inside the figure file itself and can be read back
  without installing anything. A PDF emailed on its own still carries its commit, its calling
  function, its arguments and its data scope.
- **Styles:** a journal, a supervisor or a slide deck needs a different look. You add a style
  and re-run the figures, with no plotting code changed.
- **Prior art:**
  - Sumatra, recipy and DVC all track provenance, but they need a database, a log or a workflow
    system.
  - matplotlib `.mplstyle` files and SciencePlots provide styles.
  - The new part here is (a) provenance stored in the file, with no other dependency, and (b)
    save-time style rules that rcParams can't express (tick caps, hiding titles, setting legends
    apart, forcing Type 42 fonts).

## Inventory

| File | Lines | Fate |
| --- | ---: | --- |
| `provenance.py` | 303 | → `backstamp/provenance.py` (standard library only) |
| `viz/metadata.py` | 219 | → `backstamp/metadata.py` |
| `viz/save.py` | 241 | → `backstamp/save.py` |
| `viz/styles.py` | 367 | → `backstamp/styles.py` |
| `viz/legends.py` | 145 | stays (Q3); imports `legends_separate` from `backstamp` |
| `viz/series.py` | 115 | stays (Q3) |
| `viz/plotter.py` | 44 | stays (Q3) |
| `io/*`, `cli/*` | 1 300 | stay; untouched |
| `tests/test_provenance.py` | 371 | → `backstamp/tests/` |
| `tests/test_save.py` | 74 | → `backstamp/tests/` |

- The four moving modules import nothing from `io/` or `cli/`. The extraction cuts no dependency.
- The only link back from what stays: `legends.py:24` imports `legends_separate` from
  `styles`. That becomes `hypnose-helpers → backstamp`, so the dependency stays one-way.
- `src/hypnose_helpers.egg-info/` is committed. Untrack it in Phase 1 (`git rm --cached` plus a
  `.gitignore` entry).

### Consumers outside this repo

| File | Uses |
| --- | --- |
| `hypnose-behavior/src/hypnose_behavior/io/save.py` | `save_figure`, `read_figure_metadata`, `provenance`, styles (re-exported) |
| `hypnose-behavior/src/hypnose_behavior/io/save_results.py` | `provenance` (written into `manifest.json`) |
| `hypnose-behavior/src/hypnose_behavior/qc/figure_provenance.py` | `provenance`, `use_style`, module path `hypnose_helpers.provenance` |
| `hypnose-behavior/src/hypnose_behavior/qc/plot_regression.py` | `use_style` |
| `hypnose-somnotate/src/hypnose_somnotate/io/save.py` | `save_figure`, `read_figure_metadata`, `provenance` |
| `hypnose-somnotate/src/hypnose_somnotate/io/style.py` | `ensure_style`, `active_style` |

- `hypnose-sleap` imports only `io/`, so it is not affected.
- The `hypnose-behavior` QC gate (`qc/figure_provenance.py`, `qc/plot_regression.py`) is the
  regression check for every phase. Run it in the `hypnose-behavior` env pinned by
  `qc/fixtures/env.json`.

---

## Decisions

### Q1: Name

- **Preliminary: `backstamp`**, the maker's mark on the underside of porcelain. It isn't seen
  when you look at the piece, and is there when you turn it over.
- Free on PyPI as of 2026-10-05: `backstamp`, `figseal`, `plotseal`, `figsig`, `makersmark`,
  `plotstamp`, `figtag`, `figtrail`.
- Taken: `hallmark`, `colophon`, `imprint`, `pedigree`, `sigil`, `figleaf`, `lineage`,
  `keepsake`, `figmark`.
- Reserve the name on PyPI with a `0.0.1` placeholder as soon as it is final. Names get taken.
- Renaming is a search-and-replace up to Phase 6 and expensive after it.

### Q2: Where the repo lives

- **Planned: `SainsburyWellcomeCentre/backstamp`**, next to `hypnose-helpers`.
- Joschua checks with the SWC org once the package is ready for release.
- Licence: SWC's licensing policy decides it.
- Local checkout goes at `~/repos/harris_lab/backstamp`, outside `hypnose/`, because the package
  knows nothing about Hypnose.

### Q3: Whether legends, series and plotter move too

- They are general matplotlib slide helpers, but they encode a lab convention (`finish_figure`,
  `legend=`, `show=`).
- **Recommendation: keep them in `hypnose-helpers` for now.** Ship the smallest useful package,
  and move them later if outside users ask.

### Q4: What the record stores

- **Add:** `repo` (`git remote get-url origin`, with any credentials removed), `branch`,
  `python`, `backstamp` version, and `diff_sha` (hash of `git diff HEAD`) when dirty.
- **Add:** a `"schema": 1` field so later readers can tell record versions apart.
- **Keep:** `created_at`, `commit`, `version`, `function`, `module`, `file`, `lineno`, `chain`,
  `params`.
- **Do not store** the absolute `path`. It leaks usernames and directory layout into figures
  that get sent out. `file` is enough.
- **Scope:** replace the hardcoded `subjids`/`dates` with an `inputs={…}` dict whose keys are
  free-form. `subjids=` and `dates=` remain as shortcuts that fill `inputs["subject"]` and
  `inputs["date"]`.

### Q5: Filename convention

- `{save_name}_sub-XXX_date-…pdf` is the Hypnose convention. It should not be the package's
  default.
- **Recommendation:**
  - The package defaults to `{save_name}.pdf`.
  - `filename=` accepts a callable `(save_name, inputs) -> str`.
  - `hypnose-helpers` ships `hypnose_filename` and passes it in.
- This also removes the `int(s):03d` crash on non-numeric IDs (`save.py:165`) from the package.

### Q6: Python floor

- `hypnose-helpers` is `>=3.9`, because `hypnose-eeg-preprocessing` is pinned to 3.9.
- Python 3.9 has been end-of-life since 2025-10. Outside users won't need it.
- **Recommendation: `>=3.9`** while that pin exists, since it costs only the
  `packages_distributions` fallback, which already exists. Raise it to `>=3.10` once the pin goes.

---

## Target API

```python
import backstamp

backstamp.use_style("paper")                     # or a builder, a dict, or a path to .mplstyle
backstamp.register_style("lab-talk", my_rc, rules=backstamp.Rules(max_yticks=4, max_xticks=5))

path = backstamp.save_figure(
    fig, "accuracy",
    fig_dir="figures/",
    inputs={"subject": [40, 45], "date": ["20251124", "20260203"]},
)

rec = backstamp.read(path)                       # -> Record
rec.status                                       # "ok" | "unstamped" | "unreadable" | "missing"
rec.commit, rec.repo, rec.call, rec.inputs
rec.reproduce()                                  # clone, checkout and call, as text
rec.to_dict()
```

```text
$ backstamp show figures/accuracy.pdf
accuracy  subject=40,45  date=20251124–20260203
made by   hypnose_behavior.visualization.accuracy:plot_accuracy (accuracy.py:212)
commit    a1b2c3d-dirty  on main  github.com/SainsburyWellcomeCentre/hypnose-behavior
params    subjids=[40, 45]  window=50  style='presentation'
created   2026-10-05T14:02:11+01:00  python 3.12.13  backstamp 0.2.0

$ backstamp show --json figures/accuracy.pdf
$ backstamp show --reproduce figures/accuracy.pdf

$ backstamp ls figures/ --dirty --input subject=40
name          function        commit         inputs                  created
accuracy      plot_accuracy   a1b2c3d-dirty  subject=40,45 date=2…   2026-10-05
...
```

---

## Phases

Each phase is one chat. Read this plan fresh at the start, and tick the Progress table at the end.

### Phase 0: Decisions (Joschua)

- Answer Q1–Q6.
- Reserve the PyPI name.
- Create the empty GitHub repo.

### Phase 1: Extract unchanged

- Create `backstamp/` with a `src/` layout and `pyproject.toml`. Dependencies are `matplotlib` and
  `cycler` only; `pypdf` is an optional extra.
- Move the four modules **unchanged** apart from import paths. `_SKIP_MODULES` becomes
  `backstamp.*`.
- Turn `hypnose_helpers/provenance.py` and `hypnose_helpers/viz/{save,metadata,styles}.py` into
  re-export shims. Every current import keeps working.
- Shims must not appear as the calling frame. Add the shim module names to `_SKIP_MODULES`
  through `skip_modules`, or the provenance records the shim instead of the plotting function.
- Add `hypnose-helpers` dependency: `backstamp @ git+https://…@v0.1.0`.
- Move `test_provenance.py` and `test_save.py`; both pass in `backstamp`.
- The remaining `hypnose-helpers` tests pass.
- **Check:** the `hypnose-behavior` QC gate stays GREEN. `qc/figure_provenance.py` checks
  the recorded function name, so it is the test that catches a shim showing up as the caller.
- Untrack `hypnose_helpers.egg-info/`.

### Phase 2: Make provenance general

- Add the Q4 fields: `repo`, `branch`, `python`, `backstamp`, `diff_sha` and `schema`. Drop
  `path`.
- Add `inputs={…}`, keeping `subjids`/`dates` as shortcuts. `Title` is built from `inputs`.
- Add `filename=`, defaulting to `{save_name}.pdf`. `hypnose-helpers` gains `hypnose_filename` and
  its shim passes it, so Hypnose file names don't change.
- `Creator` becomes `backstamp <version>` when the caller's package version is unknown, in place of
  `"hypnose"`.
- **Backward compatibility:** the reader must still parse every existing Hypnose PDF (no
  `schema` key, `subjids`/`dates` at top level). Add a fixture PDF saved by `83dfc95` to the
  tests.
- **Check:** the QC gate. The new metadata fields are an intended output change, so regenerate
  fixtures in the same commit and confirm the diff moves only those fields.

### Phase 3: New reader

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
  - `.reproduce()`: `git clone`, `git checkout <commit>` and the recorded call as text. Warns
    when the commit is `-dirty`, since the checked-out code is not what ran.
  - `.to_dict()`, a readable `__str__` for the terminal, and `_repr_html_` for Jupyter.
- `Record` reads both schemas: `schema: 1` and the unversioned records in existing Hypnose PDFs
  (`subjids`/`dates` at top level become `inputs`).
- `backstamp show <files, folders or globs>`: one readable block per figure. `--json` and
  `--reproduce` flags.
- `backstamp ls <folder>`: one row per figure, recursive. Filters: `--dirty`,
  `--function NAME`, `--input KEY=VALUE`, `--commit SHA`, `--unstamped`.
- `hypnose-helpers` keeps `read_figure_metadata` as a shim returning `read(path).to_dict()`,
  until Phase 6.
- Works with no extra install; `pypdf` stays optional.
- **Check:** tests cover all four statuses, both schemas and the fixture PDF from Phase 2.

### Phase 4: Survival test

Measure where the metadata survives before deciding whether anything needs fixing. The
expectation, unverified: it survives byte-for-byte copies and is lost whenever something
redraws the figure.

- Make a test set with `save_figure`:
  - a small figure, a figure with a near-`MAX_BLOB` record, and a figure with non-ASCII text in
    its title and inputs.
- Add `scripts/survival_check.py <original> <returned>…`. For each returned file it reports:
  - byte-identical or not
  - record intact, partly kept (which fields), or lost
  - for `.pptx` and `.key` files (zip containers): whether the original PDF is stored inside,
    and whether its record is intact.
- Joschua runs the GUI rows and drops the returned files into one folder. The script fills
  the table.

| Route | Result |
| --- | --- |
| Finder copy / move | |
| Dropbox / OneDrive / Google Drive, upload then download | |
| git commit then clone | |
| Slack upload, recipient downloads | |
| Email attachment (UCL Outlook), recipient saves | |
| Open in Preview, close without saving | |
| Annotate in Preview, save | |
| Open in Acrobat, save | |
| Open in Illustrator / Inkscape, save as PDF | |
| Drag into Keynote, save; record of the PDF stored inside the `.key` | |
| Drag into Mac PowerPoint, save; record of the PDF stored inside the `.pptx` | |
| Insert into Windows PowerPoint, save | |
| Insert into Google Slides (via PNG), download as `.pptx` | |
| Copy-paste out of Keynote / PowerPoint into another deck | |
| Copy-paste out of Keynote / PowerPoint into Preview ("New from Clipboard") | |
| Export the deck to PDF | |
| Print to PDF | |
| Overleaf: `\includegraphics`, compile, download | |

- The filled table goes into the README in Phase 7 as "What the metadata survives".
- **Fixes are out of scope for this phase.** They are discussed after the test, with the
  results in hand. Options raised on 2026-10-05 (a visible ID, a save log, image matching,
  invisible text in the PDF) were not taken up.

### Phase 5: Make styles general

- Add `register_style(name, rc, rules=None)` as the public replacement for `_STYLE_BUILDERS`.
- `use_style` accepts a `.mplstyle` path, so labs can bring their existing style sheets.
- Add `Rules`, a small dataclass of save-time behaviour: `max_yticks`, `max_xticks`,
  `boxplot_xtick_size`, `separate_legends`, `titles`.
- Record which style is active when `use_style` is called. This replaces `_presentation_active()`,
  which detects the presentation style by matching three rcParam values, so any user style
  using those sizes would turn on the tick caps.
- Rename `nature` → `paper`. Its 20 pt axis labels and 12 pt tick labels are not Nature's
  spec, and outside users will read the name as a promise. `hypnose-helpers` registers
  `"nature"` as an alias, so lab code keeps working.
- Built-in styles: `paper`, `presentation`, `poster`.
- **Check:** this is a pure refactor for the existing styles. The QC gate's `plot_regression`
  must stay GREEN with no fixture regeneration.

### Phase 6: Lab rollout

- Move the consumers listed in the Inventory to `backstamp` imports.
- `hypnose-behavior` and `hypnose-somnotate` keep their own `io/save.py` wrappers. Only the
  import lines change.
- Remove the shims from `hypnose-helpers`. Bump it to `0.2.0`.
- Tag `backstamp v0.1.0`. Consumers pin to the tag.
- Add a "Figure provenance" section to the lab README or wiki: install, `use_style`,
  `save_figure`, `backstamp show`.

### Phase 7: Public release

- Write a README for an outside reader:
  - a 10-line quick start
  - what is recorded and what is not (see Risks)
  - what the metadata survives (the Phase 4 table)
  - a style how-to
  - a screenshot of `backstamp show`
- Set up GitHub Actions: tests on Python 3.9–3.13 on Linux, macOS and Windows. Git-dependent
  tests run against a temporary repo created in the test.
- Publish to TestPyPI first, then to PyPI through a Trusted Publisher (no API token stored).
- Write a `CHANGELOG.md` and tag `v0.2.0` or later; the first public version follows the lab
  trial.

---

## Optional, after the first release

- **Finder Quick Action:** right-click a figure → "Show provenance", calling `backstamp show`.
  For people who don't use a terminal.
- **Spotlight search:** put the function and commit into the PDF `Keywords` field, which
  Spotlight indexes. Untested.
- **PNG and SVG metadata:** matplotlib takes arbitrary text keys for both, so reading and writing
  work the same as for PDF.
- **Survival fixes**, if the Phase 4 results call for any.

---

## Risks

- **Rebuilding a figure depends on how the code is written.** `params` stores summaries
  (`<DataFrame 50x2>`), not data. The record identifies the data only when the plotting function
  receives IDs and loads the data itself. State this in the README as the convention to follow.
- **Frame-walking is fragile.** `function` is the nearest frame that isn't skipped. Wrappers
  must pass `skip_modules` or an explicit `provenance=`. This already caused trouble once, and
  `chain` exists because of it.
- **Stale `dist-info`.** If an old distribution is still installed next to the new one,
  `packages_distributions()` lists both and `version` can be wrong. This is already recorded in
  `hypnose-behavior` `DECISIONS.md` §19. The `backstamp` README should cover it too.
- **Private data in the record.** `params` can hold paths and names. Removing `path` (Q4) covers
  the obvious leak. Add `backstamp.save_figure(..., redact=[…])` if outside users ask.
- **PDF info dictionary limit.** The record is capped at 3 000 characters (`MAX_BLOB`). The new
  fields add about 200. `_dump` drops `params` first when the record is too long, which is
  acceptable.
