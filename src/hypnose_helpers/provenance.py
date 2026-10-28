"""`backstamp.provenance` under its `hypnose_helpers` import path.

- The module replaces itself in `sys.modules`, so this name *is* `backstamp.provenance`.
  Setting a constant through it (``MAX_CHAIN``, as `qc/figure_provenance.py --break-chain`
  does) reaches the code that reads it; a star re-export would set a copy.
"""
import importlib
import sys

sys.modules[__name__] = importlib.import_module("backstamp.provenance")
