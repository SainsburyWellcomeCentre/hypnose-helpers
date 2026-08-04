"""Provenance embedded in the saved PDF itself -- no sidecar, still one file.

Open a figure months later and recover what it shows and how it was made, from the file
you are already looking at. A sidecar JSON solves the same problem right up until
someone emails the PDF on its own.

**The constraint that shapes this** (verified against the matplotlib PDF backend): the
PDF info dictionary accepts only ``Title``, ``Author``, ``Subject``, ``Keywords``,
``Creator``, ``Producer``, ``CreationDate``, ``ModDate`` and ``Trapped``. Any other key
is dropped with a ``UserWarning``, and ``CreationDate`` must be a real ``datetime``. So
the structured record goes into ``Subject`` as JSON, with a human-readable one-liner in
``Title`` -- the field a PDF viewer shows without being asked.

Reading needs no dependency. `pypdf` is used when installed, but matplotlib writes the
info dictionary as an uncompressed literal string, so the stdlib fallback recovers it
too. Provenance that can only be read by installing something extra is provenance nobody
reads.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from ..provenance import provenance as _provenance

# A PDF string value has to stay a reasonable size; beyond this the record is truncated
# rather than risking an unwieldy info dictionary.
MAX_BLOB = 3000

# The keys matplotlib will accept. Anything else is silently discarded, so filter here
# rather than letting a warning appear at every save.
_ALLOWED = frozenset({
    "Title", "Author", "Subject", "Keywords", "Creator", "Producer",
    "CreationDate", "ModDate", "Trapped",
})


def summarize_scope(save_name: str, subjids=None, dates=None) -> str:
    """The one-line human summary that lands in ``Title``.

    e.g. ``"accuracy sub-040,045,066 20251124-20260203"``.
    """
    parts = [save_name] if save_name else []
    subj = _as_list(subjids)
    date = _as_list(dates)
    if subj:
        parts.append("sub-" + ",".join(_fmt_subj(s) for s in subj))
    if date:
        dates_sorted = sorted(str(d) for d in date)
        parts.append(
            dates_sorted[0] if len(dates_sorted) == 1
            else f"{dates_sorted[0]}-{dates_sorted[-1]}"
        )
    return " ".join(parts)


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set, frozenset)):
        return list(value)
    return [value]


def _fmt_subj(value):
    try:
        return f"{int(value):03d}"
    except (TypeError, ValueError):
        return str(value)


def build_pdf_metadata(save_name: str, *, subjids=None, dates=None,
                       provenance: dict | None = None, call: dict | None = None,
                       extra: dict | None = None) -> dict:
    """The matplotlib ``metadata=`` dict for one figure.

    ``provenance`` overrides capture entirely; otherwise a record is built from ``call``
    (a `capture_call` result) or, failing that, captured here.
    """
    record = provenance if provenance is not None else _provenance(call=call)
    if subjids is not None:
        record.setdefault("subjids", [_fmt_subj(s) for s in _as_list(subjids)])
    if dates is not None:
        record.setdefault("dates", [str(d) for d in _as_list(dates)])
    if extra:
        record.update(extra)

    blob = _dump(record)
    creator = "hypnose"
    if record.get("version"):
        creator = f"{record.get('module', 'hypnose')} {record['version']}"

    return {
        "Title": summarize_scope(save_name, subjids, dates),
        "Subject": blob,
        "Creator": creator,
        "CreationDate": datetime.now(),  # must be a datetime, not a string
    }


def _dump(record: dict) -> str:
    """JSON, ASCII-only, shrunk by dropping the bulkiest field if it will not fit.

    ``ensure_ascii=True`` is load-bearing, not tidiness: matplotlib writes a PDF string
    containing any non-ASCII character as UTF-16BE with a byte-order mark instead of
    latin-1. Keeping the blob ASCII keeps the encoding predictable for every reader.
    """
    blob = json.dumps(record, default=str)
    if len(blob) <= MAX_BLOB:
        return blob
    trimmed = dict(record)
    trimmed["params"] = {"...": "omitted (too large)"}
    blob = json.dumps(trimmed, default=str)
    return blob if len(blob) <= MAX_BLOB else blob[: MAX_BLOB - 3] + "..."


def filter_metadata(metadata: dict) -> dict:
    """Drop keys matplotlib would reject, so saving never emits a UserWarning."""
    return {k: v for k, v in (metadata or {}).items() if k in _ALLOWED}


# --- reading back ---------------------------------------------------------


def read_figure_metadata(path) -> dict:
    """Recover a saved figure's provenance.

    Returns the parsed ``Subject`` record, plus ``_title`` and ``_creator``.

    Yields ``{}`` for a PDF carrying no provenance, an unreadable one, or a missing
    file -- never raises, since this is a diagnostic tool and failing hard on an old
    figure helps nobody. Note the emptiness is deliberate rather than incidental:
    matplotlib stamps every PDF with its own ``Creator``, so returning that alone would
    make ``if not read_figure_metadata(p)`` stop meaning "no provenance here".
    """
    path = Path(path)
    if not path.exists():
        return {}
    info = _read_info_pypdf(path)
    if info is None:
        info = _read_info_stdlib(path)

    subject = (info or {}).get("Subject")
    if not subject:
        return {}

    out: dict = {}
    try:
        parsed = json.loads(subject)
    except (ValueError, TypeError):
        parsed = None
    if isinstance(parsed, dict):
        out.update(parsed)
    else:
        out["_subject"] = subject
    if info.get("Title"):
        out["_title"] = info["Title"]
    if info.get("Creator"):
        out["_creator"] = info["Creator"]
    return out


def _read_info_pypdf(path: Path) -> dict | None:
    try:
        from pypdf import PdfReader
    except Exception:
        return None
    try:
        meta = PdfReader(str(path)).metadata or {}
        return {str(k).lstrip("/"): str(v) for k, v in meta.items()}
    except Exception:
        return None


# `/Subject (....)` where the closing paren is not escaped. matplotlib writes the info
# dictionary uncompressed, so this finds it without a PDF parser.
_ENTRY_RE = r"/{key}\s*\((.*?)(?<!\\)\)"


def _read_info_stdlib(path: Path) -> dict:
    try:
        raw = path.read_bytes()
    except OSError:
        return {}
    info = {}
    for key in ("Title", "Subject", "Creator"):
        match = re.search(_ENTRY_RE.format(key=key).encode(), raw, re.S)
        if match:
            info[key] = _unescape(match.group(1))
    return info


_ESCAPES = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f"}


def _unescape(value: bytes) -> str:
    """Undo PDF literal-string escaping and decode.

    Two things that are easy to get wrong:

    * Unescaping is one left-to-right pass, not a sequence of `str.replace` calls --
      replacing ``\\(`` before ``\\\\`` corrupts a literal backslash preceding a paren.
    * A PDF string holding any non-ASCII character is written as UTF-16BE behind a
      byte-order mark. We keep our own blob ASCII, but a figure saved by other code (or
      by an older version of this one) may not be, so honour the BOM.
    """
    if value[:2] in (b"\xfe\xff", b"\xff\xfe"):
        text = value.decode("utf-16", errors="replace")
    else:
        text = value.decode("utf-8", errors="replace")
    return re.sub(r"\\(.)", lambda m: _ESCAPES.get(m.group(1), m.group(1)), text)


__all__ = [
    "build_pdf_metadata", "read_figure_metadata", "summarize_scope", "filter_metadata",
    "MAX_BLOB",
]
