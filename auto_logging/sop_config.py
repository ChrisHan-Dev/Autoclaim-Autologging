"""
sop_config.py — SOP Tool Config Manager (Multi-Display Support 1, 2, 3, 4)
========================================================================
Quản lý file sop_config.json độc lập với autoclaim config.json.
Hỗ trợ quản lý toạ độ theo đúng số thứ tự Màn hình Windows (1, 2, 3, 4).
Mặc định tập trung vào cặp Màn hình 4 (Main) và Màn hình 3.
"""

from __future__ import annotations

import json
import os
from typing import Any

# File config riêng của SOP tool
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
            "name": "Màn hình 4 (Main)",
            "form_coords": _DEFAULT_FORM_COORDS.copy(),
            "dropdown_geometry": {},
        },
        "3": {
            "name": "Màn hình 3 (Phụ)",
            "form_coords": _DEFAULT_FORM_COORDS.copy(),
            "dropdown_geometry": {},
        },
        "1": {
            "name": "Màn hình 1",
            "form_coords": _DEFAULT_FORM_COORDS.copy(),
            "dropdown_geometry": {},
        },
        "2": {
            "name": "Màn hình 2",
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
    """JSON config manager cho SOP tool hỗ trợ màn hình 1, 2, 3, 4."""

    def __init__(self, path: str = _DEFAULT_CONFIG_PATH) -> None:
        self._path = path
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self._path):
            with open(self._path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        else:
            self._data = _DEFAULTS.copy()
            self.save()
            return

        displays = self._data.setdefault("displays", {})

        # Migration: Nếu toạ độ Màn 1 trước đây thực chất là Main Screen (Màn 4)
        if "1" in displays and "4" not in displays:
            # Chuyển toạ độ đã calibrate sang Màn 4
            displays["4"] = {
                "name": "Màn hình 4 (Main)",
                "form_coords": displays["1"].get("form_coords", self._data.get("form_coords", _DEFAULT_FORM_COORDS.copy())),
                "dropdown_geometry": displays["1"].get("dropdown_geometry", self._data.get("dropdown_geometry", {})),
            }
        elif "4" not in displays:
            displays["4"] = {
                "name": "Màn hình 4 (Main)",
                "form_coords": self._data.get("form_coords", _DEFAULT_FORM_COORDS.copy()),
                "dropdown_geometry": self._data.get("dropdown_geometry", {}),
            }

        if "3" not in displays:
            displays["3"] = {
                "name": "Màn hình 3 (Phụ)",
                "form_coords": _DEFAULT_FORM_COORDS.copy(),
                "dropdown_geometry": {},
            }

        if "active_display" not in self._data or self._data["active_display"] not in [3, 4]:
            self._data["active_display"] = 4

        if "active_pair" not in self._data:
            self._data["active_pair"] = [4, 3]

        hotkeys = self._data.setdefault("hotkeys", {})
        if "toggle_display" not in hotkeys:
            hotkeys["toggle_display"] = "f6"

        self.save()

    def save(self) -> None:
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
        pair = self._data.get("active_pair", [4, 3])
        return [int(p) for p in pair]

    def set_active_pair(self, d1: int, d2: int) -> None:
        self._data["active_pair"] = [int(d1), int(d2)]
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
                "name": f"Màn hình {d_id}",
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
                "name": f"Màn hình {d_id}",
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

    # ── Properties cho backward compatibility ──────────────────────────────────

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
