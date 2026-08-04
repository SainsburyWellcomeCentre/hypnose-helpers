"""Where data lives and what format it is in -- never what it contains.

Modules:

    paths.py      data-location profiles: load_profiles, get_active, set_active,
                  get_rawdata_root, get_server_root, get_derivatives_root
    layout.py     sub-XXX_id-*/ses-YY_date-YYYYMMDD walking: SessionLayout.find_sessions(),
                  .session_index(), normalize_subjid()
    selectors.py  forgiving subject/session/date parsing: 66 / "066" / "sub-066" / "66,67"
    serialize.py  generic JSON/DataFrame normalisation for saving

Still planned:

    tables.py     parquet-vs-CSV dispatch
"""
