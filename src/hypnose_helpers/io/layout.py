"""The `sub-XXX/ses-YY_date-YYYYMMDD` directory layout: walking it, and naming it.

Every Hypnose dataset -- behaviour, EEG, and whatever comes next -- lays its subjects
out the same way::

    <root>/sub-xxx_id-123/ses-xxx_date-YYYYMMDD/<modality>/

so "find the session directory for this subject and date" is a property of the *layout*,
not of the data. 

Two layers, because they answer different questions:

* the module-level functions (`list_sessions`, `filter_sessions`, `normalize_subjid`) are
  pure and root-free -- give them a subject directory and they work;
* `SessionLayout` binds a *root* so callers get the plan's intended signature,
  ``find_sessions(subjid, ses=..., date=...)``, with no root to pass or get wrong.

Bind the root as a **callable**, not a Path::

    derivatives = SessionLayout(get_derivatives_root, name="derivatives")

A resolved Path captured at import is frozen for the life of the process, which breaks
any consumer that redirects its data root at runtime -- the behaviour repo's QC harness
does exactly that, per session, via an env var plus ``cache_clear()``. 

Selection is forgiving in the way the CLI already is (``66`` / ``"066"`` / ``"sub-066"`` /
``"66,67"``), and `ses` and `date` are interchangeable selectors because the directory
name carries both.

Ordering, deliberately kept as two separate things:

* sessions are returned in **directory-name order**, which is `ses` order. That is what
  every ``sorted(subj_dir.glob("ses-*_date-*"))`` in the family already produced, so
  concatenation order is unchanged.
* ``SessionRef.session_index`` is the **date rank** within the subject, 1..N and gap-free.
  `ses` numbers have holes (29% of current subjects), so they make a poor x-axis; the two
  orders differ for any subject whose sessions were numbered out of chronological order.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Sequence, Tuple, Union

from .selectors import (
    parse_dates, parse_date_range, parse_index_range, parse_indices,
    parse_sessions, parse_session_range,
)

# `sub-066` or `sub-066_id-123`; the `_id-*` suffix is not used to select anything.
SUBJECT_DIR_RE = re.compile(r"^sub-(\d+)(?:_|$)")

# `ses-040_date-20260709`. The session token is not required to be numeric -- a
# non-numeric one still yields a usable ref, selectable by date.
SESSION_DIR_RE = re.compile(r"^ses-([^_]+)_date-(\d{8})$")

# What a subject directory is called, given the `sub-NNN` token. `{subject}*` matches
# both bare `sub-066` and `sub-066_id-123`; a consumer whose tree always carries the id
# suffix can narrow it to `{subject}_id-*`.
DEFAULT_SUBJECT_PATTERN = "{subject}*"


def normalize_subjid(subjid: Union[int, str]) -> str:
    """The canonical `sub-NNN` directory token for a subject.

    Accepts ``66``, ``"66"``, ``"066"``, ``"sub-66"`` and ``"sub-066"``; always returns
    three-digit zero-padded form. Replaces the ~26 hand-rolled
    ``f"sub-{str(subjid).zfill(3)}"`` expressions that fed a glob.
    """
    return f"sub-{parse_subject(subjid):03d}"


def parse_subject(value: Union[int, str]) -> int:
    """Re-exported from `selectors` so callers need only one import here."""
    from .selectors import parse_subject as _parse_subject
    return _parse_subject(value)


def parse_subject_dirname(name: str) -> Optional[int]:
    """The subject number in a directory name, or None if it is not a subject dir."""
    match = SUBJECT_DIR_RE.match(name)
    return int(match.group(1)) if match else None


def parse_session_dirname(name: str) -> Optional[Tuple[Optional[int], str]]:
    """``(ses, date)`` for a session directory name, or None if it is not one.

    ``ses`` is None when the session token is not numeric -- tolerated rather than
    rejected, because such a session is still perfectly selectable by date.
    """
    match = SESSION_DIR_RE.match(name)
    if not match:
        return None
    token, date = match.groups()
    return (int(token) if token.isdigit() else None), date


@dataclass(frozen=True)
class SessionRef:
    """One session directory, with everything a caller needs to avoid re-parsing it.

    ``ses`` identifies, ``session_index`` orders: see the module docstring.
    """

    subjid: int
    subject: str
    subject_dir: Path
    ses: Optional[int]
    date: str
    path: Path
    session_index: int

    def __str__(self) -> str:  # pragma: no cover - convenience only
        ses = f"ses-{self.ses:03d}" if self.ses is not None else "ses-?"
        return f"{self.subject}/{ses}_date-{self.date}"


class DuplicateSessionError(ValueError):
    """Two session directories claim the same `ses` or the same date for one subject.

    Raised rather than resolved, because picking the first match is precisely the
    failure that surfaces months later as an unexplained result. Both candidate paths
    are named so the tree can be fixed.
    """


def list_sessions(subject_dir: Union[str, Path], *, subjid: Optional[int] = None) -> List[SessionRef]:
    """Every session under ``subject_dir``, in directory-name order, index-annotated.

    Unparseable directory names are skipped, not raised on -- a stray folder in a
    subject directory is not an error. Genuine ambiguity *is*: a repeated `ses` or a
    repeated date raises `DuplicateSessionError`.
    """
    subject_dir = Path(subject_dir)
    if subjid is None:
        subjid = parse_subject_dirname(subject_dir.name)
        if subjid is None:
            raise ValueError(
                f"cannot infer a subject number from directory name {subject_dir.name!r}; "
                "pass subjid= explicitly."
            )
    subject = f"sub-{subjid:03d}"

    found = []
    for path in sorted(subject_dir.glob("ses-*_date-*")):
        if not path.is_dir():
            continue
        parsed = parse_session_dirname(path.name)
        if parsed is None:
            continue
        ses, date = parsed
        found.append((ses, date, path))

    _reject_duplicates(subject, found)

    # Rank by date over the whole subject, so the index is gap-free and stable under
    # any later filtering. Dates are YYYYMMDD, so lexical order is chronological.
    ranks = {date: i for i, date in enumerate(sorted(d for _, d, _ in found), start=1)}

    return [
        SessionRef(
            subjid=subjid,
            subject=subject,
            subject_dir=subject_dir,
            ses=ses,
            date=date,
            path=path,
            session_index=ranks[date],
        )
        for ses, date, path in found
    ]


def _reject_duplicates(subject: str, found: Sequence[Tuple[Optional[int], str, Path]]) -> None:
    """Raise if any `ses` or any date appears twice among ``found``."""
    for label, key_index in (("ses", 0), ("date", 1)):
        seen: dict = {}
        for entry in found:
            key = entry[key_index]
            if key is None:  # a non-numeric session token cannot collide meaningfully
                continue
            if key in seen:
                raise DuplicateSessionError(
                    f"{subject} has two directories with the same {label} "
                    f"{key!r}:\n  {seen[key]}\n  {entry[2]}\n"
                    "Selecting either one silently would make the result unexplainable; "
                    "fix the tree instead."
                )
            seen[key] = entry[2]


def filter_sessions(
    sessions: Iterable[SessionRef],
    *,
    ses=None,
    date=None,
    index=None,
    ses_range=None,
    date_range=None,
    index_range=None,
) -> List[SessionRef]:
    """Narrow a session list. Every filter supplied must match (they intersect).

    Three interchangeable keys, answering different questions:

    ``ses``
        the number written on the directory. Stable, and what you quote in a lab book.
    ``date``
        the session date, ``YYYYMMDD``.
    ``index``
        the subject's gap-free chronological rank, 1..N -- "its first nine sessions",
        comparable across animals recorded months apart. `ses` cannot express that: it
        has holes, and for a subject whose numbering carried over from an earlier
        protocol it does not start near 1 at all.

    Each accepts a single value, a list, a comma-separated string, or an inclusive
    ``A-B`` range -- a bare `ses`, index or YYYYMMDD date all lack a hyphen, so the
    range form is never ambiguous. The ``*_range`` arguments are the explicit forms,
    and also accept a 2-tuple whose bounds may be None (unbounded).

    ``None`` means "do not filter on this"; an **empty** list means "match nothing".
    The distinction is load-bearing -- callers build date lists per subject, and a
    subject with no requested dates must yield no sessions rather than all of them.

    Note ``index`` is read off each `SessionRef`, and those are ranked over the
    subject's *whole* history when the list is built. So filtering by date first and
    index second still means "of this animal's first nine sessions", not "the first
    nine of what is left" -- which is what makes it comparable across subjects.
    """
    result = list(sessions)

    ses_values, ses_bounds = _split_selector(ses, parse_sessions, parse_session_range)
    date_values, date_bounds = _split_selector(date, parse_dates, parse_date_range)
    index_values, index_bounds = _split_selector(index, parse_indices, parse_index_range)

    if ses_range is not None:
        ses_bounds = _merge_bounds(ses_bounds, _coerce_range(ses_range, parse_session_range))
    if date_range is not None:
        date_bounds = _merge_bounds(date_bounds, _coerce_range(date_range, parse_date_range))
    if index_range is not None:
        index_bounds = _merge_bounds(index_bounds,
                                     _coerce_range(index_range, parse_index_range))

    if ses_values is not None:
        wanted = set(ses_values)
        result = [s for s in result if s.ses in wanted]
    if ses_bounds is not None:
        low, high = ses_bounds
        result = [
            s for s in result
            if s.ses is not None
            and (low is None or s.ses >= low)
            and (high is None or s.ses <= high)
        ]
    if date_values is not None:
        wanted = set(date_values)
        result = [s for s in result if s.date in wanted]
    if date_bounds is not None:
        low, high = date_bounds
        result = [
            s for s in result
            if (low is None or s.date >= low) and (high is None or s.date <= high)
        ]
    if index_values is not None:
        wanted = set(index_values)
        result = [s for s in result if s.session_index in wanted]
    if index_bounds is not None:
        low, high = index_bounds
        result = [
            s for s in result
            if (low is None or s.session_index >= low)
            and (high is None or s.session_index <= high)
        ]
    return result


def _split_selector(value, parse_values, parse_range):
    """Read a `ses=`/`date=` argument as either a value list or an inclusive range.

    A 2-tuple, or a string holding a digit-hyphen-digit, means a range; anything else is
    a set of values. Returns ``(values, bounds)``; both are None when nothing was asked
    for, and exactly one is populated otherwise. An empty ``values`` list is a real
    filter (matching nothing), which is why None rather than ``[]`` signals "no filter".
    """
    if value is None:
        return None, None
    if isinstance(value, tuple) and len(value) == 2:
        return None, _coerce_range(value, parse_range)
    if isinstance(value, str) and re.search(r"(?<=\d)-(?=\d)", value):
        return None, parse_range(value)
    return parse_values(value), None


def _coerce_range(value, parse_range):
    """A range from a string, or from a 2-sequence whose bounds may be None.

    Open-ended bounds mean "everything from/up to here" and are used by existing
    callers, but the shared selector parsers reject them; each present bound is
    validated here by round-tripping it through the range parser on its own.
    """
    if isinstance(value, (list, tuple)) and len(value) == 2 and any(v is None for v in value):
        low, high = value
        return (
            parse_range(f"{low}-{low}")[0] if low is not None else None,
            parse_range(f"{high}-{high}")[0] if high is not None else None,
        )
    return parse_range(value)


def _merge_bounds(existing, new):
    """Intersect two ranges; either may be None."""
    if existing is None:
        return new
    if new is None:
        return existing
    lows = [b for b in (existing[0], new[0]) if b is not None]
    highs = [b for b in (existing[1], new[1]) if b is not None]
    return (max(lows) if lows else None, min(highs) if highs else None)


class SessionLayout:
    """Subject and session discovery under one dataset root.

    Parameters
    ----------
    root
        The dataset root, as a Path or -- preferably -- a zero-argument callable
        returning one. A callable is re-resolved on every access, so a consumer that
        redirects its root at runtime (env var, profile switch, test sandbox) is
        followed rather than silently ignored.
    name
        Used in error messages, so "no subject directory under <root>" says *which*
        root -- rawdata and derivatives are easy to confuse when one is empty.
    subject_pattern
        Glob for a subject directory, with ``{subject}`` replaced by the `sub-NNN`
        token. Defaults to ``{subject}*``, matching both bare and `_id-` suffixed
        trees.
    """

    def __init__(
        self,
        root: Union[str, Path, Callable[[], Path]],
        *,
        name: str = "dataset",
        subject_pattern: str = DEFAULT_SUBJECT_PATTERN,
    ) -> None:
        self._root = root
        self._name = name
        self._subject_pattern = subject_pattern

    @property
    def root(self) -> Path:
        """The dataset root, resolved now -- never cached. See the class docstring."""
        return Path(self._root() if callable(self._root) else self._root)

    @property
    def name(self) -> str:
        return self._name

    def __repr__(self) -> str:  # pragma: no cover - debugging convenience
        return f"SessionLayout(name={self._name!r}, root={self.root})"

    def _all_subjects_glob(self) -> str:
        """The subject pattern widened to every subject.

        Derived from ``subject_pattern`` rather than hardcoded to ``sub-*`` so that a
        consumer which narrowed the pattern also narrows its "all subjects" sweep --
        otherwise `iter_subjects()` would pick up directories `subject_dir()` refuses
        to resolve. Collapses the ``**`` the default pattern would otherwise produce,
        since pathlib reads that as a recursive glob in some positions.
        """
        return self._subject_pattern.format(subject="sub-*").replace("**", "*")

    # --- subjects -----------------------------------------------------------

    def subject_dir(self, subjid, *, missing_ok: bool = False) -> Optional[Path]:
        """The directory for one subject.

        Raises `FileNotFoundError` when it does not exist, or
        `DuplicateSessionError` when several match -- with ``missing_ok=True``,
        returns None for the absent case instead, for callers that skip and carry on.
        """
        subject = normalize_subjid(subjid)
        root = self.root
        matches = sorted(
            p for p in root.glob(self._subject_pattern.format(subject=subject)) if p.is_dir()
        )
        if not matches:
            if missing_ok:
                return None
            raise FileNotFoundError(
                f"No subject directory for {subject} under the {self._name} root {root}"
            )
        if len(matches) > 1:
            raise DuplicateSessionError(
                f"{subject} has several directories under the {self._name} root:\n  "
                + "\n  ".join(str(p) for p in matches)
            )
        return matches[0]

    def iter_subjects(self, subjids: Optional[Iterable] = None) -> List[Tuple[int, Path]]:
        """``(subjid, subject_dir)`` pairs, sorted by subject number.

        ``subjids=None`` means every subject in the tree. Named subjects that do not
        exist are skipped rather than raised on, so a cohort list may over-specify;
        use `subject_dir` when a missing subject should be an error.
        """
        root = self.root
        if subjids is None:
            found = []
            for path in sorted(root.glob(self._all_subjects_glob())):
                if not path.is_dir():
                    continue
                subjid = parse_subject_dirname(path.name)
                if subjid is not None:
                    found.append((subjid, path))
            return found

        pairs = []
        for value in subjids:
            subjid = parse_subject(value)
            path = self.subject_dir(subjid, missing_ok=True)
            if path is not None:
                pairs.append((subjid, path))
        return pairs

    # --- sessions -----------------------------------------------------------

    def find_sessions(
        self,
        subjid,
        *,
        ses=None,
        date=None,
        index=None,
        ses_range=None,
        date_range=None,
        index_range=None,
        missing_ok: bool = False,
    ) -> List[SessionRef]:
        """Sessions for one subject, optionally narrowed by `ses` and/or date.

        Returns ``[]`` when the subject exists but nothing matches. A *missing* subject
        raises unless ``missing_ok=True``, since "no such animal" and "no session that
        day" are different problems and only one of them is routine.
        """
        subject_dir = self.subject_dir(subjid, missing_ok=missing_ok)
        if subject_dir is None:
            return []
        sessions = list_sessions(subject_dir, subjid=parse_subject(subjid))
        return filter_sessions(
            sessions, ses=ses, date=date, index=index, ses_range=ses_range,
            date_range=date_range, index_range=index_range,
        )

    def find_session(self, subjid, *, ses=None, date=None, index=None) -> SessionRef:
        """Exactly one session, or raise.

        The point-lookup form: the ~10 sites that resolved a subject and a date to a
        single directory. Reports the available sessions on a miss, as the better of
        the previous implementations did.
        """
        matches = self.find_sessions(subjid, ses=ses, date=date, index=index)
        if len(matches) == 1:
            return matches[0]

        subject = normalize_subjid(subjid)
        wanted = ", ".join(
            f"{k}={v!r}" for k, v in (("ses", ses), ("date", date), ("index", index))
            if v is not None
        ) or "any session"
        if not matches:
            available = [
                f"ses-{s.ses:03d}_date-{s.date}" if s.ses is not None else f"date-{s.date}"
                for s in self.find_sessions(subjid)
            ]
            raise FileNotFoundError(
                f"No session with {wanted} for {subject} under the {self._name} root "
                f"{self.root}.\nAvailable sessions: {available}"
            )
        raise DuplicateSessionError(
            f"{wanted} matches {len(matches)} sessions for {subject}:\n  "
            + "\n  ".join(str(s.path) for s in matches)
        )

    def session_index(self, subjid, date_or_ses) -> int:
        """The subject's 1..N date rank for one session -- the plotting ordinal.

        Accepts either key: an 8-digit value is read as a date, anything else as a
        `ses` number. Gap-free by construction, unlike `ses` itself.
        """
        token = str(date_or_ses).strip()
        key = {"date": token} if re.fullmatch(r"\d{8}", token) else {"ses": token}
        return self.find_session(subjid, **key).session_index


__all__ = [
    "SessionRef",
    "SessionLayout",
    "DuplicateSessionError",
    "list_sessions",
    "filter_sessions",
    "normalize_subjid",
    "parse_subject",
    "parse_subject_dirname",
    "parse_session_dirname",
    "SUBJECT_DIR_RE",
    "SESSION_DIR_RE",
]
