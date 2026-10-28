"""A saved figure's provenance record as a dict, for callers that import it from here.

- `backstamp.read` returns the same record as a `backstamp.Record`.
"""
from backstamp import read


def read_figure_metadata(path) -> dict:
    """``backstamp.read(path).to_dict()``: the record with its ``status`` and ``title``."""
    return read(path).to_dict()
