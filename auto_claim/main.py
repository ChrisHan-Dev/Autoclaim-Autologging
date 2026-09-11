"""
main.py — Teleops GUI Automation Tool (Terminal + Popup)
Runs from terminal with a small floating status popup HUD.

Usage:
    python main.py              # Run automation (popup + terminal)
    python main.py calibrate    # Calibrate screen regions
    python main.py status       # View current config status
"""

import os
import sys
import signal
import threading
import time
import queue
import argparse

# Ensure root dir is in sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from auto_claim.config import ConfigManager
from auto_claim.logger import Logger
from auto_claim.workflow import WorkflowEngine
from auto_claim.hotkeys import HotkeyManager
from auto_claim.status_window import StatusWindow


# ── Terminal status printer ──────────────────────────────────────────────────

class TerminalStatus:
    """Print live automation status to the terminal in real time."""

    _ICONS = {
        "IDLE":           "⬜",
        "SCANNING":       "🔍",
        "CLAIM_FOUND":    "🎯",
        "CLICK_CLAIM":    "🖱 ",
        "WAIT_USERNAME":  "⏳",
        "CLAIM_SUCCESS":  "✅",
        "CLICK_SELECT":   "🖱 ",
        "CLICK_CONNECT":  "🔗",
        "CONNECTED":      "🟢",
        "STOPPED":        "⏹ ",
        "ERROR":          "❌",
        "PAUSED":         "⏸ ",
    }

    def __init__(self):
        self._last_state = ""

    def update(self, state=None, **kwargs):
        if state is None:
            return
        if state == self._last_state:
            return
        self._last_state = state

        icon = self._ICONS.get(state, "•")
        ts = time.strftime("%H:%M:%S")
        print(f"[{ts}] {icon}  {state}", flush=True)


# ── Combined updater ─────────────────────────────────────────────────────────

class CombinedUpdater:
    """Send status updates to both popup HUD and terminal simultaneously."""

    def __init__(self, popup: StatusWindow, terminal: TerminalStatus):
        self._popup = popup
        self._terminal = terminal

    def update(self, **kwargs):
        self._popup.update(**kwargs)
        self._terminal.update(**kwargs)


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
        print("[INFO] (To grant full Admin privileges, run via Run_AutoClaim_Admin.bat)")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Teleops GUI Automation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Hotkeys (system-wide):
  F8   — Toggle automation ON / OFF
  F9   — Emergency Stop
  F10  — Pause / Resume
  ESC  — Exit program

Examples:
  python main.py              # Run automation
  python main.py calibrate    # Calibrate screen regions
  python main.py status       # Check config status
        """
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "calibrate", "status"],
        help="Command to run (default: run)",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="Choose profile (e.g. home / office)",
    )
    args = parser.parse_args()

    # Check Administrator privileges (except status command)
    if args.command != "status":
        ensure_admin()

    cfg = ConfigManager()
    log = Logger(cfg.logging_cfg)

    if args.profile:
        try:
            cfg.switch_profile(args.profile)
            print(f"[AutoClaim] Switched to profile: {args.profile.upper()}")
        except KeyError as e:
            print(f"[AutoClaim] Warning: {e}")

    # ── calibrate ──────────────────────────────────────────────────────
    if args.command == "calibrate":
        from auto_claim.calibrate import CalibrationTool
        log.info("Starting calibration...")
        calibrator = CalibrationTool(cfg, log)
        calibrator.run()
        log.info("Calibration complete.")
        return

    # ── status ─────────────────────────────────────────────────────────
    if args.command == "status":
        print("\n=== Teleops Automation — Config Status ===")
        print(f"  Config file      : {cfg._path}")
        print(f"  Active Profile   : {cfg.get_active_profile().upper()}")
        print(f"  Calibrated       : {'YES' if cfg.is_calibrated() else 'NO  ← run: python main.py calibrate'}")
        print(f"  Username         : {cfg.username or '(not set)'}")
        print(f"  Table region     : {cfg.table_region}")
        print(f"  Type column      : {cfg.type_column}")
        print(f"  Site column      : {cfg.site_column}")
        print(f"  Alarm column     : {cfg.alarm_column}")
        print(f"  Claim column     : {cfg.claim_column}")
        print(f"  Select col       : {cfg.select_column}")
        print(f"  Connect btn      : {cfg.connect_button}")
        print(f"  Site blocklist   : {cfg.site_blocklist}")
        print(f"  Allowed Types    : {cfg.allowed_teleop_types}")
        print(f"  Max Alarm Time   : {cfg.max_alarm_time}")
        print(f"  Header exclusion : {cfg.get('header_exclusion_px', 5)} px")
        return

    # ── run ────────────────────────────────────────────────────────────
    if not cfg.is_calibrated():
        print("\n⚠️  Not calibrated! Please run first:")
        print("     python main.py calibrate\n")
        sys.exit(1)

    # Thread-safe queue for events
    ui_queue = queue.Queue()

    # Create popup + terminal updater
    terminal = TerminalStatus()
    status_window = StatusWindow(cfg)
    combined = CombinedUpdater(status_window, terminal)

    # Start engine in background thread
    engine = WorkflowEngine(cfg, log, on_update=combined.update)
    engine_thread = threading.Thread(target=engine.start, daemon=True, name="WorkflowEngine")
    engine_thread.start()

    # Register system-wide hotkeys
    hk_manager = HotkeyManager(cfg.get("hotkeys", {}), engine)
    hk_manager.start()

    print("\n" + "="*50)
    print("  🤖 Teleops Auto Claim — Running")
    print("="*50)
    print(f"  Profile   : [{cfg.get_active_profile().upper()}] (Switch on popup or via --profile)")
    print(f"  User      : {cfg.username or '(not set)'}")
    print(f"  Blocklist : {cfg.site_blocklist or 'None'}")
    print()
    hk = cfg.get("hotkeys", {})
    print(f"  {hk.get('toggle', 'F8').upper():6} — Start / Stop")
    print(f"  {hk.get('emergency_stop', 'F9').upper():6} — Emergency Stop")
    print(f"  {hk.get('pause_resume', 'F10').upper():6} — Pause / Resume")
    print(f"  {'ESC':6} — Exit")
    print("="*50 + "\n")

    # Handle queue from popup (EXIT only)
    def process_queue_callback(q: queue.Queue):
        try:
            while True:
                msg = q.get_nowait()
                if msg == "EXIT":
                    engine.safe_exit()
                    hk_manager.stop()
                    status_window.stop()
        except queue.Empty:
            # If engine thread dies, close popup
            if not engine_thread.is_alive():
                status_window.stop()

    # Handle Ctrl+C
    def _sigint(sig, frame):
        print("\n[!] Ctrl+C — exiting...")
        engine.safe_exit()
        hk_manager.stop()
        status_window.stop()

    signal.signal(signal.SIGINT, _sigint)

    # Run popup on main thread (blocking)
    # Terminal prints concurrently via TerminalStatus
    status_window.build_and_run(ui_queue, process_queue_callback)

    # After popup closes
    engine.safe_exit()
    hk_manager.stop()
    print("[✓] Exited.")


if __name__ == "__main__":
    main()
