#!/usr/bin/env python
"""Unit tests for `hypnose_helpers.io.layout` -- fast, and they never touch the mount.

Run directly (no pytest needed, and none is installed in the pinned analysis env)::

    python tests/test_layout.py

pytest collects the same `test_*` functions unchanged where it is available.

These matter more than usual: the behaviour repo's golden-master regression covers
`trial_data` and the metrics dict, so it would catch a session resolving to the *wrong*
directory but is blind to session ordering, `session_index`, and every selector form.
That is exactly the surface below.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hypnose_helpers.io.layout import (  # noqa: E402
    DuplicateSessionError,
    SessionLayout,
    filter_sessions,
    list_sessions,
    normalize_subjid,
    parse_session_dirname,
    parse_subject_dirname,
)


def make_tree(root: Path, spec: dict) -> None:
    """spec: {"sub-036_id-1": ["ses-010_date-20260301", ...]}"""
    for subject, sessions in spec.items():
        for session in sessions:
            (root / subject / session).mkdir(parents=True, exist_ok=True)


# --- naming ---------------------------------------------------------------


def test_normalize_subjid_accepts_every_written_form():
    for value in (66, "66", "066", "sub-66", "sub-066", " 66 "):
        assert normalize_subjid(value) == "sub-066", value


def test_normalize_subjid_rejects_nonsense():
    for value in ("sub-abc", "", "12x"):
        try:
            normalize_subjid(value)
        except ValueError:
            continue
        raise AssertionError(f"{value!r} should not parse as a subject")


def test_parse_dirnames():
    assert parse_subject_dirname("sub-066_id-123") == 66
    assert parse_subject_dirname("sub-066") == 66
    assert parse_subject_dirname("figures") is None
    assert parse_session_dirname("ses-040_date-20260709") == (40, "20260709")
    # A non-numeric session token is tolerated: still selectable by date.
    assert parse_session_dirname("ses-pilot_date-20260709") == (None, "20260709")
    assert parse_session_dirname("saved_analysis_results") is None


# --- ordering vs indexing -------------------------------------------------


def test_list_order_is_dirname_but_index_is_date_rank():
    """The distinction the whole design rests on.

    Sessions come back in `ses` order -- byte-identical to the
    `sorted(subj_dir.glob("ses-*_date-*"))` every call site used before -- while
    `session_index` ranks by date, so a subject numbered out of chronological order
    gets a correct x-axis without its concatenation order shifting.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        make_tree(root, {"sub-036_id-1": [
            "ses-010_date-20260301",
            "ses-011_date-20260101",
            "ses-020_date-20260201",
        ]})
        sessions = list_sessions(root / "sub-036_id-1")

        assert [s.ses for s in sessions] == [10, 11, 20]
        assert [s.date for s in sessions] == ["20260301", "20260101", "20260201"]
        assert [s.session_index for s in sessions] == [3, 1, 2]


def test_session_index_is_gap_free_despite_ses_holes():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        make_tree(root, {"sub-038_id-1": [
            "ses-001_date-20260101",
            "ses-038_date-20260102",
            "ses-097_date-20260103",
        ]})
        sessions = list_sessions(root / "sub-038_id-1")
        assert [s.ses for s in sessions] == [1, 38, 97]
        assert [s.session_index for s in sessions] == [1, 2, 3]


def test_stray_directories_are_ignored_not_raised_on():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        make_tree(root, {"sub-040_id-1": ["ses-001_date-20260101"]})
        (root / "sub-040_id-1" / "figures").mkdir()
        (root / "sub-040_id-1" / "ses-notasession").mkdir()
        assert len(list_sessions(root / "sub-040_id-1")) == 1


# --- ambiguity is refused -------------------------------------------------


def test_duplicate_ses_raises_naming_both():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        make_tree(root, {"sub-036_id-1": [
            "ses-060_date-20260101",
            "ses-060_date-20260202",
        ]})
        try:
            list_sessions(root / "sub-036_id-1")
        except DuplicateSessionError as exc:
            assert "20260101" in str(exc) and "20260202" in str(exc)
            return
        raise AssertionError("a repeated ses must raise")


def test_duplicate_date_raises():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        make_tree(root, {"sub-036_id-1": [
            "ses-060_date-20260101",
            "ses-061_date-20260101",
        ]})
        try:
            list_sessions(root / "sub-036_id-1")
        except DuplicateSessionError:
            return
        raise AssertionError("a repeated date must raise")


def test_duplicate_subject_dir_raises():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        make_tree(root, {
            "sub-040_id-1": ["ses-001_date-20260101"],
            "sub-040_id-2": ["ses-002_date-20260102"],
        })
        layout = SessionLayout(root, name="test")
        try:
            layout.subject_dir(40)
        except DuplicateSessionError:
            return
        raise AssertionError("two directories for one subject must raise")


# --- selection ------------------------------------------------------------


def _sample_layout(root: Path) -> SessionLayout:
    make_tree(root, {"sub-066_id-1": [
        "ses-001_date-20260701",
        "ses-002_date-20260707",
        "ses-005_date-20260712",
        "ses-009_date-20260718",
        "ses-012_date-20260801",
    ]})
    return SessionLayout(root, name="test")


def test_ses_and_date_are_interchangeable_selectors():
    with tempfile.TemporaryDirectory() as tmp:
        layout = _sample_layout(Path(tmp))
        by_ses = layout.find_session(66, ses=5)
        by_date = layout.find_session(66, date="20260712")
        assert by_ses.path == by_date.path


def test_selector_forms():
    with tempfile.TemporaryDirectory() as tmp:
        layout = _sample_layout(Path(tmp))
        dates = lambda **kw: [s.date for s in layout.find_sessions(66, **kw)]  # noqa: E731

        assert dates(ses=5) == ["20260712"]
        assert dates(ses="ses-005") == ["20260712"]
        assert dates(ses="2,5") == ["20260707", "20260712"]
        # "A-B" is unambiguous: a bare ses number never contains a hyphen.
        assert dates(ses="02-09") == ["20260707", "20260712", "20260718"]
        assert dates(ses_range=(2, 9)) == ["20260707", "20260712", "20260718"]
        assert dates(date="20260707") == ["20260707"]
        assert dates(date=20260707) == ["20260707"]
        assert dates(date_range="20260707-20260718") == ["20260707", "20260712", "20260718"]
        # Inverted bounds are sorted, matching parse_date_range.
        assert dates(date_range="20260718-20260707") == ["20260707", "20260712", "20260718"]
        # Open-ended bounds: existing callers pass these meaning "everything up to here".
        assert dates(date_range=(None, "20260707")) == ["20260701", "20260707"]
        assert dates(date_range=("20260718", None)) == ["20260718", "20260801"]
        # Filters intersect.
        assert dates(ses_range=(1, 5), date_range=("20260707", "20260801")) == [
            "20260707", "20260712"]
        # No match is empty, not an error.
        assert dates(date="20991231") == []


def test_empty_selector_matches_nothing_but_none_matches_everything():
    """`None` and `[]` must not mean the same thing.

    Callers build a per-subject date list and pass it straight through; a subject with
    no requested dates has to yield no sessions. Treating `[]` as "no filter" would
    quietly plot the animal's entire history instead.
    """
    with tempfile.TemporaryDirectory() as tmp:
        layout = _sample_layout(Path(tmp))
        assert layout.find_sessions(66, date=[]) == []
        assert layout.find_sessions(66, ses=[]) == []
        assert len(layout.find_sessions(66, date=None)) == 5
        assert len(layout.find_sessions(66)) == 5


def test_index_selects_the_first_n_sessions_across_cohorts():
    """The case `ses` cannot express: "each subject's first 9 sessions".

    `ses` is the number on the directory. It has holes, and for a subject whose
    numbering carried over from an earlier protocol it does not start near 1 -- so
    `ses` 1-9 returns 9, 3 and 0 sessions for these three animals, while index 1-9
    returns 9 each, spanning cohorts recorded months apart.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        make_tree(root, {
            # contiguous numbering
            "sub-040_id-1": [f"ses-{n:03d}_date-202511{n:02d}" for n in range(1, 13)],
            # gaps in ses
            "sub-057_id-2": [f"ses-{n:03d}_date-202607{i:02d}" for i, n in
                             enumerate([1, 3, 7, 12, 15, 19, 24, 30, 38, 41], start=1)],
            # numbering continued from an earlier protocol
            "sub-062_id-3": [f"ses-{n:03d}_date-202607{i:02d}" for i, n in
                             enumerate(range(38, 48), start=1)],
        })
        layout = SessionLayout(root, name="test", subject_pattern="{subject}_id-*")

        by_ses = {s: len(layout.find_sessions(s, ses="01-09")) for s, _ in layout.iter_subjects()}
        assert by_ses == {40: 9, 57: 3, 62: 0}

        by_index = {s: layout.find_sessions(s, index_range=(1, 9))
                    for s, _ in layout.iter_subjects()}
        assert {s: len(v) for s, v in by_index.items()} == {40: 9, 57: 9, 62: 9}
        # ...and they really are each animal's first nine, chronologically.
        for refs in by_index.values():
            assert sorted(r.session_index for r in refs) == list(range(1, 10))
        assert by_index[40][0].date.startswith("202511")   # different cohorts
        assert by_index[62][0].date.startswith("202607")


def test_index_selector_forms():
    with tempfile.TemporaryDirectory() as tmp:
        layout = _sample_layout(Path(tmp))  # ses 1,2,5,9,12 over 5 dates
        idx = lambda **kw: [s.session_index for s in layout.find_sessions(66, **kw)]  # noqa: E731

        assert idx(index=1) == [1]
        assert idx(index="2,4") == [2, 4]
        assert idx(index="2-4") == [2, 3, 4]
        assert idx(index_range=(2, 4)) == [2, 3, 4]
        assert idx(index_range=(None, 2)) == [1, 2]
        assert idx(index_range=(4, None)) == [4, 5]
        assert idx(index=[]) == []
        assert idx(index=None) == [1, 2, 3, 4, 5]
        # index and ses intersect like every other pair of filters
        assert idx(index_range=(1, 3), ses_range=(2, 12)) == [2, 3]
        # a ses- prefix is meaningless for an index and must be refused
        try:
            layout.find_sessions(66, index="ses-01")
        except ValueError:
            return
        raise AssertionError("index must not accept a ses- prefix")


def test_index_is_the_full_history_rank_even_after_date_filtering():
    """Filtering by date first must not renumber the index.

    Otherwise "first nine sessions" would silently mean "first nine of what is left",
    which is not comparable across subjects -- the entire point of the key.
    """
    with tempfile.TemporaryDirectory() as tmp:
        layout = _sample_layout(Path(tmp))
        late = layout.find_sessions(66, date_range=("20260712", "20260801"))
        assert [s.session_index for s in late] == [3, 4, 5]
        assert filter_sessions(late, index_range=(1, 2)) == []


def test_session_index_by_either_key():
    with tempfile.TemporaryDirectory() as tmp:
        layout = _sample_layout(Path(tmp))
        assert layout.session_index(66, "20260712") == 3
        assert layout.session_index(66, 5) == 3
        assert layout.session_index(66, "ses-012") == 5


# --- roots ----------------------------------------------------------------


def test_callable_root_is_re_resolved_every_time():
    """The QC harness redirects its derivatives root per session, mid-process.

    A SessionLayout that captured a Path at construction would keep answering from the
    previous root -- silently, with plausible-looking results.
    """
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        make_tree(base / "first", {"sub-066_id-1": ["ses-001_date-20260101"]})
        make_tree(base / "second", {"sub-066_id-1": ["ses-002_date-20260202"]})

        current = {"root": base / "first"}
        layout = SessionLayout(lambda: current["root"], name="test")
        assert layout.find_session(66, date="20260101").ses == 1

        current["root"] = base / "second"
        assert layout.find_session(66, date="20260202").ses == 2


def test_missing_subject_raises_but_missing_ok_returns_empty():
    with tempfile.TemporaryDirectory() as tmp:
        layout = _sample_layout(Path(tmp))
        assert layout.find_sessions(999, missing_ok=True) == []
        assert layout.subject_dir(999, missing_ok=True) is None
        try:
            layout.find_sessions(999)
        except FileNotFoundError as exc:
            assert "sub-999" in str(exc) and "test" in str(exc)
            return
        raise AssertionError("an unknown subject must raise by default")


def test_find_session_miss_reports_what_exists():
    with tempfile.TemporaryDirectory() as tmp:
        layout = _sample_layout(Path(tmp))
        try:
            layout.find_session(66, date="20991231")
        except FileNotFoundError as exc:
            assert "ses-005_date-20260712" in str(exc)
            return
        raise AssertionError("a missing date must raise")


def test_iter_subjects():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        make_tree(root, {
            "sub-040_id-1": ["ses-001_date-20260101"],
            "sub-066_id-2": ["ses-001_date-20260101"],
        })
        (root / "figures").mkdir()
        layout = SessionLayout(root, name="test")

        assert [s for s, _ in layout.iter_subjects()] == [40, 66]
        assert [s for s, _ in layout.iter_subjects([66, 40])] == [66, 40]
        # A named subject that does not exist is skipped, not raised on.
        assert [s for s, _ in layout.iter_subjects([40, 999])] == [40]


def test_subject_pattern_narrows_the_glob():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        make_tree(root, {"sub-040": ["ses-001_date-20260101"]})
        assert SessionLayout(root, name="t").subject_dir(40).name == "sub-040"
        # The behaviour tree always carries the id suffix, so it narrows the pattern.
        strict = SessionLayout(root, name="t", subject_pattern="{subject}_id-*")
        assert strict.subject_dir(40, missing_ok=True) is None


def test_narrowed_pattern_also_narrows_iter_subjects():
    """iter_subjects() must not surface subjects subject_dir() would refuse."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        make_tree(root, {
            "sub-040_id-1": ["ses-001_date-20260101"],
            "sub-041": ["ses-001_date-20260101"],
        })
        assert [s for s, _ in SessionLayout(root, name="t").iter_subjects()] == [40, 41]
        strict = SessionLayout(root, name="t", subject_pattern="{subject}_id-*")
        assert [s for s, _ in strict.iter_subjects()] == [40]


# --- filter_sessions on a bare list ---------------------------------------


def test_filter_sessions_preserves_input_order():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        make_tree(root, {"sub-036_id-1": [
            "ses-010_date-20260301",
            "ses-011_date-20260101",
            "ses-020_date-20260201",
        ]})
        sessions = list_sessions(root / "sub-036_id-1")
        kept = filter_sessions(sessions, date_range=("20260101", "20260301"))
        assert [s.ses for s in kept] == [10, 11, 20]
        assert [s.session_index for s in kept] == [3, 1, 2]


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failures = []
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001 - a test runner reports everything
            failures.append((test.__name__, exc))
            print(f"  [FAIL] {test.__name__}: {type(exc).__name__}: {exc}")
        else:
            print(f"  [ok]   {test.__name__}")
    print(f"\n{len(tests) - len(failures)}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
