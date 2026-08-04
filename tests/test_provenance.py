#!/usr/bin/env python
"""Unit tests for `hypnose_helpers.provenance` and `viz.metadata`.

Run directly (no pytest needed)::

    python tests/test_provenance.py

The value summariser is where the work is: every argument any plotting function has ever
been called with has to become small, JSON-safe text without raising. Most of the cases
below are that.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from hypnose_helpers.provenance import (  # noqa: E402
    capture_call, git_commit, provenance, summarize_value,
)
from hypnose_helpers.viz.metadata import (  # noqa: E402
    MAX_BLOB, build_pdf_metadata, filter_metadata, read_figure_metadata, summarize_scope,
)
from hypnose_helpers.viz.save import save_figure  # noqa: E402


# --- the value summariser -------------------------------------------------


def test_scalars_pass_through():
    for value in (None, True, False, 0, -3, 2.5, "short"):
        assert summarize_value(value) == value, value


def test_long_strings_truncate():
    out = summarize_value("x" * 500)
    assert len(out) <= 80 and out.endswith("...")


def test_non_finite_floats_become_strings():
    """NaN and inf are not valid JSON; json.dumps emits them anyway, so catch them here."""
    for value in (float("nan"), float("inf"), float("-inf")):
        assert isinstance(summarize_value(value), str)
    assert json.loads(json.dumps({"v": summarize_value(float("nan"))}))


def test_containers_truncate_and_report_the_remainder():
    out = summarize_value(list(range(50)))
    assert len(out) == 11 and out[-1] == "...+40 more"
    out = summarize_value({f"k{i}": i for i in range(50)})
    assert len(out) == 11 and out["..."] == "+40 more"
    assert summarize_value((1, 2)) == [1, 2]
    assert sorted(summarize_value({3, 1, 2})) == [1, 2, 3]


def test_nested_containers_are_summarised_recursively():
    assert summarize_value({"a": [1, {"b": "x" * 500}]})["a"][1]["b"].endswith("...")


def test_scientific_types_become_descriptors():
    import numpy as np
    import pandas as pd

    assert summarize_value(pd.DataFrame({"a": [1, 2], "b": [3, 4]})) == "<DataFrame 2x2>"
    assert summarize_value(pd.Series([1, 2, 3])).startswith("<Series 3 ")
    assert summarize_value(np.zeros((100, 3))) == "<ndarray (100, 3) float64>"
    fig, ax = plt.subplots()
    assert summarize_value(ax).startswith("<Axes")
    plt.close(fig)


def test_unknown_objects_become_type_names():
    class Widget:
        pass

    assert summarize_value(Widget()) == "<Widget>"
    assert summarize_value(Path("/tmp/x")) == "/tmp/x"


def test_summariser_output_is_json_serialisable():
    import numpy as np
    import pandas as pd

    payload = {"df": pd.DataFrame({"a": [1]}), "arr": np.zeros(3), "nested": [{"x": None}],
               "big": list(range(100)), "nan": float("nan")}
    json.dumps(summarize_value(payload))  # must not raise


# --- capturing the call ---------------------------------------------------


def _plotter(df, subjids, *, window=30, **kwargs):
    return capture_call()


def test_capture_records_function_args_and_kwargs():
    import pandas as pd

    got = _plotter(pd.DataFrame({"a": [1, 2]}), [40, 45], window=7, color="red")
    assert got["function"] == "_plotter"
    assert got["file"] == "test_provenance.py"
    assert isinstance(got["lineno"], int)
    assert got["params"]["df"] == "<DataFrame 2x1>"
    assert got["params"]["subjids"] == [40, 45]
    assert got["params"]["window"] == 7
    assert got["params"]["color"] == "red"  # arrived via **kwargs


def test_capture_skips_the_saving_machinery():
    """The first frame must never be provenance.py itself."""
    assert capture_call()["function"] == "test_capture_skips_the_saving_machinery"


# --- git ------------------------------------------------------------------


def test_git_commit_reports_dirty_and_tolerates_a_non_repo():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        assert git_commit(root) is None  # not a repo -> None, never an exception

        run = lambda *a: subprocess.run(a, cwd=root, capture_output=True)  # noqa: E731
        run("git", "init", "-q")
        run("git", "config", "user.email", "t@t")
        run("git", "config", "user.name", "t")
        (root / "a.txt").write_text("one")
        run("git", "add", "-A")
        run("git", "commit", "-qm", "first")

        clean = git_commit(root)
        assert clean and not clean.endswith("-dirty")

        (root / "a.txt").write_text("two")
        assert git_commit(root) == f"{clean}-dirty"

    assert git_commit(None) is None
    assert git_commit(Path("/nonexistent/xyz")) is None


def test_provenance_anchors_on_the_caller_not_on_helpers():
    """The whole point: the commit must describe the code that ran.

    hypnose-helpers is installed as a library, so anchoring on its own __file__ would
    stamp every figure from every repo with the helpers commit.
    """
    record = provenance()
    assert record["function"] == "test_provenance_anchors_on_the_caller_not_on_helpers"
    assert record["file"] == "test_provenance.py"
    assert "created_at" in record
    json.dumps(record)


# --- the PDF ---------------------------------------------------------------


def test_package_version_resolves_a_renamed_distribution():
    """Import package and distribution names differ across this family.

    `hypnose_behavior` ships from `hypnose-behavior-analysis`, so swapping underscores
    for hyphens finds nothing; only packages_distributions() maps it.
    """
    from hypnose_helpers.provenance import package_version

    assert package_version("hypnose_helpers.viz.save")
    assert package_version("pandas.core.frame")
    assert package_version("__main__") is None
    assert package_version("definitely_not_installed_xyz") is None
    assert package_version(None) is None


def test_summarize_scope():
    assert summarize_scope("accuracy", 66, 20260709) == "accuracy sub-066 20260709"
    assert summarize_scope("accuracy", [40, 45, 66], ["20251124", "20260203"]) == (
        "accuracy sub-040,045,066 20251124-20260203")
    assert summarize_scope("plain") == "plain"


def test_filter_metadata_drops_keys_matplotlib_would_reject():
    out = filter_metadata({"Title": "t", "Subject": "s", "Custom": "x"})
    assert out == {"Title": "t", "Subject": "s"}


def test_oversized_records_are_shrunk_not_dropped():
    huge = {"function": "f", "params": {f"k{i}": "v" * 100 for i in range(200)}}
    blob = build_pdf_metadata("n", provenance=huge)["Subject"]
    assert len(blob) <= MAX_BLOB
    assert json.loads(blob)["function"] == "f"  # the identifying fields survive


def test_pdf_round_trip():
    """Save a real figure and read its provenance back out."""
    with tempfile.TemporaryDirectory() as tmp:
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 4, 9])
        path = save_figure(fig, "accuracy", fig_dir=tmp, subjids=[40, 66],
                           dates=[20251124, 20260203])
        plt.close(fig)
        assert path.exists()

        got = read_figure_metadata(path)
        assert got["function"] == "test_pdf_round_trip"
        assert got["file"] == "test_provenance.py"
        assert got["subjids"] == ["040", "066"]
        assert got["dates"] == ["20251124", "20260203"]
        assert got["_title"] == "accuracy sub-040,066 20251124-20260203"
        assert "created_at" in got


def test_explicit_provenance_overrides_introspection():
    with tempfile.TemporaryDirectory() as tmp:
        fig, ax = plt.subplots()
        path = save_figure(fig, "x", fig_dir=tmp, subjids=1,
                           provenance={"function": "the_real_plotter", "note": "explicit"})
        plt.close(fig)
        got = read_figure_metadata(path)
        assert got["function"] == "the_real_plotter" and got["note"] == "explicit"


def test_saving_never_warns_about_infodict_keys():
    import warnings

    with tempfile.TemporaryDirectory() as tmp:
        fig, ax = plt.subplots()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            save_figure(fig, "x", fig_dir=tmp, subjids=1, metadata={"Bogus": "dropped"})
        plt.close(fig)
        assert not [w for w in caught if "infodict" in str(w.message)]


def test_reading_a_provenance_free_or_missing_pdf_returns_empty():
    """Empty must mean "no provenance", so `if not read_figure_metadata(p)` is usable.

    matplotlib stamps a Creator on every PDF it writes, so a bare figure is not an
    empty info dictionary -- it just has nothing of ours in it.
    """
    with tempfile.TemporaryDirectory() as tmp:
        fig, ax = plt.subplots()
        bare = Path(tmp) / "bare.pdf"
        fig.savefig(bare)
        plt.close(fig)
        assert read_figure_metadata(bare) == {}
        assert read_figure_metadata(Path(tmp) / "nope.pdf") == {}
        (Path(tmp) / "junk.pdf").write_bytes(b"not a pdf")
        assert read_figure_metadata(Path(tmp) / "junk.pdf") == {}


def test_stdlib_reader_matches_on_awkward_characters():
    """No pypdf in the pinned env, so the fallback parser is the one that must work."""
    from hypnose_helpers.viz.metadata import _read_info_stdlib

    with tempfile.TemporaryDirectory() as tmp:
        fig, ax = plt.subplots()
        note = r"parens ( ) and \ backslash"
        path = save_figure(fig, "x", fig_dir=tmp, subjids=1,
                           provenance={"function": "f", "note": note})
        plt.close(fig)
        assert json.loads(_read_info_stdlib(path)["Subject"])["note"] == note
        assert read_figure_metadata(path)["note"] == note


def test_a_wrapper_can_exclude_itself():
    """A repo whose save_figure is a thin wrapper must not name itself as the plotter.

    Capturing inside the wrapper is not enough -- capture_call still returns the
    wrapper's own frame. Only the skip list fixes it.
    """
    import types

    # A stand-in for hypnose_behavior.io.save, in its own module namespace -- the
    # wrapper and the plotter must not share one, or skipping hides both.
    wrapper_mod = types.ModuleType("fake_repo.io.save")
    wrapper_mod.provenance = provenance
    exec(
        "def save_figure():\n"
        "    return provenance(), provenance(skip_modules=('fake_repo.io.save',))\n",
        wrapper_mod.__dict__,
    )

    def real_plotter():
        return wrapper_mod.save_figure()

    naive, skipped = real_plotter()
    assert naive["function"] == "save_figure"      # the bug this guards against
    assert skipped["function"] == "real_plotter"   # what we actually want


def test_chain_reaches_past_an_inner_save_closure():
    """The real case from movement_analysis_utils: a nested `_save_fig` helper.

    `function` can only ever be "the nearest frame we did not skip", and in real
    plotting code that is often a local closure rather than the analysis that produced
    the figure. The chain is what makes the enclosing function recoverable.
    """
    def run_movement_stats_batch():
        def _save_fig():  # the closure that actually calls save_figure
            return provenance()
        return _save_fig()

    record = run_movement_stats_batch()
    assert record["function"] == "_save_fig"
    assert record["chain"][:2] == ["_save_fig", "run_movement_stats_batch"]
    assert "test_chain_reaches_past_an_inner_save_closure" in record["chain"]


def test_chain_survives_the_pdf_round_trip():
    with tempfile.TemporaryDirectory() as tmp:
        def analysis():
            def _save_fig():
                fig, ax = plt.subplots()
                path = save_figure(fig, "x", fig_dir=tmp, subjids=1)
                plt.close(fig)
                return path
            return _save_fig()

        got = read_figure_metadata(analysis())
        assert got["chain"][:2] == ["_save_fig", "analysis"]


def test_blob_stays_ascii_so_the_pdf_string_encoding_is_predictable():
    """Any non-ASCII character makes matplotlib write the string as UTF-16BE.

    The truncation markers used to be "…", which silently switched the encoding and
    broke the stdlib reader for exactly the records that needed truncating.
    """
    from hypnose_helpers.viz.metadata import _dump

    blob = _dump({"params": summarize_value({"big": list(range(99)), "s": "y" * 300})})
    blob.encode("ascii")  # must not raise
    assert "..." in blob


def test_round_trip_survives_truncation_and_non_ascii_arguments():
    with tempfile.TemporaryDirectory() as tmp:
        fig, ax = plt.subplots()
        path = save_figure(fig, "x", fig_dir=tmp, subjids=1, provenance={
            "function": "f",
            "params": summarize_value({"many": list(range(99)), "unicode": "µ ± σ °C"}),
        })
        plt.close(fig)
        got = read_figure_metadata(path)
        assert got["function"] == "f"
        assert got["params"]["many"][-1] == "...+89 more"
        assert got["params"]["unicode"] == "µ ± σ °C"


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failures = []
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001
            failures.append(test.__name__)
            print(f"  [FAIL] {test.__name__}: {type(exc).__name__}: {exc}")
        else:
            print(f"  [ok]   {test.__name__}")
    print(f"\n{len(tests) - len(failures)}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
