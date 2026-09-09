"""
sop_main.py — SOP Logging Automation (Multi-Display Support)
============================================================
Chạy RIÊNG, KHÔNG cần main.py đang chạy.
Hỗ trợ quản lý độc lập các Màn hình (Màn 4 Main và Màn 3) với 1 Popup HUD duy nhất.

Lệnh:
  python sop_main.py                                   # Chạy SOP auto-logging (HUD + Hotkeys)
  python sop_main.py calibrate [--display 3|4]        # Hiệu chỉnh toạ độ form SOP cho Màn 3 hoặc Màn 4
  python sop_main.py calibrate_options [--display 3|4]# Hiệu chỉnh toạ độ dropdown options
  python sop_main.py status                            # Xem config SOP hiện tại
  python sop_main.py test --case 1 [--display 3|4]     # Test trực tiếp

Hotkey mặc định:
  F6      — Đổi qua lại Màn 4 (Main) <-> Màn 3 (Phụ)
  Insert  — Fill Case 1
  Home    — Fill Case 2
  PageUp  — Fill Case 3
  PageDown— Fill Case 4
  End     — Fill Case 5
  Ctrl+ESC— Thoát
"""

import sys
import argparse
import signal
import threading
import time

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# Thêm thư mục gốc vào path
import os
sys.path.insert(0, os.path.dirname(__file__))

from sop.sop_config import SOPConfig
from sop.sop_hud import SOPStatusHUD
from automation.sop_logging import SOPHotkeyManager, SOPFormFiller, SOP_CASES


# ─────────────────────────────────────────────────────────────────────────────
# Banner
# ─────────────────────────────────────────────────────────────────────────────

def print_banner(cfg: SOPConfig) -> None:
    hk = cfg.hotkeys_cfg
    active_disp = cfg.get_active_display()
    pair = cfg.get_active_pair()
    d1, d2 = pair[0], pair[1]

    c1 = cfg.is_calibrated(d1)
    c2 = cfg.is_calibrated(d2)
    g1 = bool(cfg.get_dropdown_geometry(d1))
    g2 = bool(cfg.get_dropdown_geometry(d2))

    n1 = f"Màn {d1} (Main)" if d1 == 4 else f"Màn {d1}"
    n2 = f"Màn {d2} (Main)" if d2 == 4 else f"Màn {d2}"

    print("\n" + "=" * 60)
    print("  📋 [SOP] SOP Logging Automation (Multi-Display)")
    print("=" * 60)
    print(f"  Config       : {cfg._path}")
    print(f"  Admin        : {'[OK] Running as Administrator' if is_admin() else '[WARN] Standard User'}")
    print(f"  Active Màn   : MÀN HÌNH {active_disp}")
    print(f"  {n1:12} : Form: {'[OK]' if c1 else '[--] Chưa calib'} | Options: {'[OK]' if g1 else '[--] Chưa calib'}")
    print(f"  {n2:12} : Form: {'[OK]' if c2 else '[--] Chưa calib'} | Options: {'[OK]' if g2 else '[--] Chưa calib'}")
    print()
    print("  -- Phím tắt -------------------------------------------------------------")
    toggle_key = hk.get("toggle_display", "f6").upper()
    print(f"  {toggle_key:10} -> Chuyển đổi Màn {d1} <-> Màn {d2}")
    for i, (key_default, case) in enumerate(SOP_CASES.items(), start=1):
        key_name = hk.get(f"case_{i}", key_default).upper()
        print(f"  {key_name:10} -> {case.name}")
    print()
    print(f"  {'Ctrl+ESC':10} -> Thoát")
    print("=" * 60 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Status command
# ─────────────────────────────────────────────────────────────────────────────

def cmd_status(cfg: SOPConfig) -> None:
    print("\n=== SOP Config Status (Multi-Display) ===")
    print(f"  File         : {cfg._path}")
    print(f"  Admin        : {'YES (Administrator)' if is_admin() else 'NO (Standard User)'}")
    print(f"  Active Màn   : Màn hình {cfg.get_active_display()}")
    print()

    pair = cfg.get_active_pair()
    for d in pair:
        name = f"Màn hình {d} (Main)" if d == 4 else f"Màn hình {d} (Phụ)"
        cal = "YES" if cfg.is_calibrated(d) else "NO"
        geom_ok = "YES" if bool(cfg.get_dropdown_geometry(d)) else "NO"
        print(f"── [{name}] ── Form Calibrated: {cal} | Options Calibrated: {geom_ok}")
        coords = cfg.get_form_coords(d)
        for k, v in coords.items():
            ok = "[OK]" if v.get("x", 0) != 0 else "[--]"
            print(f"    {ok} {k:22}: x={v.get('x', 0):5}, y={v.get('y', 0):5}")
        print()

    print("  Hotkeys:")
    hk = cfg.hotkeys_cfg
    d1, d2 = pair[0], pair[1]
    print(f"    {hk.get('toggle_display', 'f6').upper():10} -> Đổi Màn {d1} <-> Màn {d2}")
    for i, (key_default, case) in enumerate(SOP_CASES.items(), start=1):
        cfg_key = f"case_{i}"
        print(f"    {hk.get(cfg_key, key_default).upper():10} -> {case.name}")
    print(f"    {'Ctrl+ESC':10} -> Thoát\n")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def is_admin() -> bool:
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def ensure_admin() -> None:
    """Tự động bật UAC prompt để khởi động lại dưới quyền Admin nếu chưa có."""
    if is_admin():
        return
    import ctypes
    import sys
    try:
        params = " ".join([f'"{arg}"' for arg in sys.argv])
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, None, 1
        )
        if ret > 32:
            sys.exit(0)
    except Exception as e:
        print(f"[WARN] Không thể tự động nâng quyền Admin: {e}")


def disable_quick_edit() -> None:
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        hStdin = kernel32.GetStdHandle(-10)  # STD_INPUT_HANDLE
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(hStdin, ctypes.byref(mode)):
            ENABLE_QUICK_EDIT_MODE = 0x0040
            ENABLE_EXTENDED_FLAGS = 0x0080
            new_mode = (mode.value & ~ENABLE_QUICK_EDIT_MODE) | ENABLE_EXTENDED_FLAGS
            kernel32.SetConsoleMode(hStdin, new_mode)
    except Exception:
        pass


def main() -> None:
    disable_quick_edit()
    parser = argparse.ArgumentParser(
        description="SOP Logging Automation (Độc lập & Hỗ trợ Đa Màn hình)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ:
  python sop_main.py                             # Chạy SOP auto-logging (Popup HUD + Hotkeys)
  python sop_main.py calibrate --display 3       # Calibrate form cho Màn 3
  python sop_main.py calibrate --display 4       # Calibrate form cho Màn 4 (Main)
  python sop_main.py calibrate_options --display 3# Calibrate dropdown options Màn 3
  python sop_main.py calibrate_options --display 4# Calibrate dropdown options Màn 4
  python sop_main.py test --case 1 --display 3   # Test điền Case 1 trên Màn 3
  python sop_main.py status                      # Xem toạ độ các màn hình
        """
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "test", "calibrate", "calibrate_options", "status"],
        help="Lệnh (mặc định: run)",
    )
    parser.add_argument(
        "--display", "--monitor",
        type=int,
        choices=[1, 2, 3, 4],
        default=None,
        dest="display",
        help="Chọn màn hình (1, 2, 3, hoặc 4; mặc định: 3 hoặc 4)",
    )
    parser.add_argument(
        "--case",
        type=int,
        default=1,
        choices=[1, 2, 3, 4, 5],
        help="Số thứ tự case muốn test (1-5, mặc định: 1)",
    )
    args = parser.parse_args()

    if args.command != "status":
        ensure_admin()

    cfg = SOPConfig()

    # ── status ────────────────────────────────────────────────────────────────
    if args.command == "status":
        cmd_status(cfg)
        return

    # ── calibrate ─────────────────────────────────────────────────────────────
    if args.command == "calibrate":
        from sop.sop_calibrate import SOPCalibrationTool
        tool = SOPCalibrationTool(cfg, display_id=args.display)
        tool.run()
        return

    # ── calibrate_options ──────────────────────────────────────────────────────
    if args.command == "calibrate_options":
        from sop.sop_calibrate import SOPOptionCalibrator
        cal = SOPOptionCalibrator(cfg, display_id=args.display)
        cal.run()
        return

    # ── test ──────────────────────────────────────────────────────────────────
    if args.command == "test":
        disp_id = args.display if args.display is not None else cfg.get_active_display()
        case_key = f"f{args.case}"
        case = SOP_CASES.get(case_key, SOP_CASES["f1"])
        print("\n" + "=" * 55)
        print(f"  🧪 TEST SOP AUTO-FILL: {case.name} (MÀN HÌNH {disp_id})")
        print("=" * 55)
        print(f"  Vui lòng chuyển chuột / mở sẵn form SOP trên Màn hình {disp_id}.")
        print("  Tool sẽ bắt đầu sau:")
        for sec in range(3, 0, -1):
            print(f"    [{sec}]...")
            time.sleep(1.0)
        print(f"\n  >>> ĐANG ĐIỀN FORM TRÊN MÀN {disp_id}...")
        filler = SOPFormFiller(cfg)
        filler.fill(case, display_id=disp_id)
        print(f"  ✅ TEST MÀN {disp_id} HOÀN TẤT!\n")
        return

    # ── run ───────────────────────────────────────────────────────────────────
    print_banner(cfg)

    filler = SOPFormFiller(cfg)
    filler.warmup()

    hud = None
    busy_lock = threading.Lock()
    is_busy = [False]

    def on_status(kind: str, msg: str):
        if hud is None:
            return
        if kind == "busy":
            hud.set_busy(msg)
        elif kind == "detail":
            hud.set_detail(msg)
        elif kind == "done":
            hud.set_done(msg)
        elif kind == "error":
            hud.set_error(msg)

    def on_switch_display(display_id: int):
        print(f"[SOP] Đã chuyển chế độ sang MÀN HÌNH {display_id}")
        filler.warmup(display_id)

    def on_toggle_display():
        if hud:
            hud.toggle_display()
        else:
            cur = cfg.get_active_display()
            pair = cfg.get_active_pair()
            nxt = pair[1] if cur == pair[0] else pair[0]
            cfg.set_active_display(nxt)
            print(f"[SOP] Đổi sang Màn hình {nxt}")

    def on_trigger_case(case_key: str):
        with busy_lock:
            if is_busy[0]:
                print("[SOP] Đang bận điền form, bỏ qua...")
                return
            is_busy[0] = True

        case = SOP_CASES.get(case_key)
        if not case:
            with busy_lock:
                is_busy[0] = False
            return

        active_disp = cfg.get_active_display()

        def _worker():
            try:
                if hud:
                    hud.set_busy(case.name)
                filler.fill(case, on_status=on_status, display_id=active_disp)
            except Exception as e:
                print(f"[SOP] Lỗi: {e}")
                if hud:
                    hud.set_error(str(e))
            finally:
                with busy_lock:
                    is_busy[0] = False
                def _reset():
                    time.sleep(1.5)
                    if hud and not is_busy[0]:
                        hud.set_ready()
                threading.Thread(target=_reset, daemon=True).start()

        threading.Thread(target=_worker, daemon=True).start()

    def on_exit():
        if hk_mgr:
            hk_mgr.stop()
        if hud:
            hud.stop()

    pair = cfg.get_active_pair()
    d1, d2 = pair[0], pair[1]

    # Khởi động hotkey manager
    hk_mgr = SOPHotkeyManager(
        cfg,
        on_trigger_case=on_trigger_case,
        on_toggle_display=on_toggle_display,
    )
    hk_mgr.start()

    # Khởi động HUD
    hud = SOPStatusHUD(
        cfg,
        on_trigger_case=on_trigger_case,
        on_exit=on_exit,
        on_switch_display=on_switch_display,
    )

    # Xử lý Ctrl+C
    def _sigint(sig, frame):
        print("\n[SOP] Ctrl+C — đang thoát...")
        on_exit()
        sys.exit(0)

    signal.signal(signal.SIGINT, _sigint)

    print("[SOP] Đang chạy Popup HUD và lắng nghe phím tắt:")
    print(f"      F6       -> Đổi qua lại Màn {d1} (Main) <-> Màn {d2} (Phụ)")
    print("      INSERT   -> Case 1 (All cam / Align+Extract / Success)")
    print("      HOME     -> Case 2 (No cam / No action / Unsuccessful)")
    print("      PAGE UP  -> Case 3 (All cam / Not pickable)")
    print("      PAGE DN  -> Case 4 (All cam / Align+Ext / CHD)")
    print("      END      -> Case 5 (All cam / No action / No case / Success)")
    print("      (Hoặc click trực tiếp các nút trên Popup HUD)")
    print("      Đóng Popup HUD hoặc Ctrl+C để thoát.\n")

    try:
        hud.run()
    finally:
        on_exit()
        print("[SOP] Đã thoát.")


if __name__ == "__main__":
    main()
