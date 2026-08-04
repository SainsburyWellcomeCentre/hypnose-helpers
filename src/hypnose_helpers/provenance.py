"""What produced this output: commit, version, and the call that made it.

A figure or a results file that cannot be traced back to the code that made it is a
figure you have to reproduce from scratch before you can trust it. This module builds a
small, JSON-safe record answering "which code, which version, called how" -- embedded in
saved PDFs (`viz.metadata`) and, from Phase 7, in `manifest.json` as well. One
implementation, so the two cannot drift.

**Anchoring, and why there is no default.** `git_commit()` takes the path of the code
whose commit you want. It must be the *caller's* file: hypnose-helpers is installed as a
library, so anchoring on ``__file__`` here would stamp every figure from every repo with
the helpers commit -- plausible-looking and wrong, the same silent-resolution failure
that `io/paths` hit in restructure_2 Phase 2a and `io/layout` in 2b. `capture_call()`
finds the calling frame, and `provenance()` anchors on its file.

Nothing here raises. Provenance is a nice-to-have attached to real work, so a detached
HEAD, a missing `git`, an unreadable frame or an exotic argument type degrades to a
`None` field or a `<TypeName>` placeholder -- never a failed save.
"""
from __future__ import annotations

import inspect
import subprocess
from datetime import datetime
from pathlib import Path

# Truncation limits. The PDF info dictionary is not a database: the record has to stay
# small enough to sit in one string value, so containers are sampled rather than stored.
MAX_ITEMS = 10
MAX_STR = 80
MAX_PARAMS = 15

# Frames belonging to the saving machinery itself, never the answer to "who plotted this".
_SKIP_MODULES = (
    "hypnose_helpers.provenance",
    "hypnose_helpers.viz.save",
    "hypnose_helpers.viz.metadata",
)

_GIT_TIMEOUT = 5


# --- git ------------------------------------------------------------------


def _git(args, cwd) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True,
            timeout=_GIT_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def git_commit(anchor) -> str | None:
    """Short commit of the repo containing ``anchor``, ``-dirty`` if it has changes.

    ``anchor`` is a file or directory *inside the repo you want described* -- see the
    module docstring on why this has no default.

    The dirty suffix is not decoration: a bare hash on a modified tree points at code
    that is not what ran, which is worse than recording nothing.
    """
    if anchor is None:
        return None
    anchor = Path(anchor)
    cwd = anchor.parent if anchor.is_file() else anchor
    if not cwd.exists():
        return None

    commit = _git(["rev-parse", "--short", "HEAD"], cwd)
    if not commit:
        return None
    # `git status` can be slow on a large tree; this is the cheap equivalent that still
    # sees both tracked modifications and untracked files.
    status = _git(["status", "--porcelain", "--untracked-files=normal"], cwd)
    return f"{commit}-dirty" if status else commit


def package_version(module_name: str | None) -> str | None:
    """Installed version of the distribution providing ``module_name``'s top package.

    The import package and the distribution are routinely named differently -- this
    family ships `hypnose_behavior` from `hypnose-behavior-analysis` -- so guessing by
    swapping underscores for hyphens finds nothing. `packages_distributions()` is the
    real mapping; the guess is only a fallback for Python 3.9, which lacks it.
    """
    if not module_name:
        return None
    root = module_name.split(".")[0]
    try:
        from importlib.metadata import PackageNotFoundError, version
    except Exception:
        return None

    try:
        from importlib.metadata import packages_distributions

        for dist in packages_distributions().get(root, ()):
            try:
                return version(dist)
            except PackageNotFoundError:
                continue
    except ImportError:
        pass  # Python 3.9

    for candidate in (root, root.replace("_", "-")):
        try:
            return version(candidate)
        except Exception:
            continue
    return None


# --- value summarising ----------------------------------------------------


def summarize_value(value, *, max_items: int = MAX_ITEMS, max_str: int = MAX_STR):
    """Render one call argument as something small and JSON-safe.

    Scalars pass through, strings truncate, containers are sampled, and arrays and
    frames become shape descriptors (``<DataFrame 50x2>``) rather than being serialised
    -- the point is to recognise the call later, not to reconstruct its inputs.
    """
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        # Guard against NaN/inf, which are not valid JSON.
        return value if value == value and abs(value) != float("inf") else str(value)
    if isinstance(value, str):
        return value if len(value) <= max_str else value[: max_str - 3] + "..."
    if isinstance(value, Path):
        return summarize_value(str(value), max_str=max_str)

    described = _describe_scientific(value)
    if described is not None:
        return described

    if isinstance(value, dict):
        out = {
            str(k): summarize_value(v, max_items=max_items, max_str=max_str)
            for k, v in list(value.items())[:max_items]
        }
        if len(value) > max_items:
            out["..."] = f"+{len(value) - max_items} more"
        return out
    if isinstance(value, (list, tuple, set, frozenset)):
        items = list(value)
        out = [summarize_value(v, max_items=max_items, max_str=max_str)
               for v in items[:max_items]]
        if len(items) > max_items:
            out.append(f"...+{len(items) - max_items} more")
        return out

    return f"<{type(value).__name__}>"


def _describe_scientific(value) -> str | None:
    """Shape descriptors for pandas/numpy/matplotlib objects, without importing them.

    Dispatching on the type's module keeps this module importable (and fast) in an
    environment where numpy or matplotlib is absent, and avoids paying an import just to
    describe an argument.
    """
    module = type(value).__module__.split(".")[0]
    name = type(value).__name__

    if module == "pandas":
        if name == "DataFrame":
            try:
                return f"<DataFrame {value.shape[0]}x{value.shape[1]}>"
            except Exception:
                return "<DataFrame>"
        if name == "Series":
            try:
                return f"<Series {len(value)} {value.dtype}>"
            except Exception:
                return "<Series>"
    if module == "numpy" and name == "ndarray":
        try:
            return f"<ndarray {tuple(value.shape)} {value.dtype}>"
        except Exception:
            return "<ndarray>"
    if module == "matplotlib":
        return f"<{name}>"
    return None


# --- the calling frame ----------------------------------------------------


def capture_call(*, skip_modules=(), max_params: int = MAX_PARAMS) -> dict | None:
    """Describe the nearest frame that is not saving machinery.

    Returns ``{"function", "file", "lineno", "params"}``, where ``params`` covers the
    named arguments *and* anything that arrived via ``**kwargs``.

    Frame-walking is inherently fragile -- a thin plotting primitive added later may sit
    between the real caller and this call, and the answer silently becomes the
    primitive. Extend ``skip_modules``, or pass an explicit record to `save_figure`,
    whenever the answer matters. That is why the override exists.
    """
    skip = set(_SKIP_MODULES) | set(skip_modules)
    try:
        stack = inspect.stack()
    except Exception:
        return None
    try:
        for entry in stack[1:]:
            module = entry.frame.f_globals.get("__name__", "")
            if module in skip or module.startswith(("importlib", "runpy")):
                continue
            return {
                "function": entry.function,
                "module": module,
                "file": Path(entry.filename).name,
                "path": entry.filename,
                "lineno": entry.lineno,
                "params": _frame_params(entry.frame, max_params),
            }
    except Exception:
        return None
    finally:
        # inspect.stack() holds frame references; dropping them promptly keeps large
        # plotting locals from being kept alive by a reference cycle.
        del stack
    return None


def _frame_params(frame, max_params: int) -> dict:
    try:
        info = inspect.getargvalues(frame)
    except Exception:
        return {}
    params: dict = {}
    for name in info.args:
        if name in ("self", "cls"):
            continue
        params[name] = summarize_value(info.locals.get(name))
    if info.keywords:  # the **kwargs catch-all: record what was actually passed
        for name, value in (info.locals.get(info.keywords) or {}).items():
            params[str(name)] = summarize_value(value)
    if len(params) > max_params:
        kept = dict(list(params.items())[:max_params])
        kept["..."] = f"+{len(params) - max_params} more"
        return kept
    return params


# --- the record -----------------------------------------------------------


def provenance(*, anchor=None, call: dict | None = None, extra: dict | None = None,
               skip_modules=()) -> dict:
    """A record of what produced this output.

    ``call`` is a `capture_call` result; when omitted, one is captured here. ``anchor``
    defaults to the calling code's own file, so the commit describes the repo that ran
    rather than whichever repo happens to host this function.

    ``skip_modules`` is forwarded to `capture_call`. A repo whose own ``save_figure`` is
    a thin wrapper **must** pass its module name, or the capture names the wrapper
    instead of the plotting function that called it.
    """
    if call is None:
        call = capture_call(skip_modules=skip_modules)
    if anchor is None and call is not None:
        anchor = call.get("path")

    record = {
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "commit": git_commit(anchor),
        "version": package_version(call.get("module") if call else None),
    }
    if call is not None:
        record.update(
            {k: call[k] for k in ("function", "module", "file", "lineno", "params")
             if k in call}
        )
    if extra:
        record.update(extra)
    return {k: v for k, v in record.items() if v is not None}


__all__ = [
    "provenance", "git_commit", "package_version", "summarize_value", "capture_call",
    "MAX_ITEMS", "MAX_STR", "MAX_PARAMS",
]
