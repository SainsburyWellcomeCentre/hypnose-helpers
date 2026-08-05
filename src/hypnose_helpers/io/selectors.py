"""Forgiving subject/date selector parsing.

Moved verbatim from hypnose-somnotate `io/selectors.py` (restructure_2 Phase 2a), where
it was already unit-tested. Pure parsing -- it knows the shape of an identifier
(`66` / `"066"` / `"sub-066"` / `"66,67"` / a date range), never what the data contains,
so the CLI and the Python API of every repo can agree on what a selector means.
"""

from __future__ import annotations

import re

# A date as it appears in session directory names.
DATE_RE = re.compile(r"^\d{8}$")

# Separators inside a single token: "66,67" and "66;67". Whitespace-separated values
# arrive already split (by the shell, or by argparse nargs="+").
_SPLIT_RE = re.compile(r"[,;\s]+")

# "20260707-20260718" — only valid for ranges, since a bare date never contains a
# hyphen. Kept separate from _SPLIT_RE so "sub-066" is not split on its hyphen.
_RANGE_SPLIT_RE = re.compile(r"[,;\s]+|(?<=\d)-(?=\d)")


def flatten(values) -> list[str]:
    """Split every token on commas/semicolons/whitespace and drop empties."""
    if values is None:
        return []
    if isinstance(values, (str, int)):
        values = [values]
    out: list[str] = []
    for value in values:
        for part in _SPLIT_RE.split(str(value).strip()):
            if part:
                out.append(part)
    return out


def parse_subject(value) -> int:
    """Normalise ONE subject argument to a plain integer.

    Accepts 66, "66", "066", "sub-66" and "sub-066". The scalar form exists because
    `normalize_subjid` and the layout walker want a single subject, and a second
    hand-rolled copy of this rule is how the two would drift apart.
    """
    token = str(value).strip()
    cleaned = token.lower()
    if cleaned.startswith("sub-"):
        cleaned = cleaned[4:]
    if not cleaned.isdigit():
        raise ValueError(
            f"Invalid subject {token!r}; expected a number like 66, 066 or sub-066."
        )
    return int(cleaned)


def parse_subjects(values) -> list[int]:
    """Normalise subject arguments to plain integers.

    Accepts 66, "66", "066", "sub-066", and any comma/space separated combination of
    those. Integers are returned because that is what `find_recordings` and
    `save_figure` both want. Duplicates removed, first-appearance order preserved.
    """
    subjects: list[int] = []
    for token in flatten(values):
        subject = parse_subject(token)
        if subject not in subjects:
            subjects.append(subject)
    return subjects


def _parse_ints(values, *, prefix: str | None, label: str, example: str) -> list[int]:
    """Shared body for the integer selectors. Duplicates removed, order preserved."""
    out: list[int] = []
    for token in flatten(values):
        cleaned = token.lower()
        if prefix and cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
        if not cleaned.isdigit():
            raise ValueError(f"Invalid {label} {token!r}; expected a number like {example}.")
        number = int(cleaned)
        if number not in out:
            out.append(number)
    return out


def _parse_int_range(value, *, parse, label: str, example: str) -> tuple[int, int] | None:
    """Shared body for the integer ranges. Bounds are sorted, as `parse_date_range` does."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)) and len(value) == 2:
        parts = [str(v).strip() for v in value]
    else:
        parts = [p for p in _RANGE_SPLIT_RE.split(str(value).strip()) if p]

    if len(parts) != 2:
        raise ValueError(
            f"Invalid {label} range {value!r}; expected START,END or START-END "
            f"(e.g. {example})."
        )
    start, end = sorted(parse([p])[0] for p in parts)
    return start, end


def parse_sessions(values) -> list[int]:
    """Normalise session arguments to plain integers.

    Accepts 3, "3", "03", "ses-03", and any comma/space separated combination. `ses`
    is an identifier rather than an ordinal (it has gaps and is occasionally out of
    chronological order), so it is kept as the number written on the directory.
    """
    return _parse_ints(values, prefix="ses-", label="session", example="3, 03 or ses-03")


def parse_session_range(value) -> tuple[int, int] | None:
    """Parse an inclusive session range into (start, end).

    Accepts "03-09", "3,9" and a 2-element sequence.
    """
    return _parse_int_range(value, parse=parse_sessions, label="session",
                            example="3,9 or 03-09")


def parse_indices(values) -> list[int]:
    """Normalise session-*index* arguments to plain integers.

    The index is the subject's gap-free chronological rank (1..N), not the number in
    the directory name -- so unlike `parse_sessions` a ``ses-`` prefix is not accepted
    here. Mixing the two up is the whole reason they are separate selectors: for a
    subject whose numbering carried over from an earlier protocol, `ses` 1-9 selects
    nothing while index 1-9 selects its first nine sessions.
    """
    return _parse_ints(values, prefix=None, label="session index", example="1 or 9")


def parse_index_range(value) -> tuple[int, int] | None:
    """Parse an inclusive session-index range into (start, end)."""
    return _parse_int_range(value, parse=parse_indices, label="session index",
                            example="1,9 or 1-9")


def parse_dates(values) -> list[str]:
    """Normalise date arguments to a list of YYYYMMDD strings.

    Strings rather than ints, because that is the form session directories and
    `find_recordings` use. Duplicates removed, first-appearance order preserved.
    """
    dates: list[str] = []
    for token in flatten(values):
        if not DATE_RE.match(token):
            raise ValueError(f"Invalid date {token!r}; expected YYYYMMDD (e.g. 20260707).")
        if token not in dates:
            dates.append(token)
    return dates


def parse_date_range(value) -> tuple[str, str] | None:
    """Parse an inclusive date range into (start, end).

    Accepts "20260707,20260718", "20260707-20260718", and a 2-element sequence. The
    bounds are sorted, so an inverted range still selects the intended span.
    """
    if value is None:
        return None
    if isinstance(value, (list, tuple)) and len(value) == 2:
        parts = [str(v).strip() for v in value]
    else:
        parts = [p for p in _RANGE_SPLIT_RE.split(str(value).strip()) if p]

    if len(parts) != 2:
        raise ValueError(
            f"Invalid date range {value!r}; expected START,END or START-END "
            "(e.g. 20260707,20260718 or 20260707-20260718)."
        )
    for part in parts:
        if not DATE_RE.match(part):
            raise ValueError(f"Invalid date {part!r} in range {value!r}; expected YYYYMMDD.")
    start, end = sorted(parts)
    return start, end
