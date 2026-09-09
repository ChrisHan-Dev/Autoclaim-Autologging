"""
sop_config.py — SOP Tool Config Manager
Quan ly file sop_config.json doc lap voi autoclaim config.json
"""

from __future__ import annotations

import json
import os
from typing import Any

# File config rieng cua SOP tool
_DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "sop_config.json")

_DEFAULTS: dict = {
    "form_coords": {
        # Toa do tam cua tung dropdown — se duoc calibrate
        "vision_functionality": {"x": 0, "y": 0},
        "actions_required":     {"x": 0, "y": 0},
        "maintenance_issues":   {"x": 0, "y": 0},
        "resolution":           {"x": 0, "y": 0},
        "comment":              {"x": 0, "y": 0},
        "send_button":          {"x": 0, "y": 0},
    },
    "hotkeys": {
        # Hotkey cho tung case SOP
        "case_1": "f1",
        "case_2": "f2",
        "case_3": "f3",
        "case_4": "f4",
        "exit":   "esc",
    },
    "mouse": {
        "move_duration_s":    0.15,
        "randomize_offset_px": 3,
    },
    "timing": {
        "click_delay_s":    0.3,
        "dropdown_delay_s": 0.6,
        "option_delay_s":   0.2,
        "type_interval_s":  0.05,
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
    """Simple JSON config manager cho SOP tool."""

    def __init__(self, path: str = _DEFAULT_CONFIG_PATH) -> None:
        self._path = path
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self._path):
            with open(self._path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        else:
            # Tao file voi gia tri mac dinh
            self._data = _DEFAULTS.copy()
            self.save()

    def save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    @property
    def form_coords(self) -> dict:
        return self._data.get("form_coords", _DEFAULTS["form_coords"])

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

    def is_calibrated(self) -> bool:
        """Tra ve True neu da calibrate it nhat 1 dropdown."""
        coords = self.form_coords
        return any(
            coords.get(k, {}).get("x", 0) != 0
            for k in ["vision_functionality", "actions_required", "resolution"]
        )
