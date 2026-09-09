"""
sop_display.py — Multi-Monitor helper for Windows (Matches Windows Display Settings 1, 2, 3, 4)
================================================================================================
Quản lý và định vị toạ độ chính xác theo đúng số thứ tự màn hình trong Windows Settings:
  - Màn hình 1: Laptop Screen (-1920, -416, 1536x960)
  - Màn hình 2: Top Ultrawide (217, -1440, 3440x1440)
  - Màn hình 3: Right Monitor (1920, 0, 1920x1080)
  - Màn hình 4: Main Monitor  (0, 0, 1920x1080)
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
from typing import TypedDict


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wt.DWORD),
        ("szDevice", wt.WCHAR * 32),
    ]


class DISPLAY_DEVICEW(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD),
        ("DeviceName", wt.WCHAR * 32),
        ("DeviceString", wt.WCHAR * 128),
        ("StateFlags", wt.DWORD),
        ("DeviceID", wt.WCHAR * 128),
        ("DeviceKey", wt.WCHAR * 128),
    ]


class MonitorInfo(TypedDict):
    id: int
    name: str
    is_primary: bool
    x: int
    y: int
    width: int
    height: int
    device: str


def get_windows_monitors() -> list[MonitorInfo]:
    """
    Lấy danh sách tất cả các màn hình kết nối trên Windows.
    Đánh số ID (1, 2, 3, 4...) KHỚP 100% với số hiển thị trong Windows Display Settings.
    """
    user32 = ctypes.windll.user32

    # 1. Lấy danh sách các GDI device đang gắn vào desktop theo thứ tự Windows
    active_device_order: list[str] = []
    dev = DISPLAY_DEVICEW()
    dev.cb = ctypes.sizeof(DISPLAY_DEVICEW)
    i = 0
    while user32.EnumDisplayDevicesW(None, i, ctypes.byref(dev), 0):
        # StateFlags & 1 == DISPLAY_DEVICE_ATTACHED_TO_DESKTOP
        if dev.StateFlags & 1:
            active_device_order.append(dev.DeviceName)
        i += 1

    # Tạo map từ tên device (vd: \\.\DISPLAY7) sang số thứ tự Windows (1, 2, 3, 4)
    device_to_win_num: dict[str, int] = {
        name: idx for idx, name in enumerate(active_device_order, start=1)
    }

    # 2. Lấy toạ độ thực tế của từng màn hình qua EnumDisplayMonitors
    raw_monitors = {}

    def _enum_proc(h_monitor, hdc_monitor, lprc_monitor, dw_data):
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if user32.GetMonitorInfoW(h_monitor, ctypes.byref(info)):
            dev_name = str(info.szDevice)
            raw_monitors[dev_name] = {
                "is_primary": bool(info.dwFlags & 1),
                "x": info.rcMonitor.left,
                "y": info.rcMonitor.top,
                "width": info.rcMonitor.right - info.rcMonitor.left,
                "height": info.rcMonitor.bottom - info.rcMonitor.top,
                "device": dev_name,
            }
        return True

    MONITORENUMPROC = ctypes.WINFUNCTYPE(
        ctypes.c_bool, wt.HMONITOR, wt.HDC, ctypes.POINTER(RECT), wt.LPARAM
    )
    user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(_enum_proc), 0)

    result: list[MonitorInfo] = []
    for dev_name in active_device_order:
        if dev_name in raw_monitors:
            mon = raw_monitors[dev_name]
            win_id = device_to_win_num.get(dev_name, len(result) + 1)
            role = "Main" if mon["is_primary"] else "Phụ"
            result.append({
                "id": win_id,
                "name": f"Màn hình {win_id} ({role})",
                "is_primary": mon["is_primary"],
                "x": mon["x"],
                "y": mon["y"],
                "width": mon["width"],
                "height": mon["height"],
                "device": dev_name,
            })

    return result


def get_monitor_bounds(display_id: int = 4) -> tuple[int, int, int, int]:
    """
    Trả về (x, y, width, height) của màn hình theo số Windows Display (ví dụ: 1, 2, 3, 4).
    """
    monitors = get_windows_monitors()
    for m in monitors:
        if m["id"] == display_id:
            return m["x"], m["y"], m["width"], m["height"]

    # Fallback tìm primary nếu display_id không tồn tại
    for m in monitors:
        if m["is_primary"]:
            return m["x"], m["y"], m["width"], m["height"]

    if monitors:
        return monitors[0]["x"], monitors[0]["y"], monitors[0]["width"], monitors[0]["height"]

    return 0, 0, 1920, 1080
