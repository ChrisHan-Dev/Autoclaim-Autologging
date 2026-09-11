"""
sop_main.py — SOP Logging Automation (Multi-Display Support)
============================================================
Runs STANDALONE, independent of auto_claim main.py.
Supports independent display management (Display 4 Main & Display 3) with a single Popup HUD.

Commands:
  python sop_main.py                                   # Run SOP auto-logging (HUD + Hotkeys)
  python sop_main.py calibrate [--display 3|4]        # Calibrate SOP form coords for Display 3 or 4
  python sop_main.py calibrate_options [--display 3|4]# Calibrate dropdown options geometry
  python sop_main.py status                            # View current SOP config
  python sop_main.py test --case 1 [--display 3|4]     # Direct test filling a case

Default hotkeys:
  F6      — Toggle between displays in the active cycle
  F7      — Toggle SOP Type (SUSPECT <-> CHRF)
  Insert  — Fill Case 1
  Home    — Fill Case 2
  PageUp  — Fill Case 3
  PageDown— Fill Case 4
  End     — Fill Case 5
  Delete  — Fill Case 6
  Ctrl+ESC— Exit
"""

import sys
import argparse
import signal
import threading
import time
import os

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from auto_logging.sop_config import SOPConfig
from auto_logging.sop_hud import SOPStatusHUD
from auto_logging.sop_logging import (
    SOPHotkeyManager,
    SOPFormFiller,
    SOP_CASES,
    SUSPECT_CASES,
    CHRF_CASES,
    SOP_CASES_BY_TYPE,
)


# ─────────────────────────────────────────────────────────────────────────────
# Banner
# ─────────────────────────────────────────────────────────────────────────────

def print_banner(cfg: SOPConfig) -> None:
    hk = cfg.hotkeys_cfg
    active_disp = cfg.get_active_display()
    active_type = cfg.get_active_sop_type()
    active_prof = cfg.get_active_profile()
    pair = cfg.get_active_pair()

    print("\n" + "=" * 60)
    print("  📋 [SOP] SOP Logging Automation (Multi-Display & Multi-Type)")
    print("=" * 60)
    print(f"  Config       : {cfg._path}")
    print(f"  Admin        : {'[OK] Running as Administrator' if is_admin() else '[WARN] Standard User'}")
    print(f"  Profile      : [{active_prof.upper()}] (Switch via HUD or --profile)")
    print(f"  Active Disp  : DISPLAY {active_disp}")
    print(f"  Active Type  : [{active_type}] (Switch via HUD dropdown)")
    for d in pair:
        c = cfg.is_calibrated(d)
        g = bool(cfg.get_dropdown_geometry(d))
        nd = f"Display {d}"
        form_status = "[OK]" if c else "[--] Not calibrated"
        opt_status = "[OK]" if g else "[--] Not calibrated"
        print(f"  {nd:12} : Form: {form_status} | Options: {opt_status}")
    print()
    print("  -- Hotkeys -------------------------------------------------------------")
    toggle_key = hk.get("toggle_display", "f6").upper()
    cycle_str = " <-> ".join(f"Disp {d}" for d in pair) if len(pair) > 1 else f"Disp {pair[0]}"
    print(f"  {toggle_key:10} -> Switch {cycle_str}")
    if active_type == "CHRF":
        print(f"  {'INSERT':10} -> CHRF 1 (Align + Place / Success)")
        print(f"  {'HOME':10} -> CHRF 2 (Home actuator / Success)")
        print(f"  {'PAGE UP':10} -> CHRF 3 (Home + Align + Place / Success)")
        print(f"  {'PAGE DN':10} -> CHRF 4 (Home / Axes not resp / CHD no payl)")
        print(f"  {'END':10} -> CHRF 5 (Home / Sensor malf / CHD no payl)")
        print(f"  {'DELETE':10} -> CHRF 6 (Align + Ext / Damaged / CHD payl)")
    else:
        for i, (key_default, case) in enumerate(SUSPECT_CASES.items(), start=1):
            key_name = hk.get(f"case_{i}", key_default).upper()
            print(f"  {key_name:10} -> {case.name}")
    print()
    print(f"  {'Ctrl+ESC':10} -> Exit")
    print("=" * 60 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Status command
# ─────────────────────────────────────────────────────────────────────────────

def cmd_status(cfg: SOPConfig) -> None:
    print("\n=== SOP Config Status (Multi-Display & Multi-Type) ===")
    print(f"  File         : {cfg._path}")
    print(f"  Admin        : {'YES (Administrator)' if is_admin() else 'NO (Standard User)'}")
    print(f"  Active Profile: {cfg.get_active_profile().upper()}")
    print(f"  Active Disp  : Display {cfg.get_active_display()}")
    print(f"  Active Type  : {cfg.get_active_sop_type()}")
    print()

    pair = cfg.get_active_pair()
    for d in pair:
        name = f"Display {d}"
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
    cycle_str = " <-> ".join(f"Disp {d}" for d in pair) if len(pair) > 1 else f"Disp {pair[0]}"
    print(f"    {hk.get('toggle_display', 'f6').upper():10} -> Switch {cycle_str}")
    print("    [SUSPECT]")
    for i, (key_default, case) in enumerate(SUSPECT_CASES.items(), start=1):
        cfg_key = f"case_{i}"
        print(f"      {hk.get(cfg_key, key_default).upper():10} -> {case.name}")
    print("    [CHRF]")
    print(f"      {'INSERT':10} -> CHRF 1 (Align + Place / Success)")
    print(f"      {'HOME':10} -> CHRF 2 (Home actuator / Success)")
    print(f"      {'PAGE UP':10} -> CHRF 3 (Home + Align + Place / Success)")
    print(f"      {'PAGE DN':10} -> CHRF 4 (Home / Axes not resp / CHD no payl)")
    print(f"      {'END':10} -> CHRF 5 (Home / Sensor malf / CHD no payl)")
    print(f"      {'DELETE':10} -> CHRF 6 (Align + Ext / Damaged / CHD payl)")
    print(f"    {'Ctrl+ESC':10} -> Exit\n")


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
    """Check Administrator privileges and note status."""
    if not is_admin():
        print("[INFO] Running as Standard User.")
        print("[INFO] (To run with full Administrator privileges, use Run_SOP_Admin.bat)")


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
        description="SOP Logging Automation (Standalone & Multi-Display Support)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python sop_main.py                             # Run SOP auto-logging (Popup HUD + Hotkeys)
  python sop_main.py calibrate --display 3       # Calibrate form for Display 3
  python sop_main.py calibrate --display 4       # Calibrate form for Display 4 (Main)
  python sop_main.py calibrate_options --display 3# Calibrate dropdown options Display 3
  python sop_main.py calibrate_options --display 4# Calibrate dropdown options Display 4
  python sop_main.py test --case 1 --display 3   # Test filling Case 1 on Display 3
  python sop_main.py status                      # View display coordinates
        """
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "test", "calibrate", "calibrate_options", "status"],
        help="Command to run (default: run)",
    )
    parser.add_argument(
        "--display", "--monitor",
        type=int,
        choices=[1, 2, 3, 4],
        default=None,
        dest="display",
        help="Select display (1, 2, 3, or 4; default: active_display)",
    )
    parser.add_argument(
        "--pair",
        nargs="+",
        type=int,
        choices=[1, 2, 3, 4],
        default=None,
        help="Select active display cycle (e.g. --pair 4 3 or --pair 2 3 4)",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="Select active profile (e.g. --profile home or --profile office)",
    )
    parser.add_argument(
        "--case",
        type=int,
        default=1,
        choices=[1, 2, 3, 4, 5, 6],
        help="Case index to test (1-6, default: 1)",
    )
    args = parser.parse_args()

    if args.command != "status":
        ensure_admin()

    cfg = SOPConfig()

    if args.profile:
        try:
            cfg.switch_profile(args.profile)
            print(f"[SOP] Switched to profile: {args.profile.upper()}")
        except KeyError as e:
            print(f"[SOP] Warning: {e}")

    if args.pair:
        cfg.set_active_pair(*args.pair)
        cfg.set_active_display(args.pair[0])
        pair_str = " and ".join(str(p) for p in args.pair)
        print(f"[SOP] Updated active display list: {pair_str}")

    if args.display is not None and args.command == "run":
        cfg.set_active_display(args.display)

    # ── status ────────────────────────────────────────────────────────────────
    if args.command == "status":
        cmd_status(cfg)
        return

    # ── calibrate ─────────────────────────────────────────────────────────────
    if args.command == "calibrate":
        from auto_logging.sop_calibrate import SOPCalibrationTool
        tool = SOPCalibrationTool(cfg, display_id=args.display)
        tool.run()
        return

    # ── calibrate_options ──────────────────────────────────────────────────────
    if args.command == "calibrate_options":
        from auto_logging.sop_calibrate import SOPOptionCalibrator
        cal = SOPOptionCalibrator(cfg, display_id=args.display)
        cal.run()
        return

    # ── test ──────────────────────────────────────────────────────────────────
    if args.command == "test":
        disp_id = args.display if args.display is not None else cfg.get_active_display()
        case_key = f"f{args.case}"
        case = SOP_CASES.get(case_key, SOP_CASES["f1"])
        print("\n" + "=" * 55)
        print(f"  🧪 TEST SOP AUTO-FILL: {case.name} (DISPLAY {disp_id})")
        print("=" * 55)
        print(f"  Please focus the mouse / open the SOP form on Display {disp_id}.")
        print("  Tool will start in:")
        for sec in range(3, 0, -1):
            print(f"    [{sec}]...")
            time.sleep(1.0)
        print(f"\n  >>> FILLING FORM ON DISPLAY {disp_id}...")
        filler = SOPFormFiller(cfg)
        filler.fill(case, display_id=disp_id)
        print(f"  ✅ TEST DISPLAY {disp_id} COMPLETED!\n")
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
        print(f"[SOP] Switched active mode to DISPLAY {display_id}")
        filler.warmup(display_id)

    def on_toggle_display():
        if hud:
            hud.toggle_display()
        else:
            cur = cfg.get_active_display()
            pair = cfg.get_active_pair()
            if cur in pair:
                idx = (pair.index(cur) + 1) % len(pair)
                nxt = pair[idx]
            else:
                nxt = pair[0] if pair else 4
            cfg.set_active_display(nxt)
            print(f"[SOP] Switched to Display {nxt}")

    def on_switch_sop_type(new_type: str):
        print(f"[SOP] Switched SOP Type to: {new_type}")

    def on_toggle_sop_type():
        if hud:
            hud.toggle_sop_type()
        else:
            cur = cfg.get_active_sop_type()
            nxt = "CHRF" if cur == "SUSPECT" else "SUSPECT"
            cfg.set_active_sop_type(nxt)
            print(f"[SOP] Switched SOP Type to: {nxt}")

    def on_trigger_case(case_key: str):
        with busy_lock:
            if is_busy[0]:
                print("[SOP] Busy filling form, skipping...")
                return
            is_busy[0] = True

        current_type = cfg.get_active_sop_type()
        type_cases = SOP_CASES_BY_TYPE.get(current_type, SUSPECT_CASES)

        # Map hotkeys f1..f6 to c1..c6 when in CHRF mode
        if current_type == "CHRF":
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

        case = type_cases.get(actual_key)
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
                print(f"[SOP] Error: {e}")
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

    def on_switch_profile(profile_name: str):
        print(f"[SOP] Switched to Profile: {profile_name.upper()}")
        filler.warmup(cfg.get_active_display())

    pair = cfg.get_active_pair()
    pair_str = " <-> ".join(f"Disp {m}" for m in pair) if len(pair) > 1 else f"Disp {pair[0]}"

    # Start hotkey manager
    hk_mgr = SOPHotkeyManager(
        cfg,
        on_trigger_case=on_trigger_case,
        on_toggle_display=on_toggle_display,
        on_toggle_sop_type=on_toggle_sop_type,
    )
    hk_mgr.start()

    # Start HUD
    hud = SOPStatusHUD(
        cfg,
        on_trigger_case=on_trigger_case,
        on_exit=on_exit,
        on_switch_display=on_switch_display,
        on_switch_sop_type=on_switch_sop_type,
        on_switch_profile=on_switch_profile,
    )

    # Handle Ctrl+C
    def _sigint(sig, frame):
        print("\n[SOP] Ctrl+C — exiting...")
        on_exit()
        sys.exit(0)

    signal.signal(signal.SIGINT, _sigint)

    print("[SOP] Running Popup HUD and listening for hotkeys:")
    print(f"      F6       -> Toggle {pair_str}")
    print("      F7       -> Toggle SOP Type (SUSPECT <-> CHRF)")
    print("      INSERT   -> Case 1 (All cam / Align+Extract / Success)")
    print("      HOME     -> Case 2 (No cam / No action / Unsuccessful)")
    print("      PAGE UP  -> Case 3 (All cam / Not pickable)")
    print("      PAGE DN  -> Case 4 (All cam / Align+Ext / CHD)")
    print("      END      -> Case 5 (All cam / No action / No case / Success)")
    print("      DELETE   -> Case 6 (All cam / No action / Rogue / CHD)")
    print("      (Or click directly on Popup HUD buttons)")
    print("      Close Popup HUD or press Ctrl+C to exit.\n")

    try:
        hud.run()
    finally:
        on_exit()
        print("[SOP] Exited.")


if __name__ == "__main__":
    main()
