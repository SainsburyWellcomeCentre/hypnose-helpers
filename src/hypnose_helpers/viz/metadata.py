"""`backstamp.metadata` under its `hypnose_helpers` import path.

- The module replaces itself in `sys.modules`, so this name *is* `backstamp.metadata`,
  private helpers and constants included.
"""
import importlib
import sys

sys.modules[__name__] = importlib.import_module("backstamp.metadata")
