"""Where data lives and what format it is in -- never what it contains.

Planned modules (populated during restructure_2 Phase 2a):

    paths.py      data-location profiles: load_profiles, get_active, set_active,
                  get_rawdata_root, get_server_root, get_derivatives_root
    layout.py     sub-XXX_id-*/ses-YY_date-YYYYMMDD walking; find_sessions() and
                  session_index() (Phase 2b)
    selectors.py  forgiving subject/date parsing: 66 / "066" / "sub-066" / "66,67"
    serialize.py  generic JSON/DataFrame normalisation for saving
    tables.py     parquet-vs-CSV dispatch
"""
