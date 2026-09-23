"""Shared argparse flags for picking subjects, sessions and dates.

Every spelling someone might reach for selects the same thing, so nobody has to
remember which script wants ``--sub`` and which ``--subjids``:

    subjects      -s  --sub --subs --subj --subject --subjects --subjid --subjids
    dates         -d  --date --dates
    date range        --date-range --dates-range
    sessions          --ses --session --sessions
    session range     --ses-range --session-range
    index             --index            (opt-in: ``index=True``)
    index range       --index-range      (opt-in)

- Every long flag also works with a single dash (``-sub``, ``-ses``, ``-date-range``);
  ``-h`` lists only the double-dash forms.
- Values may be space- or comma-separated and zero-padded: ``60 61``, ``60,61``,
  ``060 061``, ``sub-060``.
- Ranges take ``START END``, ``START-END`` or ``START,END``.
- Values are parsed here with `hypnose_helpers.io.selectors`, so a typo fails at the
  command line rather than mid-run; repeating a list flag appends.
"""

from __future__ import annotations

import argparse

from hypnose_helpers.io.selectors import (
    parse_date_range,
    parse_dates,
    parse_index_range,
    parse_indices,
    parse_session_range,
    parse_sessions,
    parse_subjects,
)

SUBJECT_FLAGS = ("-s", "--sub", "--subs", "--subj", "--subject", "--subjects", "--subjid",
                 "--subjids")
DATE_FLAGS = ("-d", "--date", "--dates")
DATE_RANGE_FLAGS = ("--date-range", "--dates-range")
SES_FLAGS = ("--ses", "--session", "--sessions")
SES_RANGE_FLAGS = ("--ses-range", "--session-range")
INDEX_FLAGS = ("--index",)
INDEX_RANGE_FLAGS = ("--index-range",)


def _with_single_dash(flags) -> list[str]:
    """``--sub`` -> ``--sub``, ``-sub``; one-letter flags are left alone."""
    out: list[str] = []
    for flag in flags:
        out.append(flag)
        if flag.startswith("--"):
            out.append(flag[1:])
    return out


class _ParseAction(argparse.Action):
    """Store `parse(values)`; a list flag given twice accumulates."""

    def __init__(self, option_strings, dest, *, parse, accumulate, **kwargs):
        self._parse = parse
        self._accumulate = accumulate
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        try:
            parsed = self._parse(values)
        except ValueError as exc:
            raise argparse.ArgumentError(self, str(exc)) from None
        previous = getattr(namespace, self.dest, None)
        if self._accumulate and previous:
            parsed = previous + [v for v in parsed if v not in previous]
        setattr(namespace, self.dest, parsed)


def _one_range(parse):
    """A range as one token ("3-9") or two ("3 9")."""
    return lambda values: parse(values[0] if len(values) == 1 else values)


def _add(parser, flags, *, dest, parse, accumulate, metavar, help, required=False):
    if not accumulate:
        parse = _one_range(parse)
    parser.add_argument(
        *_with_single_dash(flags), dest=dest, nargs="+", default=None, metavar=metavar,
        action=_ParseAction, parse=parse, accumulate=accumulate, required=required,
        help=help,
    )


def _compact_help(parser) -> None:
    """List each selector's flags once in ``-h``, without the single-dash copies."""
    base = parser.formatter_class

    class _Compact(base):
        def _format_action_invocation(self, action):
            if not isinstance(action, _ParseAction):
                return super()._format_action_invocation(action)
            flags = [f for f in action.option_strings if f.startswith("--") or len(f) == 2]
            metavar = self._format_args(action, self._get_default_metavar_for_optional(action))
            return f"{', '.join(flags)} {metavar}"

    parser.formatter_class = _Compact


def add_selector_args(
    parser: argparse.ArgumentParser,
    *,
    sessions: bool = True,
    index: bool = False,
    subjects_required: bool = False,
    subjects_help: str = "subject id(s); default: all",
) -> None:
    """Add the subject/date(/session/index) flags to `parser`.

    Parsed values land on the namespace as `subjids` (list[int]), `dates` (list[str]),
    `date_range` (tuple[str, str]), `ses` (list[int]), `ses_range`, `index` and
    `index_range` (ints); an absent flag is ``None``. The selectors intersect.
    """
    _compact_help(parser)
    _add(parser, SUBJECT_FLAGS, dest="subjids", parse=parse_subjects, accumulate=True,
         metavar="ID", required=subjects_required, help=subjects_help)
    _add(parser, DATE_FLAGS, dest="dates", parse=parse_dates, accumulate=True,
         metavar="YYYYMMDD", help="specific date(s)")
    _add(parser, DATE_RANGE_FLAGS, dest="date_range", parse=parse_date_range,
         accumulate=False, metavar="YYYYMMDD", help="inclusive date range: START END")
    if sessions:
        _add(parser, SES_FLAGS, dest="ses", parse=parse_sessions, accumulate=True,
             metavar="SES", help="session number(s) as written in ses-NNN (40, 040, ses-040)")
        _add(parser, SES_RANGE_FLAGS, dest="ses_range", parse=parse_session_range,
             accumulate=False, metavar="SES", help="inclusive ses range: START END")
    if index:
        _add(parser, INDEX_FLAGS, dest="index", parse=parse_indices, accumulate=True,
             metavar="N", help="session index: the subject's gap-free chronological rank, 1..N")
        _add(parser, INDEX_RANGE_FLAGS, dest="index_range", parse=parse_index_range,
             accumulate=False, metavar="N", help="inclusive session-index range: START END")
