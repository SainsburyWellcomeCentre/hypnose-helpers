"""Data-location resolution: profiles, env-var overrides, and the resolved roots.

The *mechanism* is shared across the family; the *contents* are per-dataset. So this
module owns the format, the precedence rules and the active-profile selection, while
each consumer supplies its own config directory:

    from hypnose_helpers.io.paths import DataLocations
    _loc = DataLocations(config_dir=REPO_ROOT / "configs", data_root=REPO_ROOT / "data")
    get_rawdata_root = _loc.get_rawdata_root

Deliberately a class parameterised by ``config_dir`` rather than module-level functions
plus a ``configure()`` call: the config directory cannot be derived from ``__file__``
once this lives in a shared package, and import-order-dependent global state is exactly
how a second consumer silently gets the wrong data root.

Resolution order for every root (highest priority first):

1. ``{env_prefix}_*`` environment variables -- deliberate override for CI, a test
   sandbox, or a one-off.
2. the active data-location profile -- ``data_locations.yml`` holds the shared profiles,
   the git-ignored ``data_locations.local.yml`` selects which one is active per machine.
3. the legacy ``data/rawdata`` symlink layout under ``data_root``.
"""
from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

RAW_SUBDIR = "rawdata"
DERIV_SUBDIR = "derivatives"

PROFILES_FILENAME = "data_locations.yml"
LOCAL_FILENAME = "data_locations.local.yml"


def env_path(var_name: str) -> Path | None:
    """A path from an environment variable, with ``~`` and ``$VAR`` expanded, or None."""
    val = os.getenv(var_name)
    if not val:
        return None
    return Path(os.path.expanduser(os.path.expandvars(val)))


def read_yaml(path: Path) -> dict:
    """Parse a YAML mapping, returning {} if absent -- but WARN rather than fail silently.

    A config file that exists is a statement of intent. Silently ignoring an unreadable
    one and falling back to the legacy symlink is precisely the surprise this system
    exists to prevent, so every non-absent failure is warned about.
    """
    if not path.exists():
        return {}
    try:
        import yaml  # lazy: keep this module importable even where yaml is unavailable
    except Exception:
        import warnings
        warnings.warn(
            f"pyyaml is unavailable, so the data-location config '{path.name}' is being "
            f"IGNORED (falling back to the legacy symlink). Are you in the project conda env?",
            stacklevel=2,
        )
        return {}
    try:
        return yaml.safe_load(path.read_text()) or {}
    except Exception as e:
        import warnings
        warnings.warn(f"could not read data-location config '{path}': {e}", stacklevel=2)
        return {}


class DataLocations:
    """Resolves dataset roots for one consumer repo.

    Parameters
    ----------
    config_dir
        Directory holding ``data_locations.yml`` and ``data_locations.local.yml``.
    data_root
        Fallback dataset root for the legacy symlink layout (``<data_root>/rawdata``),
        used only when no env var and no active profile apply.
    env_prefix
        Prefix for the override variables, i.e. ``{prefix}_DATA_ROOT``,
        ``{prefix}_RAWDATA_ROOT``, ``{prefix}_SERVER_ROOT``, ``{prefix}_DERIVATIVES_ROOT``.
        Lets a second dataset in the same process resolve independently.
    """

    def __init__(self, config_dir, data_root, *, env_prefix: str = "HYPNOSE") -> None:
        self._config_dir = Path(config_dir)
        self._data_root_default = Path(data_root)
        self._env_prefix = env_prefix

    # --- config files -------------------------------------------------------

    @property
    def config_dir(self) -> Path:
        return self._config_dir

    def _profiles_path(self) -> Path:
        """Committed file with the shared profiles (server-mac, server-windows, local_*, ...)."""
        return self._config_dir / PROFILES_FILENAME

    def _local_path(self) -> Path:
        """Per-machine, git-ignored file selecting the `active` profile."""
        return self._config_dir / LOCAL_FILENAME

    def _env(self, suffix: str) -> Path | None:
        return env_path(f"{self._env_prefix}_{suffix}")

    # --- profiles -----------------------------------------------------------

    def load_profiles(self) -> dict:
        """Return {profile_name: {'rawdata': ..., 'derivatives': ...}} from the committed config."""
        return read_yaml(self._profiles_path()).get("profiles", {}) or {}

    def get_active(self) -> str | None:
        """The active profile name: the per-machine local override, else the committed default."""
        active = read_yaml(self._local_path()).get("active")
        if active:
            return active
        return read_yaml(self._profiles_path()).get("default_active")

    def set_active(self, name: str) -> None:
        """Write the active profile to the git-ignored local config."""
        import yaml
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._local_path().write_text(
            "# Per-machine data-location selection (git-ignored). Set via set_data_location.\n"
            + yaml.safe_dump({"active": name}, sort_keys=False)
        )

    def _active_profile(self) -> dict | None:
        """Resolved active profile: {'name', 'rawdata', 'derivatives'} or None.
        `derivatives` defaults to the sibling of `rawdata` when not given explicitly."""
        name = self.get_active()
        if not name:
            return None
        prof = self.load_profiles().get(name)
        if not isinstance(prof, dict) or not prof.get("rawdata"):
            return None
        raw = str(prof["rawdata"])
        deriv = prof.get("derivatives") or str(Path(raw).parent / DERIV_SUBDIR)
        return {"name": name, "rawdata": raw, "derivatives": str(deriv)}

    def reload(self) -> None:
        """Clear cached lookups so a changed config (or env var) is picked up in a running
        process. Call after `set_active` in a live kernel."""
        for fn in (self.get_rawdata_root, self.get_server_root, self.get_derivatives_root):
            try:
                fn.cache_clear()
            except Exception:
                pass

    # --- resolved roots -----------------------------------------------------

    def get_data_root(self) -> Path:
        env_root = self._env("DATA_ROOT")
        return env_root if env_root is not None else self._data_root_default

    @lru_cache
    def get_rawdata_root(self) -> Path:
        env_root = self._env("RAWDATA_ROOT")
        if env_root is not None:
            return env_root.resolve(strict=False)
        prof = self._active_profile()
        if prof is not None:
            return Path(prof["rawdata"]).resolve(strict=False)
        return (self.get_data_root() / RAW_SUBDIR).resolve(strict=False)  # legacy symlink fallback

    @lru_cache
    def get_server_root(self) -> Path:
        env_root = self._env("SERVER_ROOT")
        if env_root is not None:
            return env_root.resolve(strict=False)
        rawdata_root = self.get_rawdata_root()
        return rawdata_root.parent if rawdata_root.name == RAW_SUBDIR else rawdata_root

    @lru_cache
    def get_derivatives_root(self) -> Path:
        env_root = self._env("DERIVATIVES_ROOT")
        if env_root is not None:
            return env_root.resolve(strict=False)
        prof = self._active_profile()
        if prof is not None:
            return Path(prof["derivatives"]).resolve(strict=False)
        server_root = self.get_server_root()
        deriv = server_root / DERIV_SUBDIR
        if deriv.exists():
            return deriv
        # fallback for local-only layouts
        return (self.get_data_root() / DERIV_SUBDIR).resolve(strict=False)
