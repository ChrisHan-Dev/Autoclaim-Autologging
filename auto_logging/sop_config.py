"""
sop_config.py — SOP Tool Config Manager (Multi-Display + Profile Support)
=========================================================================
Manages sop_config.json independently from autoclaim config.json.
Supports coordinate management matching Windows display IDs (1, 2, 3, 4).
Default focuses on Display 4 (Main) and Display 3.
Supports Profiles (Home / Office) for fast switching between monitor setups.
"""

from __future__ import annotations

import json
import os
from typing import Any

# SOP tool config file
_DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "sop_config.json")

_DEFAULT_FORM_COORDS: dict = {
    "vision_functionality": {"x": 0, "y": 0},
    "actions_required":     {"x": 0, "y": 0},
    "maintenance_issues":   {"x": 0, "y": 0},
    "resolution":           {"x": 0, "y": 0},
    "comment":              {"x": 0, "y": 0},
    "send_button":          {"x": 0, "y": 0},
}

_DEFAULTS: dict = {
    "active_display": 4,
    "active_pair": [4, 3],
    "active_sop_type": "SUSPECT",
    "displays": {
        "4": {
            "name": "Display 4 (Main)",
            "form_coords": _DEFAULT_FORM_COORDS.copy(),
            "dropdown_geometry": {},
        },
        "3": {
            "name": "Display 3 (Secondary)",
            "form_coords": _DEFAULT_FORM_COORDS.copy(),
            "dropdown_geometry": {},
        },
        "1": {
            "name": "Display 1",
            "form_coords": _DEFAULT_FORM_COORDS.copy(),
            "dropdown_geometry": {},
        },
        "2": {
            "name": "Display 2",
            "form_coords": _DEFAULT_FORM_COORDS.copy(),
            "dropdown_geometry": {},
        },
    },
    "form_coords": _DEFAULT_FORM_COORDS.copy(),
    "dropdown_geometry": {},
    "hotkeys": {
        "case_1": "insert",
        "case_2": "home",
        "case_3": "pageup",
        "case_4": "pagedown",
        "case_5": "end",
        "case_6": "delete",
        "toggle_display": "f6",
        "toggle_type":    "f7",
        "exit":   "ctrl+esc",
    },
    "mouse": {
        "move_duration_s":    0.02,
        "randomize_offset_px": 0,
    },
    "timing": {
        "click_delay_s":    0.03,
        "dropdown_delay_s": 0.12,
        "option_delay_s":   0.03,
        "type_interval_s":  0.02,
    },
    "ocr": {
        "gpu": False,
        "confidence_threshold": 0.4,
    },
    "logging": {
        "level":   "INFO",
        "log_dir": "sop/logs",
    },
}


class SOPConfig:
    """JSON config manager for SOP tool supporting displays 1, 2, 3, 4."""

    def __init__(self, path: str = _DEFAULT_CONFIG_PATH) -> None:
        self._path = path
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        from copy import deepcopy
        if os.path.exists(self._path):
            with open(self._path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        else:
            self._data = _DEFAULTS.copy()
            self._data["active_profile"] = "office"
            self.save()
            return

        # Ensure active_profile exists and defaults to "office"
        if "active_profile" not in self._data:
            self._data["active_profile"] = "office"

        # ── Profile migration: ensure "home" and "office" profiles exist ──────
        profiles = self._data.setdefault("profiles", {})
        if "office" not in profiles:
            profiles["office"] = self._snapshot_display_data()
        if "home" not in profiles:
            profiles["home"] = {
                "displays": {
                    str(d): {
                        "name": f"Display {d}",
                        "form_coords": _DEFAULT_FORM_COORDS.copy(),
                        "dropdown_geometry": {},
                    }
                    for d in [1, 2, 3, 4]
                },
                "active_display": 4,
                "active_pair": [4, 3],
                "active_sop_type": "SUSPECT",
            }

        # Apply active profile data into top-level so live queries are consistent
        active_prof = self.get_active_profile()
        if active_prof in profiles:
            snap = profiles[active_prof]
            if "displays" in snap:
                self._data["displays"] = deepcopy(snap["displays"])
            if "active_display" in snap:
                self._data["active_display"] = snap["active_display"]
            if "active_pair" in snap:
                self._data["active_pair"] = list(snap["active_pair"])
            if "active_sop_type" in snap:
                self._data["active_sop_type"] = snap["active_sop_type"]
            active_d = str(self._data.get("active_display", 4))
            if active_d in self._data.get("displays", {}):
                self._data["form_coords"] = deepcopy(self._data["displays"][active_d].get("form_coords", {}))
                self._data["dropdown_geometry"] = deepcopy(self._data["displays"][active_d].get("dropdown_geometry", {}))

        displays = self._data.setdefault("displays", {})

        # Ensure displays in active_pair exist in displays dict
        active_pair = self._data.get("active_pair", [4, 3])
        if not isinstance(active_pair, list) or len(active_pair) < 1:
            active_pair = [4, 3]
            self._data["active_pair"] = active_pair

        for d in [1, 2, 3, 4]:
            d_str = str(d)
            if d_str not in displays:
                displays[d_str] = {
                    "name": f"Display {d}",
                    "form_coords": _DEFAULT_FORM_COORDS.copy() if d in active_pair else {},
                    "dropdown_geometry": {},
                }

        if "active_display" not in self._data or int(self._data["active_display"]) not in [1, 2, 3, 4]:
            self._data["active_display"] = active_pair[0]

        hotkeys = self._data.setdefault("hotkeys", {})
        if "toggle_display" not in hotkeys:
            hotkeys["toggle_display"] = "f6"

    def save(self) -> None:
        active_prof = self.get_active_profile()
        if "profiles" in self._data and active_prof in self._data.get("profiles", {}):
            self._data["profiles"][active_prof] = self._snapshot_display_data()
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    # ── Multi-Display API ──────────────────────────────────────────────────────

    def get_active_display(self) -> int:
        return int(self._data.get("active_display", 4))

    def set_active_display(self, display_id: int) -> None:
        self._data["active_display"] = int(display_id)
        self.save()

    def get_active_pair(self) -> list[int]:
        """Return the list of monitors in the F6 cycle (can be 1–4 monitors)."""
        pair = self._data.get("active_pair", [4, 3])
        return [int(p) for p in pair]

    def set_active_pair(self, *monitors: int) -> None:
        """Set the monitors in the F6 cycle. Accepts 1 to 4 monitor IDs."""
        self._data["active_pair"] = [int(m) for m in monitors]
        self.save()

    def get_active_sop_type(self) -> str:
        return str(self._data.get("active_sop_type", "SUSPECT")).upper()

    def set_active_sop_type(self, sop_type: str) -> None:
        self._data["active_sop_type"] = str(sop_type).upper()
        self.save()

    def get_form_coords(self, display_id: int | None = None) -> dict:
        d_id = str(display_id if display_id is not None else self.get_active_display())
        displays = self._data.get("displays", {})
        if d_id in displays and "form_coords" in displays[d_id]:
            return displays[d_id]["form_coords"]
        return self._data.get("form_coords", _DEFAULT_FORM_COORDS.copy())

    def set_form_coords(self, coords: dict, display_id: int | None = None) -> None:
        d_id = str(display_id if display_id is not None else self.get_active_display())
        if "displays" not in self._data:
            self._data["displays"] = {}
        if d_id not in self._data["displays"]:
            self._data["displays"][d_id] = {
                "name": f"Display {d_id}",
                "form_coords": {},
                "dropdown_geometry": {},
            }
        self._data["displays"][d_id]["form_coords"] = coords
        if d_id == "4":
            self._data["form_coords"] = coords
        self.save()

    def get_dropdown_geometry(self, display_id: int | None = None) -> dict:
        d_id = str(display_id if display_id is not None else self.get_active_display())
        displays = self._data.get("displays", {})
        if d_id in displays and "dropdown_geometry" in displays[d_id]:
            return displays[d_id]["dropdown_geometry"]
        return self._data.get("dropdown_geometry", {})

    def set_dropdown_geometry(self, geom: dict, display_id: int | None = None) -> None:
        d_id = str(display_id if display_id is not None else self.get_active_display())
        if "displays" not in self._data:
            self._data["displays"] = {}
        if d_id not in self._data["displays"]:
            self._data["displays"][d_id] = {
                "name": f"Display {d_id}",
                "form_coords": {},
                "dropdown_geometry": {},
            }
        self._data["displays"][d_id]["dropdown_geometry"] = geom
        if d_id == "4":
            self._data["dropdown_geometry"] = geom
        self.save()

    def is_calibrated(self, display_id: int | None = None) -> bool:
        coords = self.get_form_coords(display_id)
        return any(
            coords.get(k, {}).get("x", 0) != 0
            for k in ["vision_functionality", "actions_required", "resolution"]
        )

    # ── Profile API ────────────────────────────────────────────────────────────

    def _snapshot_display_data(self) -> dict:
        """Capture the current display calibration data for a profile snapshot."""
        from copy import deepcopy
        return {
            "displays":        deepcopy(self._data.get("displays", {})),
            "active_display":  self._data.get("active_display", 4),
            "active_pair":     list(self._data.get("active_pair", [4, 3])),
            "active_sop_type": self._data.get("active_sop_type", "SUSPECT"),
        }

    def list_profiles(self) -> list[str]:
        """Return list of saved profile names, e.g. ['home', 'office']."""
        return list(self._data.get("profiles", {}).keys())

    def get_active_profile(self) -> str:
        """Return the name of the currently active profile."""
        return str(self._data.get("active_profile", "home"))

    def save_profile(self, name: str) -> None:
        """Snapshot current display calibration into profile *name* and persist."""
        name = name.lower().strip()
        profiles = self._data.setdefault("profiles", {})
        profiles[name] = self._snapshot_display_data()
        if "active_profile" not in self._data:
            self._data["active_profile"] = name
        self.save()

    def switch_profile(self, name: str) -> None:
        """
        Load profile *name* into the live top-level keys.
        All existing callers of get_form_coords / get_active_display etc.
        will automatically see the new values after this call.
        """
        from copy import deepcopy
        name = name.lower().strip()
        profiles = self._data.get("profiles", {})
        if name not in profiles:
            raise KeyError(f"Profile '{name}' not found. Available: {list(profiles.keys())}")

        # Preserve the current profile's latest calibration before switching
        current = self.get_active_profile()
        if current in profiles and current != name:
            profiles[current] = self._snapshot_display_data()

        snap = profiles[name]
        self._data["displays"]        = deepcopy(snap.get("displays", {}))
        self._data["active_display"]  = snap.get("active_display", 4)
        self._data["active_pair"]     = list(snap.get("active_pair", [4, 3]))
        self._data["active_sop_type"] = snap.get("active_sop_type", "SUSPECT")
        # Keep top-level form_coords in sync with active display
        active_d = str(self._data["active_display"])
        displays = self._data.get("displays", {})
        if active_d in displays:
            self._data["form_coords"]        = deepcopy(displays[active_d].get("form_coords", {}))
            self._data["dropdown_geometry"]  = deepcopy(displays[active_d].get("dropdown_geometry", {}))
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

    # ── Properties for backward compatibility ──────────────────────────────────

    @property
    def form_coords(self) -> dict:
        return self.get_form_coords()

    @property
    def hotkeys_cfg(self) -> dict:
        return self._data.get("hotkeys", _DEFAULTS["hotkeys"])

    @property
    def mouse_cfg(self) -> dict:
        return self._data.get("mouse", _DEFAULTS["mouse"])

    @property
    def timing_cfg(self) -> dict:
        return self._data.get("timing", _DEFAULTS["timing"])

    @property
    def ocr_cfg(self) -> dict:
        return self._data.get("ocr", _DEFAULTS["ocr"])
