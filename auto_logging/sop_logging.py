"""
sop_logging.py — Auto-fill "Logging SOP (SUSPECT)" form (STANDALONE & Multi-Display)
===================================================================================
Độc lập hoàn toàn với autoclaim. Chạy bằng sop_main.py.

Cách hoạt động:
  1. User nhấn hotkey (Insert, Home, PgUp, PgDn, End) hoặc click trên HUD
  2. Script kiểm tra màn hình đang chọn (Màn 1 hoặc Màn 2)
  3. Script click từng dropdown theo thứ tự và chọn option định sẵn
  4. Fill Comment nếu có
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import random
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import pyautogui
pyautogui.PAUSE = 0.0


# =============================================================================
# DROPDOWN OPTIONS  (must match exact text in the form)
# =============================================================================

class VisionFunctionality:
    ALL_CAMERAS   = "All cameras functional"
    SOME_CAMERAS  = "Some cameras functional"
    ONLY_PAYLOAD  = "Only payload cameras"
    ONLY_DRIVING  = "Only driving cameras"
    NO_CAMERAS    = "No cameras functional"


class ActionsRequired:
    HOME_ACTUATORS    = "Home actuators"
    ALIGN             = "Align"
    PLACE             = "Place"
    EXTRACT           = "Extract"
    NO_ACTION_FORCED  = "No action - forced"
    NO_ACTION_CHOICE  = "No action - choice"
    REPOSITION        = "Reposition"
    POSITION_UPDATE   = "Position update"
    WENT_TO_CHARGER   = "Went to charger (from driving)"
    SENT_TO_OPERATION = "Sent to operation (from driving)"


class MaintenanceIssues:
    AXES_NOT_RESPONDING = "Axes not responding"
    SENSOR_MALFUNCTION  = "Sensor malfunction"
    DAMAGED_CASE        = "Damaged case / Debris / Tape"
    BENT_HATS           = "Bent hats"
    BAD_SKU             = "Bad SKU"
    NO_CASE             = "No case"
    NOT_PICKABLE        = "Not pickable"
    ROGUE_CASE          = "Rogue case"
    CASE_PUSH_THROUGH   = "Case push through"
    CASE_FELL_SIDE      = "Case fell to the side"


class Resolution:
    SUCCESSFUL          = "Successful"
    BOT_STOED           = "Bot STOed"
    CHD_WITH_PAYLOAD    = "CHD (with payload)"
    CHD_WITHOUT_PAYLOAD = "CHD (without payload)"
    UNSUCCESSFUL        = "Unsuccessful"


# =============================================================================
# DROPDOWN OPTION ORDER (phải khớp chính xác với thứ tự trong UI)
# Dùng để tính toạ độ click theo index
# =============================================================================

DROPDOWN_OPTIONS: dict[str, list[str]] = {
    "vision_functionality": [
        VisionFunctionality.ALL_CAMERAS,     # index 0
        VisionFunctionality.SOME_CAMERAS,    # index 1
        VisionFunctionality.ONLY_PAYLOAD,    # index 2
        VisionFunctionality.ONLY_DRIVING,    # index 3
        VisionFunctionality.NO_CAMERAS,      # index 4
    ],
    "actions_required": [
        ActionsRequired.HOME_ACTUATORS,      # index 0
        ActionsRequired.ALIGN,               # index 1
        ActionsRequired.PLACE,               # index 2
        ActionsRequired.EXTRACT,             # index 3
        ActionsRequired.NO_ACTION_FORCED,    # index 4
        ActionsRequired.NO_ACTION_CHOICE,    # index 5
        ActionsRequired.REPOSITION,          # index 6
        ActionsRequired.POSITION_UPDATE,     # index 7
        ActionsRequired.WENT_TO_CHARGER,     # index 8
        ActionsRequired.SENT_TO_OPERATION,   # index 9
    ],
    "maintenance_issues": [
        MaintenanceIssues.AXES_NOT_RESPONDING,   # index 0
        MaintenanceIssues.SENSOR_MALFUNCTION,    # index 1
        MaintenanceIssues.DAMAGED_CASE,          # index 2
        MaintenanceIssues.BENT_HATS,             # index 3
        MaintenanceIssues.BAD_SKU,               # index 4
        MaintenanceIssues.NO_CASE,               # index 5
        MaintenanceIssues.NOT_PICKABLE,          # index 6
        MaintenanceIssues.ROGUE_CASE,            # index 7
        MaintenanceIssues.CASE_PUSH_THROUGH,     # index 8
        MaintenanceIssues.CASE_FELL_SIDE,        # index 9
    ],
    "resolution": [
        Resolution.SUCCESSFUL,               # index 0
        Resolution.BOT_STOED,                # index 1
        Resolution.CHD_WITH_PAYLOAD,         # index 2
        Resolution.CHD_WITHOUT_PAYLOAD,      # index 3
        Resolution.UNSUCCESSFUL,             # index 4
    ],
}

SINGLE_SELECT_FIELDS = {"vision_functionality", "resolution"}
MULTI_SELECT_FIELDS  = {"actions_required", "maintenance_issues"}


# =============================================================================
# SOP CASE DEFINITION
# =============================================================================

@dataclass
class SOPCase:
    name: str
    vision_functionality: Optional[str] = None
    actions_required: Optional[str | list] = None
    maintenance_issues: Optional[str] = None
    resolution: Optional[str] = None
    comment: str = ""


# =============================================================================
# CÁC TRƯỜNG HỢP SOP THEO TỪNG LOẠI (SUSPECT / CHRF)
# =============================================================================

# ── 1. SUSPECT (6 Cases ban đầu) ──────────────────────────────────────────────
SUSPECT_CASES: dict[str, SOPCase] = {

    # ── Case 1 (Insert) ── All cameras / Align+Extract / (no maint) / Successful
    "f1": SOPCase(
        name                 = "Case 1 - All cam / Align+Extract / Successful",
        vision_functionality = VisionFunctionality.ALL_CAMERAS,
        actions_required     = [ActionsRequired.ALIGN, ActionsRequired.EXTRACT],
        maintenance_issues   = None,
        resolution           = Resolution.SUCCESSFUL,
        comment              = "",
    ),

    # ── Case 2 (Home) ── No cameras / No action-forced / (no maint) / Unsuccessful
    "f2": SOPCase(
        name                 = "Case 2 - No cam / No action forced / Unsuccessful",
        vision_functionality = VisionFunctionality.NO_CAMERAS,
        actions_required     = ActionsRequired.NO_ACTION_FORCED,
        maintenance_issues   = None,
        resolution           = Resolution.UNSUCCESSFUL,
        comment              = "",
    ),

    # ── Case 3 (PgUp) ── All cameras / No action-forced / Not pickable / Unsuccessful
    "f3": SOPCase(
        name                 = "Case 3 - All cam / No action forced / Not pickable / Unsuccessful",
        vision_functionality = VisionFunctionality.ALL_CAMERAS,
        actions_required     = ActionsRequired.NO_ACTION_FORCED,
        maintenance_issues   = MaintenanceIssues.NOT_PICKABLE,
        resolution           = Resolution.UNSUCCESSFUL,
        comment              = "",
    ),

    # ── Case 4 (PgDn) ── All cameras / Align+Extract / Damaged case / CHD with payload
    "f4": SOPCase(
        name                 = "Case 4 - All cam / Align+Extract / Damaged case / CHD",
        vision_functionality = VisionFunctionality.ALL_CAMERAS,
        actions_required     = [ActionsRequired.ALIGN, ActionsRequired.EXTRACT],
        maintenance_issues   = MaintenanceIssues.DAMAGED_CASE,
        resolution           = Resolution.CHD_WITH_PAYLOAD,
        comment              = "",
    ),

    # ── Case 5 (End) ── All cameras / No action-forced / No case / Successful
    "f5": SOPCase(
        name                 = "Case 5 - All cam / No action / No case / Successful",
        vision_functionality = VisionFunctionality.ALL_CAMERAS,
        actions_required     = ActionsRequired.NO_ACTION_FORCED,
        maintenance_issues   = MaintenanceIssues.NO_CASE,
        resolution           = Resolution.SUCCESSFUL,
        comment              = "",
    ),

    # ── Case 6 (Del) ── All cameras / No action-forced / Rogue case / CHD with payload
    "f6": SOPCase(
        name                 = "Case 6 - All cam / No action forced / Rogue case / CHD",
        vision_functionality = VisionFunctionality.ALL_CAMERAS,
        actions_required     = ActionsRequired.NO_ACTION_FORCED,
        maintenance_issues   = MaintenanceIssues.ROGUE_CASE,
        resolution           = Resolution.CHD_WITH_PAYLOAD,
        comment              = "",
    ),

}

# ── 2. CHRF (Charger Recovery) ────────────────────────────────────────────────
CHRF_CASES: dict[str, SOPCase] = {

    # ── Case 1 (Insert) ── All cam / Align + Place / Successful
    "c1": SOPCase(
        name                 = "CHRF 1 - All cam / Align+Place / Successful",
        vision_functionality = VisionFunctionality.ALL_CAMERAS,
        actions_required     = [ActionsRequired.ALIGN, ActionsRequired.PLACE],
        maintenance_issues   = None,
        resolution           = Resolution.SUCCESSFUL,
        comment              = "",
    ),

    # ── Case 2 (Home) ── All cam / Home actuator / Successful
    "c2": SOPCase(
        name                 = "CHRF 2 - All cam / Home actuator / Successful",
        vision_functionality = VisionFunctionality.ALL_CAMERAS,
        actions_required     = ActionsRequired.HOME_ACTUATORS,
        maintenance_issues   = None,
        resolution           = Resolution.SUCCESSFUL,
        comment              = "",
    ),

    # ── Case 3 (PgUp) ── All cam / Home actuator + Align + Place / Successful
    "c3": SOPCase(
        name                 = "CHRF 3 - All cam / Home+Align+Place / Successful",
        vision_functionality = VisionFunctionality.ALL_CAMERAS,
        actions_required     = [ActionsRequired.HOME_ACTUATORS, ActionsRequired.ALIGN, ActionsRequired.PLACE],
        maintenance_issues   = None,
        resolution           = Resolution.SUCCESSFUL,
        comment              = "",
    ),

    # ── Case 4 (PgDn) ── All cam / Home actuator / Axes not responding / CHD (without payload)
    "c4": SOPCase(
        name                 = "CHRF 4 - All cam / Home / Axes not resp / CHD no payl",
        vision_functionality = VisionFunctionality.ALL_CAMERAS,
        actions_required     = ActionsRequired.HOME_ACTUATORS,
        maintenance_issues   = MaintenanceIssues.AXES_NOT_RESPONDING,
        resolution           = Resolution.CHD_WITHOUT_PAYLOAD,
        comment              = "",
    ),

    # ── Case 5 (End) ── All cam / Home actuator / Sensor malfunction / CHD (without payload)
    "c5": SOPCase(
        name                 = "CHRF 5 - All cam / Home / Sensor malf / CHD no payl",
        vision_functionality = VisionFunctionality.ALL_CAMERAS,
        actions_required     = ActionsRequired.HOME_ACTUATORS,
        maintenance_issues   = MaintenanceIssues.SENSOR_MALFUNCTION,
        resolution           = Resolution.CHD_WITHOUT_PAYLOAD,
        comment              = "",
    ),

    # ── Case 6 (Del) ── All cam / Align + Extract / Damaged case / CHD (with payload)
    "c6": SOPCase(
        name                 = "CHRF 6 - All cam / Align+Ext / Damaged / CHD with payl",
        vision_functionality = VisionFunctionality.ALL_CAMERAS,
        actions_required     = [ActionsRequired.ALIGN, ActionsRequired.EXTRACT],
        maintenance_issues   = MaintenanceIssues.DAMAGED_CASE,
        resolution           = Resolution.CHD_WITH_PAYLOAD,
        comment              = "",
    ),

}

SOP_CASES_BY_TYPE: dict[str, dict[str, SOPCase]] = {
    "SUSPECT": SUSPECT_CASES,
    "CHRF":    CHRF_CASES,
}

# Tương thích ngược: mặc định trỏ về SUSPECT_CASES
SOP_CASES: dict[str, SOPCase] = SUSPECT_CASES


# =============================================================================
# FORM FILLER ENGINE  (position-based — KHÔNG dùng OCR)
# =============================================================================

class SOPFormFiller:
    """
    Chọn option trong dropdown theo toạ độ pixel đã calibrate của màn hình tương ứng.
    KHÔNG dùng OCR.
    """

    def __init__(self, cfg) -> None:
        self._cfg = cfg
        timing = cfg.timing_cfg
        mouse  = cfg.mouse_cfg

        self.CLICK_DELAY    = timing.get("click_delay_s",    0.03)
        self.DROPDOWN_DELAY = timing.get("dropdown_delay_s", 0.12)
        self.OPTION_DELAY   = timing.get("option_delay_s",   0.03)
        self.TYPE_INTERVAL  = timing.get("type_interval_s",  0.02)

    def warmup(self, display_id: int | None = None) -> None:
        """Kiểm tra calibration trước khi chạy."""
        pyautogui.FAILSAFE = False
        d_id = display_id if display_id is not None else self._cfg.get_active_display()
        geom = self._cfg.get_dropdown_geometry(d_id)
        missing = [f for f in DROPDOWN_OPTIONS if f not in geom]
        if missing:
            print(f"[SOP] WARN (Màn {d_id}): Chưa calibrate options cho: {missing}")
            print(f"[SOP]       Chạy: python sop_main.py calibrate_options --display {d_id}")
        else:
            print(f"[SOP] Ready (Màn {d_id}, position-based, no OCR).")

    # ── win32 mouse implementation (multi-monitor & hardware-safe) ─────────────

    def _move_cursor(self, x: int, y: int) -> None:
        """Dịch chuyển chuột tức thì đến toạ độ ảo (0ms, hỗ trợ mọi màn hình)."""
        ctypes.windll.user32.SetCursorPos(int(x), int(y))

    def _hardware_click(self, hold_s: float = 0.005) -> None:
        """Nhấn chuột trái duy nhất 1 lần tại vị trí hiện tại (~5ms)."""
        ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
        time.sleep(hold_s)
        ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP

    def _click(self, coord: dict) -> None:
        try:
            x = int(coord["x"])
            y = int(coord["y"])
            print(f"[SOP]    > Move & Click: ({x}, {y})")
            self._move_cursor(x, y)
            self._hardware_click(hold_s=0.005)
            time.sleep(self.CLICK_DELAY)
        except Exception as e:
            print(f"[SOP] Lỗi click: {e}")

    def _click_xy(self, x: int, y: int) -> None:
        try:
            print(f"[SOP]    > Move & Click Option: ({x}, {y})")
            self._move_cursor(int(x), int(y))
            self._hardware_click(hold_s=0.005)
            time.sleep(self.OPTION_DELAY)
        except Exception as e:
            print(f"[SOP] Lỗi click_xy: {e}")

    def _send_esc(self) -> None:
        """Gửi phím ESC siêu tốc qua Win32 API (~15ms)."""
        ctypes.windll.user32.keybd_event(0x1B, 0, 0, 0)  # VK_ESCAPE DOWN
        time.sleep(0.005)
        ctypes.windll.user32.keybd_event(0x1B, 0, 2, 0)  # VK_ESCAPE UP
        time.sleep(0.01)

    # ── position helpers ──────────────────────────────────────────────────────

    def _get_option_pos(self, field: str, option_text: str, display_id: int | None = None) -> tuple | None:
        """
        Tính toạ độ màn hình của option trong dropdown dựa trên display_id.
        first_option_y + index * row_height
        """
        d_id = display_id if display_id is not None else self._cfg.get_active_display()
        geom = self._cfg.get_dropdown_geometry(d_id).get(field)
        if not geom:
            print(f"[SOP] WARN: Chưa calibrate options cho '{field}' (Màn {d_id})!")
            print(f"[SOP]       Chạy: python sop_main.py calibrate_options --display {d_id}")
            return None

        options_list = DROPDOWN_OPTIONS.get(field, [])
        if option_text not in options_list:
            print(f"[SOP] WARN: '{option_text}' không có trong DROPDOWN_OPTIONS['{field}']!")
            return None

        idx = options_list.index(option_text)
        x   = geom["first_option_x"]
        y   = geom["first_option_y"] + idx * geom["row_height"]
        return (x, y)

    # ── single-select (Vision, Resolution): click -> auto-close ──────────────

    def _select_single(self, field: str, coord: dict, option_text: str, display_id: int | None = None) -> bool:
        pos = self._get_option_pos(field, option_text, display_id=display_id)
        if pos is None:
            return False

        idx = DROPDOWN_OPTIONS[field].index(option_text)
        print(f"[SOP]   [{idx}] {option_text} @ ({pos[0]}, {pos[1]})")

        self._click(coord)
        time.sleep(self.DROPDOWN_DELAY)
        self._click_xy(pos[0], pos[1])
        return True

    # ── multi-select (Actions, Maintenance): click options -> ESC ─────────────

    def _select_multi(self, field: str, coord: dict, options: list, display_id: int | None = None) -> bool:
        self._click(coord)
        time.sleep(self.DROPDOWN_DELAY)

        success = True
        for opt in options:
            pos = self._get_option_pos(field, opt, display_id=display_id)
            if pos is None:
                success = False
                continue
            idx = DROPDOWN_OPTIONS[field].index(opt)
            print(f"[SOP]    + [{idx}] {opt} @ ({pos[0]}, {pos[1]})")
            self._click_xy(pos[0], pos[1])

        self._send_esc()
        return success

    # ── comment ───────────────────────────────────────────────────────────────

    def _fill_comment(self, text: str, coords: dict) -> None:
        if not text:
            return
        if "comment" in coords:
            self._click(coords["comment"])
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.02)
            pyautogui.typewrite(text, interval=self.TYPE_INTERVAL)

    def _ensure_window_focus(self, coords: dict) -> None:
        """
        Kích hoạt cửa sổ Teleops trước khi click dropdown:
        1. Gọi Win32 SetForegroundWindow vào cửa sổ chứa form.
        2. Click nhẹ vào phần nhãn text 'Vision Functionality :' ở bên trái ô nhập.
        """
        vf = coords.get("vision_functionality", {"x": 252, "y": 638})
        vx = int(vf.get("x", 252))
        vy = int(vf.get("y", 638))

        try:
            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
            pt = POINT(vx, vy)
            hwnd = ctypes.windll.user32.WindowFromPoint(pt)
            if hwnd:
                root = ctypes.windll.user32.GetAncestor(hwnd, 2)  # GA_ROOT
                target = root if root else hwnd
                ctypes.windll.user32.SetForegroundWindow(target)
                time.sleep(0.01)
        except Exception as e:
            print(f"[SOP] Win32 focus note: {e}")

        safe_x = max(-3000, vx - 130)
        safe_y = vy
        print(f"[SOP] Focus Teleops window at label: ({safe_x}, {safe_y})")
        self._move_cursor(safe_x, safe_y)
        self._hardware_click(hold_s=0.005)
        time.sleep(0.01)

    # ── main fill method ──────────────────────────────────────────────────────

    def fill(
        self,
        case: SOPCase,
        on_status: Optional[Callable[[str, str], None]] = None,
        display_id: int | None = None,
    ) -> bool:
        t_start = time.perf_counter()
        d_id = display_id if display_id is not None else self._cfg.get_active_display()

        # Nhả các phím modifier (Alt, Ctrl, Shift)
        time.sleep(0.003)
        ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)  # VK_MENU (Alt) UP
        ctypes.windll.user32.keybd_event(0x11, 0, 2, 0)  # VK_CONTROL UP
        ctypes.windll.user32.keybd_event(0x10, 0, 2, 0)  # VK_SHIFT UP
        time.sleep(0.003)

        coords = self._cfg.get_form_coords(d_id)
        if not self._cfg.is_calibrated(d_id):
            err_msg = f"Màn hình {d_id} chưa calibrate! Chạy: python sop_main.py calibrate --display {d_id}"
            print(f"\n[SOP] ❌ {err_msg}\n")
            if on_status:
                on_status("error", f"Màn {d_id} chưa Calibrate!")
            return False

        if on_status:
            on_status("busy", f"Màn {d_id}: {case.name}")

        print(f"\n[SOP] >>> [MÀN HÌNH {d_id}] {case.name}")

        try:
            self._ensure_window_focus(coords)

            # ── Vision Functionality ──────────────────────────────────────────
            if case.vision_functionality:
                if on_status:
                    on_status("detail", f"[Màn {d_id}] Vision: {case.vision_functionality}")
                print(f"[SOP]  Vision  : {case.vision_functionality}")
                self._select_single(
                    "vision_functionality",
                    coords["vision_functionality"],
                    case.vision_functionality,
                    display_id=d_id,
                )

            # ── Actions Required ──────────────────────────────────────────────
            if case.actions_required:
                opts = case.actions_required if isinstance(case.actions_required, list) \
                       else [case.actions_required]
                if on_status:
                    on_status("detail", f"[Màn {d_id}] Actions: {', '.join(opts)}")
                print(f"[SOP]  Actions : {', '.join(opts)}")
                self._select_multi(
                    "actions_required",
                    coords["actions_required"],
                    opts,
                    display_id=d_id,
                )

            # ── Maintenance Issues ────────────────────────────────────────────
            if case.maintenance_issues:
                if on_status:
                    on_status("detail", f"[Màn {d_id}] Maint: {case.maintenance_issues}")
                print(f"[SOP]  Maint   : {case.maintenance_issues}")
                self._select_multi(
                    "maintenance_issues",
                    coords["maintenance_issues"],
                    [case.maintenance_issues],
                    display_id=d_id,
                )

            # ── Resolution ────────────────────────────────────────────────────
            if case.resolution:
                if on_status:
                    on_status("detail", f"[Màn {d_id}] Resol: {case.resolution}")
                print(f"[SOP]  Resol   : {case.resolution}")
                self._select_single(
                    "resolution",
                    coords["resolution"],
                    case.resolution,
                    display_id=d_id,
                )

            # ── Comment ───────────────────────────────────────────────────────
            if case.comment:
                if on_status:
                    on_status("detail", f"[Màn {d_id}] Comment: {case.comment}")
                print(f"[SOP]  Comment : {case.comment}")
                self._fill_comment(case.comment, coords)

            t_elapsed = time.perf_counter() - t_start
            print(f"[SOP] DONE (Màn {d_id}) in {t_elapsed:.2f}s: {case.name}\n")
            if on_status:
                on_status("done", f"Màn {d_id} hoàn tất ({t_elapsed:.2f}s)")
            return True

        except Exception as e:
            print(f"[SOP] ERROR (Màn {d_id}): {e}\n")
            if on_status:
                on_status("error", f"Lỗi: {e}")
            return False


# =============================================================================
# STANDALONE HOTKEY MANAGER (Win32)
# =============================================================================

WM_HOTKEY = 0x0312

MOD_NONE  = 0x0000
MOD_ALT   = 0x0001
MOD_CTRL  = 0x0002
MOD_SHIFT = 0x0004

_VK_MAP: dict[str, int] = {
    "f1":  0x70, "f2":  0x71, "f3":  0x72, "f4":  0x73,
    "f5":  0x74, "f6":  0x75, "f7":  0x76, "f8":  0x77,
    "f9":  0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    "esc": 0x1B, "escape": 0x1B,
    "tab": 0x09,
    "space": 0x20, "enter": 0x0D,
    "insert": 0x2D, "ins": 0x2D,
    "home": 0x24,
    "pageup": 0x21, "page_up": 0x21, "page up": 0x21, "pgup": 0x21,
    "pagedown": 0x22, "page_down": 0x22, "page down": 0x22, "pgdn": 0x22,
    "end": 0x23,
    "delete": 0x2E, "del": 0x2E,
}

_MOD_MAP: dict[str, int] = {
    "alt":   MOD_ALT,
    "ctrl":  MOD_CTRL,
    "shift": MOD_SHIFT,
    "ralt":  MOD_ALT,
    "lalt":  MOD_ALT,
}


def _parse_key(combo: str) -> tuple[int, int]:
    parts = [p.strip().lower() for p in combo.split("+")]
    mods = MOD_NONE
    vk   = None
    for part in parts:
        if part in _MOD_MAP:
            mods |= _MOD_MAP[part]
        elif part in _VK_MAP:
            vk = _VK_MAP[part]
    return mods, vk


class SOPHotkeyThread(threading.Thread):
    """Win32 hotkey listener."""

    def __init__(self, hotkeys: dict[int, tuple[int, int, Callable]]) -> None:
        super().__init__(daemon=True, name="SOPHotkeyThread")
        self._hotkeys = hotkeys
        self._running = True
        self._user32 = ctypes.windll.user32

    def run(self) -> None:
        for hk_id, (mods, vk, _) in self._hotkeys.items():
            if not self._user32.RegisterHotKey(None, hk_id, mods, vk):
                print(f"[SOP HK] Failed to register ID={hk_id} mods={hex(mods)} VK={hex(vk)}")

        msg = ctypes.wintypes.MSG()
        try:
            while self._running:
                if self._user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                    if msg.message == WM_HOTKEY:
                        hk_id = msg.wParam
                        if hk_id in self._hotkeys:
                            _, _, callback = self._hotkeys[hk_id]
                            if callable(callback):
                                threading.Thread(target=callback, daemon=True).start()
                    self._user32.TranslateMessage(ctypes.byref(msg))
                    self._user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            for hk_id in self._hotkeys:
                self._user32.UnregisterHotKey(None, hk_id)

    def stop(self) -> None:
        self._running = False
        self._user32.PostThreadMessageW(self.ident, 0, 0, 0)


class SOPHotkeyManager:
    """
    Quản lý hotkey riêng cho SOP tool.
    Hỗ trợ các phím đơn (Insert, Home, PageUp, PageDown, End), phím chuyển màn hình (F6), và tổ hợp.
    """

    def __init__(
        self,
        cfg,
        on_trigger_case: Optional[Callable[[str], None]] = None,
        on_toggle_display: Optional[Callable[[], None]] = None,
        on_toggle_sop_type: Optional[Callable[[], None]] = None,
    ) -> None:
        self._cfg = cfg
        self._filler = SOPFormFiller(cfg)
        self._hk_cfg = cfg.hotkeys_cfg
        self._on_trigger_case = on_trigger_case
        self._on_toggle_display = on_toggle_display
        self._on_toggle_sop_type = on_toggle_sop_type
        self._thread: Optional[SOPHotkeyThread] = None
        self._busy = False
        self._lock = threading.Lock()
        self._exit_requested = False

    def start(self) -> None:
        self._filler.warmup()

        hotkeys: dict[int, tuple[int, int, Callable]] = {}
        hk_id = 1

        for i, (case_key, case) in enumerate(SOP_CASES.items(), start=1):
            cfg_key  = f"case_{i}"
            default  = f"alt+{case_key}"
            combo    = self._hk_cfg.get(cfg_key, default)
            mods, vk = _parse_key(combo)
            if vk:
                cb = self._make_callback(case_key, case)
                hotkeys[hk_id] = (mods, vk, cb)
                hk_id += 1

                if mods & MOD_ALT:
                    hotkeys[hk_id] = (mods | MOD_CTRL, vk, cb)
                    hk_id += 1
                    display = f"Alt+{combo.split('+')[-1].upper()} (L/R)"
                else:
                    display = combo.upper()

                print(f"[SOP HK] {display:14} -> {case.name}")

        # Hotkey chuyển đổi màn hình (Toggle Display - F6)
        if self._on_toggle_display:
            toggle_combo = self._hk_cfg.get("toggle_display", "f6")
            t_mods, t_vk = _parse_key(toggle_combo)
            if t_vk:
                hotkeys[hk_id] = (t_mods, t_vk, self._on_toggle_display)
                hk_id += 1
                print(f"[SOP HK] {toggle_combo.upper():14} -> Chuyển đổi Màn hình")

        # Hotkey chuyển đổi loại SOP (Toggle SOP Type SUSPECT <-> CHRF - nếu có trong config)
        if self._on_toggle_sop_type:
            type_combo = self._hk_cfg.get("toggle_type")
            if type_combo:
                tp_mods, tp_vk = _parse_key(type_combo)
                if tp_vk:
                    hotkeys[hk_id] = (tp_mods, tp_vk, self._on_toggle_sop_type)
                    hk_id += 1
                    print(f"[SOP HK] {type_combo.upper():14} -> Chuyển đổi Loại SOP (SUSPECT <-> CHRF)")

        # Exit hotkey
        exit_combo = self._hk_cfg.get("exit", "ctrl+esc")
        exit_mods, exit_vk = _parse_key(exit_combo)
        if exit_vk and (exit_mods != MOD_NONE or exit_vk != 0x1B):
            hotkeys[hk_id] = (exit_mods, exit_vk, self._on_exit)

        self._thread = SOPHotkeyThread(hotkeys)
        self._thread.start()

    def _make_callback(self, case_key: str, case: SOPCase) -> Callable:
        def cb():
            if self._on_trigger_case:
                self._on_trigger_case(case_key)
            else:
                with self._lock:
                    if self._busy:
                        print("[SOP] Đang bận điền form, bỏ qua...")
                        return
                    self._busy = True
                try:
                    active_type = self._cfg.get_active_sop_type()
                    type_cases = SOP_CASES_BY_TYPE.get(active_type, SUSPECT_CASES)
                    if active_type == "CHRF":
                        map_chrf = {
                            "f1": "c1",
                            "f2": "c2",
                            "f3": "c3",
                            "f4": "c4",
                            "f5": "c5",
                            "f6": "c6",
                        }
                        actual_key = map_chrf.get(case_key, case_key)
                    else:
                        actual_key = case_key
                    resolved_case = type_cases.get(actual_key, case)
                    self._filler.fill(resolved_case)
                finally:
                    self._busy = False
        return cb

    def _on_exit(self) -> None:
        self._exit_requested = True

    def stop(self) -> None:
        if self._thread:
            self._thread.stop()
            self._thread.join(timeout=2.0)

    def wait_for_exit(self) -> None:
        while not self._exit_requested:
            time.sleep(0.2)
