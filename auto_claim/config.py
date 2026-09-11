"""
config.py — ConfigManager
Loads, validates, and saves all runtime configuration from/to config.json.
Supports Home / Office display profiles for instant layout switching.
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Default configuration — used when a key is missing from config.json
# ---------------------------------------------------------------------------
_DEFAULTS: dict[str, Any] = {
    "monitor_index": 1,
    "table_region": {"left": -1, "top": -1, "width": -1, "height": -1},
    "site_column": {"left": -1, "top": -1, "width": -1, "height": -1},
    "type_column": {"left": -1, "top": -1, "width": -1, "height": -1},
    "alarm_column": {"left": -1, "top": -1, "width": -1, "height": -1},
    "claim_column": {"left": -1, "top": -1, "width": -1, "height": -1},
    "select_column": {"left": -1, "top": -1, "width": -1, "height": -1},
    "connect_button": {"x": -1, "y": -1},
    "username": "",
    "site_blocklist": [],
    "allowed_teleop_types": ["SUSPECT", "CHRF"],
    "max_alarm_time": "10:00",
    "pending_keywords": ["claiming", "aiming", "laiming", "clalming"],
    "pending_match_threshold": 85,
    "ocr": {
        "languages": ["en"],
        "gpu": False,
        "confidence_threshold": 0.4,
        "claim_keyword": "CLAIM",
        "cache_identical_frames": True,
    },
    "timing": {
        "loop_interval_ms": 100,
        "post_click_wait_ms": 500,
        "post_connect_wait_ms": 1000,
        "claim_timeout_s": 5,
        "state_timeout_s": 10,
        "debounce_ms": 500,
    },
    "mouse": {
        "move_duration_s": 0.15,
        "randomize_offset_px": 3,
        "failsafe": True,
    },
    "row_detection": {
        "method": "horizontal_lines",
        "min_row_height_px": 15,
        "max_row_height_px": 60,
        "line_thickness_threshold": 1,
        "use_template_matching": False,
        "template_select_btn": "auto_claim/templates/select_btn.png",
        "template_confidence": 0.80,
    },
    "debug": {
        "enabled": False,
        "overlay_alpha": 0.6,
        "show_fps": True,
        "show_ocr_boxes": True,
        "show_row_boxes": True,
        "show_state": True,
        "save_screenshots_on_error": True,
    },
    "logging": {
        "level": "INFO",
        "log_dir": "auto_claim/logs",
        "screenshot_dir": "auto_claim/screenshots",
        "max_log_files": 7,
        "max_log_size_mb": 10,
    },
}

import sys

def get_base_dir() -> Path:
    """Returns the base directory for the application, handling PyInstaller."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

def _resolve_config_path() -> Path:
    """Look for config.json inside auto_claim/ first, then in root directory."""
    local_cfg = Path(__file__).resolve().parent / "config.json"
    if local_cfg.exists():
        return local_cfg
    root_cfg = get_base_dir() / "config.json"
    if root_cfg.exists():
        return root_cfg
    return local_cfg

# Path resolution: config.json lives inside auto_claim or next to the executable
_DEFAULT_CONFIG_PATH = _resolve_config_path()


class ConfigManager:
    """
    Singleton-style config manager.

    Usage::

        cfg = ConfigManager()           # loads from default path
        cfg = ConfigManager("my.json")  # custom path
        table = cfg.get("table_region")
        cfg.set("username", "alice")
        cfg.save()
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self._path = Path(path) if path else _DEFAULT_CONFIG_PATH
        self._data: dict[str, Any] = deepcopy(_DEFAULTS)
        self.load()

    # ------------------------------------------------------------------
    # I/O
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load config from disk, merging with defaults for missing keys."""
        if self._path.exists():
            with self._path.open("r", encoding="utf-8") as fh:
                on_disk = json.load(fh)
            self._data = self._deep_merge(_DEFAULTS, on_disk)
        else:
            self._data = deepcopy(_DEFAULTS)
            self._data["active_profile"] = "office"
        self._ensure_profiles()
        active_prof = self.get_active_profile()
        profiles = self._data.get("profiles", {})
        if active_prof in profiles:
            self._apply_layout(profiles[active_prof])

    def save(self) -> None:
        """Persist current config to disk (pretty-printed JSON)."""
        active_prof = self.get_active_profile()
        if "profiles" in self._data and active_prof in self._data.get("profiles", {}):
            self._data["profiles"][active_prof] = self._snapshot_layout()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Return a top-level config value (or a nested dict)."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a top-level config value."""
        self._data[key] = value

    def update_nested(self, section: str, updates: dict) -> None:
        """Merge *updates* into a nested config section dict."""
        section_data = self._data.setdefault(section, {})
        section_data.update(updates)

    # Convenience shortcuts --------------------------------------------------

    @property
    def table_region(self) -> dict:
        return self._data["table_region"]

    @property
    def claim_column(self) -> dict:
        return self._data["claim_column"]

    @property
    def select_column(self) -> dict:
        return self._data["select_column"]

    @property
    def site_column(self) -> dict:
        return self._data.get("site_column", {"left": -1, "top": -1, "width": -1, "height": -1})

    @property
    def type_column(self) -> dict:
        return self._data.get("type_column", {"left": -1, "top": -1, "width": -1, "height": -1})

    @property
    def alarm_column(self) -> dict:
        return self._data.get("alarm_column", {"left": -1, "top": -1, "width": -1, "height": -1})

    @property
    def site_blocklist(self) -> list[str]:
        return self._data.get("site_blocklist", [])

    @property
    def allowed_teleop_types(self) -> list[str]:
        return self._data.get("allowed_teleop_types", ["SUSPECT", "CHRF"])

    @property
    def max_alarm_time(self) -> str:
        return self._data.get("max_alarm_time", "10:00")

    @property
    def pending_keywords(self) -> list[str]:
        return self._data.get("pending_keywords", ["claiming", "aiming", "laiming", "clalming"])

    @property
    def pending_match_threshold(self) -> int:
        return int(self._data.get("pending_match_threshold", 85))

    @property
    def connect_button(self) -> dict:
        return self._data["connect_button"]

    @property
    def username(self) -> str:
        return self._data.get("username", "")

    @property
    def ocr_cfg(self) -> dict:
        return self._data["ocr"]

    @property
    def timing(self) -> dict:
        return self._data["timing"]

    @property
    def mouse_cfg(self) -> dict:
        return self._data["mouse"]

    @property
    def row_detection(self) -> dict:
        return self._data["row_detection"]

    @property
    def debug_cfg(self) -> dict:
        return self._data["debug"]

    @property
    def logging_cfg(self) -> dict:
        return self._data["logging"]

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def is_calibrated(self) -> bool:
        """Return True if at minimum the table_region has been set."""
        tr = self._data["table_region"]
        return tr.get("left", -1) >= 0 and tr.get("width", -1) > 0

    # ------------------------------------------------------------------
    # Profile API
    # ------------------------------------------------------------------

    # Keys that are layout/calibration-specific and belong inside a profile
    _PROFILE_KEYS: tuple[str, ...] = (
        "monitor_index",
        "table_region",
        "site_column",
        "type_column",
        "alarm_column",
        "claim_column",
        "select_column",
        "connect_button",
        "status_window_x",
        "status_window_y",
    )

    def _snapshot_layout(self) -> dict:
        """Capture current calibration/layout keys for a profile snapshot."""
        return {k: deepcopy(self._data[k]) for k in self._PROFILE_KEYS if k in self._data}

    def _apply_layout(self, snap: dict) -> None:
        """Write profile snapshot back into live _data."""
        for k in self._PROFILE_KEYS:
            if k in snap:
                self._data[k] = deepcopy(snap[k])

    def _ensure_profiles(self) -> None:
        """Ensure 'home' and 'office' profiles exist (run once after load)."""
        profiles = self._data.setdefault("profiles", {})
        if "active_profile" not in self._data:
            self._data["active_profile"] = "office"
        if "office" not in profiles:
            profiles["office"] = self._snapshot_layout()
        if "home" not in profiles:
            # Home starts as a blank (uncalibrated) copy
            blank: dict = {
                "monitor_index": self._data.get("monitor_index", 1),
                "table_region":  {"left": -1, "top": -1, "width": -1, "height": -1},
                "site_column":   {"left": -1, "top": -1, "width": -1, "height": -1},
                "type_column":   {"left": -1, "top": -1, "width": -1, "height": -1},
                "alarm_column":  {"left": -1, "top": -1, "width": -1, "height": -1},
                "claim_column":  {"left": -1, "top": -1, "width": -1, "height": -1},
                "select_column": {"left": -1, "top": -1, "width": -1, "height": -1},
                "connect_button": {"x": -1, "y": -1},
                "status_window_x": self._data.get("status_window_x", 100),
                "status_window_y": self._data.get("status_window_y", 100),
            }
            profiles["home"] = blank

    def list_profiles(self) -> list[str]:
        """Return list of saved profile names, e.g. ['home', 'office']."""
        return list(self._data.get("profiles", {}).keys())

    def get_active_profile(self) -> str:
        """Return the name of the currently active profile."""
        return str(self._data.get("active_profile", "office"))

    def save_profile(self, name: str) -> None:
        """Snapshot current layout into profile *name* and persist."""
        name = name.lower().strip()
        profiles = self._data.setdefault("profiles", {})
        profiles[name] = self._snapshot_layout()
        if "active_profile" not in self._data:
            self._data["active_profile"] = name
        self.save()

    def switch_profile(self, name: str) -> None:
        """
        Load profile *name* into the live config keys.
        All existing callers (table_region, connect_button, etc.) will
        automatically see the new values after this call.
        """
        name = name.lower().strip()
        profiles = self._data.get("profiles", {})
        if name not in profiles:
            raise KeyError(f"Profile '{name}' not found. Available: {list(profiles.keys())}")

        # Preserve the current profile's latest layout before switching
        current = self.get_active_profile()
        if current in profiles and current != name:
            profiles[current] = self._snapshot_layout()

        self._apply_layout(profiles[name])
        self._data["active_profile"] = name
        self.save()

    def delete_profile(self, name: str) -> None:
        """Remove a profile (cannot delete the currently active one)."""
        if name == self.get_active_profile():
            raise ValueError(f"Cannot delete the currently active profile '{name}'.")
        profiles = self._data.get("profiles", {})
        if name in profiles:
            del profiles[name]
            self.save()

    def validate(self) -> list[str]:
        """
        Return a list of human-readable validation warnings.
        Empty list means the config looks good.
        """
        warnings: list[str] = []
        if not self.is_calibrated():
            warnings.append(
                "table_region not calibrated — run 'python main.py calibrate'."
            )
        if not self._data.get("username"):
            warnings.append(
                "username is empty — set it in config.json before running."
            )
        cb = self._data["connect_button"]
        if cb.get("x", -1) < 0:
            warnings.append(
                "connect_button not calibrated — run 'python main.py calibrate'."
            )
        return warnings

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """Recursively merge *override* into a copy of *base*."""
        result = deepcopy(base)
        for key, val in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(val, dict):
                result[key] = ConfigManager._deep_merge(result[key], val)
            else:
                result[key] = val
        return result

    def __repr__(self) -> str:
        return f"ConfigManager(path={self._path!r}, calibrated={self.is_calibrated()})"
