"""Modality-agnostic helpers shared across the Hypnose repos.

What belongs here is decided by one test:

    Does it know what the data *is*, or only where it lives and what format it's in?

    Knows the data (harp streams, odors, trials, EDF channels, sleep stages)  -> modality repo
    Knows only layout/format (sub-XXX/ dirs, parquet-vs-CSV, JSON, figure styles) -> here

**This package imports nothing from the rest of the family.** Strictly one-way:
hypnose-behavior-analysis and hypnose-somnotate depend on this; it depends on neither.
The first time that is violated you get an import cycle, and the second consumer is the
one that discovers it.
"""

__version__ = "0.1.0"
