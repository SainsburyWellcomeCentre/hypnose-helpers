"""Generic serialisation for saving tables and metadata.

Moved from hypnose-behavior-analysis `io/save_results.py` (restructure_2 Phase 2a).
These know only *formats* -- numpy/pandas scalars, timestamps, Paths, and which
DataFrame columns hold nested objects -- never what the values mean, so every repo in
the family can save with the same conventions.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from datetime import datetime, date

import numpy as np
import pandas as pd


def _json_safe(obj):
    """Recursively convert objects to JSON-friendly types."""
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_json_safe(x) for x in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        f = float(obj)
        return None if np.isnan(f) else f
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (pd.Timestamp, datetime, date)):
        return obj.isoformat()
    if hasattr(obj, "isoformat"):
        try:
            return obj.isoformat()
        except Exception:
            pass
    try:
        import pandas as _pd
        if isinstance(obj, _pd.Timedelta):
            return obj.total_seconds()
    except Exception:
        pass
    if isinstance(obj, Path):
        return str(obj)
    return obj

def _json_default(o):
    if isinstance(o, (pd.Timestamp, )):
        return o.isoformat()
    if hasattr(o, "isoformat"):
        try:
            return o.isoformat()
        except Exception:
            pass
    if isinstance(o, (set, tuple)):
        return list(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        f = float(o)
        return None if np.isnan(f) else f
    if isinstance(o, (np.ndarray,)):
        return o.tolist()
    return str(o)

def _normalize_df_for_io(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    JSON-encode object columns containing dict/list/tuple/set/ndarray.
    Returns (normalized_df, jsonified_columns).
    """
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return df, []
    df2 = df.copy()
    json_cols = []

    def _is_nullish(v):
        if v is None:
            return True
        try:
            if isinstance(v, (float, np.floating)):
                return math.isnan(float(v))
        except Exception:
            pass
        return False

    def _json_default_local(o):
        try:
            return _json_default(o)
        except NameError:
            return _json_safe(o)

    for col in df2.columns:
        if df2[col].dtype == "object":
            sample = df2[col].dropna().head(10).tolist()
            needs_json = any(isinstance(v, (dict, list, tuple, set, np.ndarray)) for v in sample)
            if needs_json:
                json_cols.append(col)
                df2[col] = df2[col].apply(
                    lambda v: (None if _is_nullish(v) else json.dumps(v, default=_json_default_local))
                )
    return df2, json_cols
