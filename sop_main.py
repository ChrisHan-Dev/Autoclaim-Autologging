"""
sop_main.py — SOP Logging Automation (DOC LAP voi autoclaim)
=============================================================
Chay RIENG, KHONG can main.py dang chay.

Lenh:
  python sop_main.py              # Chay SOP auto-logging
  python sop_main.py calibrate    # Hieu chinh toa do form SOP
  python sop_main.py status       # Xem config SOP hien tai

Hotkey mac dinh:
  F1  — Fill Case 1
  F2  — Fill Case 2
  F3  — Fill Case 3
  F4  — Fill Case 4
  ESC — Thoat

(Co the doi hotkey trong sop/sop_config.json)
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

# Them thu muc goc vao path
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
    calibrated = cfg.is_calibrated()
    geom_ok = bool(cfg.get("dropdown_geometry", {}))

    print("\n" + "=" * 55)
    print("  [SOP] SOP Logging Automation")
    print("=" * 55)
    print(f"  Config : {cfg._path}")
    print(f"  Admin  : {'[OK] Running as Administrator' if is_admin() else '[WARN] Standard User'}")
    print(f"  Form   : {'[OK] Calibrated' if calibrated else '[WARN] CHUA calibrate form!'}")
    print(f"  Options: {'[OK] Calibrated' if geom_ok else '[WARN] CHUA calibrate_options!'}")
    if not calibrated:
        print("  -> Chay: python sop_main.py calibrate")
    if not geom_ok:
        print("  -> Chay: python sop_main.py calibrate_options")
    print()
    print("  -- Cases ---------------------------------------------------------------")
    for i, (key_default, case) in enumerate(SOP_CASES.items(), start=1):
        key_name = hk.get(f"case_{i}", key_default).upper()
        print(f"  {key_name:10} -> {case.name}")
    print()
    print(f"  {'[X] / Ctrl+C':10} -> Thoat")
    print("=" * 55 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Status command
# ─────────────────────────────────────────────────────────────────────────────

def cmd_status(cfg: SOPConfig) -> None:
    print("\n=== SOP Config Status ===")
    print(f"  File       : {cfg._path}")
    print(f"  Admin      : {'YES (Administrator)' if is_admin() else 'NO (Standard User)'}")
    print(f"  Calibrated : {'YES' if cfg.is_calibrated() else 'NO'}")
    print()
    print("  Form coordinates:")
    for k, v in cfg.form_coords.items():
        ok = "[OK]" if v.get("x", 0) != 0 else "[--]"
        print(f"  {ok} {k:22}: x={v.get('x', 0):4}, y={v.get('y', 0):4}")
    print()
    print("  Hotkeys:")
    hk = cfg.hotkeys_cfg
    for i, (key_default, case) in enumerate(SOP_CASES.items(), start=1):
        cfg_key = f"case_{i}"
        print(f"  {hk.get(cfg_key, key_default).upper():10} -> {case.name}")
    print(f"  {'[X] / Ctrl+C':10} -> Thoat\n")


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
    """Neu chua co quyen Administrator, tu dong bat UAC prompt de tai khoi dong duoi quyen Admin."""
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
            # Khoi dong tien trinh elevated thanh cong -> thoat tien trinh hien tai
            sys.exit(0)
    except Exception as e:
        print(f"[WARN] Khong the tu dong nang quyen Admin: {e}")


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
        description="SOP Logging Automation (doc lap voi autoclaim)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Vi du:
  python sop_main.py                  # Chay SOP auto-logging (nhan hotkey Alt+F5..F8)
  python sop_main.py test --case 1    # Test truc tiep Case 1 (dem nguoc 3 giay roi tu dong dien)
  python sop_main.py calibrate        # Calibrate toa do cac o dropdown
  python sop_main.py calibrate_options # Calibrate vi tri option trong dropdown
  python sop_main.py status           # Xem config hien tai
        """
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "test", "calibrate", "calibrate_options", "status"],
        help="Lenh (mac dinh: run)",
    )
    parser.add_argument(
        "--case",
        type=int,
        default=1,
        choices=[1, 2, 3, 4, 5],
        help="So thu tu case muon test (1-5, mac dinh: 1)",
    )
    args = parser.parse_args()

    # Tu dong nang quyen Run as Administrator neu dang chay quyen thuong (tru lenh status)
    if args.command != "status":
        ensure_admin()

    # Load SOP config rieng
    cfg = SOPConfig()

    # ── status ────────────────────────────────────────────────────────────────
    if args.command == "status":
        cmd_status(cfg)
        return

    # ── calibrate ─────────────────────────────────────────────────────────────
    if args.command == "calibrate":
        from sop.sop_calibrate import SOPCalibrationTool
        tool = SOPCalibrationTool(cfg)
        tool.run()
        return

    # ── calibrate_options ──────────────────────────────────────────────────────
    if args.command == "calibrate_options":
        from sop.sop_calibrate import SOPOptionCalibrator
        cal = SOPOptionCalibrator(cfg)
        cal.run()
        return

    # ── test ──────────────────────────────────────────────────────────────────
    if args.command == "test":
        case_key = f"f{args.case}"
        case = SOP_CASES.get(case_key, SOP_CASES["f1"])
        print("\n" + "=" * 55)
        print(f"  🧪  TEST SOP AUTO-FILL: {case.name}")
        print("=" * 55)
        print("  Vui long chuyen chuot / mo san form SOP tren man hinh.")
        print("  Tool se bat dau sau:")
        for sec in range(3, 0, -1):
            print(f"    [{sec}]...")
            time.sleep(1.0)
        print("\n  >>> DANG DIEN FORM...")
        filler = SOPFormFiller(cfg)
        filler.fill(case)
        print("  ✅ TEST HOAN TAT!\n")
        return

    # ── run ───────────────────────────────────────────────────────────────────
    if not cfg.is_calibrated():
        print("\n[WARN] Chua calibrate! Hay chay truoc:")
        print("       python sop_main.py calibrate\n")

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

        def _worker():
            try:
                if hud:
                    hud.set_busy(case.name)
                filler.fill(case, on_status=on_status)
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

    # Khoi dong hotkey manager
    hk_mgr = SOPHotkeyManager(cfg, on_trigger_case=on_trigger_case)
    hk_mgr.start()

    # Khoi dong HUD
    hud = SOPStatusHUD(cfg, on_trigger_case=on_trigger_case, on_exit=on_exit)

    # Xu ly Ctrl+C
    def _sigint(sig, frame):
        print("\n[SOP] Ctrl+C — dang thoat...")
        on_exit()
        sys.exit(0)

    signal.signal(signal.SIGINT, _sigint)

    print("[SOP] Đang chạy Popup HUD và lắng nghe phím tắt:")
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
