#!/usr/bin/env python
"""Select the active data location (rawdata / derivatives roots) for this machine.

Profiles live in a repo's committed `configs/data_locations.yml`. This writes your
choice to `configs/data_locations.local.yml` (git-ignored), which that repo's
`io.paths` reads — so the selection persists across kernels / terminals / reboots and is
never committed.

One CLI serves every repo in the family; `--config-dir` says which repo's profiles to
act on, and `--env-prefix` matches that repo's override variables.

Usage
-----
  hypnose-set-data-location server-mac                 # activate a profile
  hypnose-set-data-location --show                     # print the resolved roots
  hypnose-set-data-location --list                     # list available profiles
  hypnose-set-data-location --config-dir path/to/configs --env-prefix HYPNOSE_EEG --show

Note: a running kernel caches the paths — after switching, restart the kernel or call
that repo's `io.paths.reload()`. Terminal runs pick up the new choice automatically.
Any `<PREFIX>_*` env var still overrides this (that's how the QC sandbox / CI work).
"""
from __future__ import annotations

import os
import sys
import argparse
from pathlib import Path

from hypnose_helpers.io.paths import DataLocations

_ENV_SUFFIXES = ["RAWDATA_ROOT", "DERIVATIVES_ROOT", "SERVER_ROOT", "DATA_ROOT"]


def _env_vars(prefix: str) -> list[str]:
    return [f"{prefix}_{s}" for s in _ENV_SUFFIXES]


def _report_env_overrides(prefix: str) -> None:
    """If any override env var is set, flag it and print the OS-correct removal commands.
    (A script can't unset the parent shell's env, so we tell you exactly what to run.)"""
    set_vars = {v: os.environ[v] for v in _env_vars(prefix) if os.environ.get(v)}
    if not set_vars:
        return
    print(f"\n  ⚠ {prefix}_* environment variable(s) are set and take precedence over the active profile:")
    for v, val in set_vars.items():
        print(f"      {v} = {val}")
    print("  Remove them so the profile drives the paths (a script can't unset your shell's env):")
    if sys.platform.startswith("win"):
        print("    # this session:")
        for v in set_vars:
            print(f"      Remove-Item Env:{v} -ErrorAction SilentlyContinue")
        print("    # permanently (User scope) — then restart the shell / fully restart VS Code:")
        for v in set_vars:
            print(f'      [Environment]::SetEnvironmentVariable("{v}", $null, "User")')
    else:
        print("    # this session:")
        print("      unset " + " ".join(set_vars))
        print("    # permanently: delete the matching 'export ...' lines from ~/.zshrc / ~/.bashrc")
    print("    (then re-run --show to confirm)")


def _print_resolved(loc: DataLocations, prefix: str) -> None:
    loc.reload()
    active = loc.get_active()
    raw = loc.get_rawdata_root()
    print(f"  config dir     : {loc.config_dir}")
    print(f"  active profile : {active or '(none — using legacy symlink/fallback)'}")
    print(f"  rawdata        : {raw}      {'OK' if raw.exists() else 'MISSING ⚠'}")
    print(f"  server         : {loc.get_server_root()}")
    print(f"  derivatives    : {loc.get_derivatives_root()}")
    if not raw.exists():
        print("  ⚠ rawdata path does not exist — wrong profile for this machine, or the drive/mount is not available.")
    if active and any(os.environ.get(v) for v in _env_vars(prefix)[:3]):
        print("  ⚠ an env var is overriding your selected profile (see below).")
    _report_env_overrides(prefix)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("profile", nargs="?", help="profile name to activate (see --list)")
    ap.add_argument("--show", action="store_true", help="print the currently resolved data roots")
    ap.add_argument("--list", action="store_true", help="list available profiles")
    ap.add_argument("--config-dir", default="configs", type=Path,
                    help="directory holding data_locations.yml (default: ./configs)")
    ap.add_argument("--env-prefix", default="HYPNOSE",
                    help="prefix of the override env vars (default: HYPNOSE; EEG uses HYPNOSE_EEG)")
    args = ap.parse_args(argv)

    config_dir = args.config_dir.resolve()
    if not config_dir.is_dir():
        print(f"No config directory at {config_dir}. Run this from a repo root, or pass --config-dir.")
        return 1

    # data_root only matters for the legacy symlink fallback, which is repo-relative.
    loc = DataLocations(config_dir=config_dir, data_root=config_dir.parent / "data",
                        env_prefix=args.env_prefix)
    profiles = loc.load_profiles()

    if args.list:
        active = loc.get_active()
        if not profiles:
            print(f"No profiles found in {config_dir / 'data_locations.yml'}.")
            return 1
        print("Available data-location profiles:")
        for name, prof in profiles.items():
            mark = " (active)" if name == active else ""
            print(f"  - {name}{mark}: rawdata={prof.get('rawdata')}")
        return 0

    if args.show:
        print("Resolved data location:")
        _print_resolved(loc, args.env_prefix)
        return 0

    if not args.profile:
        ap.error("give a profile name to activate, or use --show / --list")
    if args.profile not in profiles:
        print(f"Unknown profile '{args.profile}'. Available: {', '.join(profiles) or '(none)'}")
        return 1

    loc.set_active(args.profile)
    print(f"Active data location set to '{args.profile}' (written to {loc._local_path()}).")
    _print_resolved(loc, args.env_prefix)
    print("\n(If a Jupyter kernel is running, restart it or call that repo's io.paths.reload() to pick this up.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
