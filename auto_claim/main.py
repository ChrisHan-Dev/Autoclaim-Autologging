"""
main.py — Teleops GUI Automation Tool (Terminal + Popup)
Chạy từ terminal, hiện popup nhỏ trạng thái.

Cách dùng:
    python main.py              # Chạy automation (popup + terminal)
    python main.py calibrate    # Hiệu chỉnh vùng màn hình
    python main.py status       # Xem trạng thái config hiện tại
"""

import os
import sys
import signal
import threading
import time
import queue
import argparse

# Đảm bảo đường dẫn gốc được thêm vào sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from auto_claim.config import ConfigManager
from auto_claim.logger import Logger
from auto_claim.workflow import WorkflowEngine
from auto_claim.hotkeys import HotkeyManager
from auto_claim.status_window import StatusWindow


# ── Terminal status printer ──────────────────────────────────────────────────

class TerminalStatus:
    """In trạng thái automation ra terminal theo thời gian thực."""

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
    """Gửi update tới cả popup và terminal cùng lúc."""

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
    """Tự động bật UAC prompt để chạy lại dưới quyền Administrator nếu chưa có."""
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


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Teleops GUI Automation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Hotkeys (hoạt động toàn hệ thống):
  F8   — Bật / Tắt automation
  F9   — Dừng khẩn cấp
  F10  — Tạm dừng / Tiếp tục
  ESC  — Thoát chương trình

Ví dụ:
  python main.py              # Chạy automation
  python main.py calibrate    # Hiệu chỉnh màn hình
  python main.py status       # Xem trạng thái config
        """
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "calibrate", "status"],
        help="Lệnh cần chạy (mặc định: run)",
    )
    args = parser.parse_args()

    # Tự động nâng quyền Administrator (trừ lệnh status)
    if args.command != "status":
        ensure_admin()

    cfg = ConfigManager()
    log = Logger(cfg.logging_cfg)

    # ── calibrate ──────────────────────────────────────────────────────
    if args.command == "calibrate":
        from auto_claim.calibrate import CalibrationTool
        log.info("Bắt đầu hiệu chỉnh...")
        calibrator = CalibrationTool(cfg, log)
        calibrator.run()
        log.info("Hiệu chỉnh xong.")
        return

    # ── status ─────────────────────────────────────────────────────────
    if args.command == "status":
        print("\n=== Teleops Automation — Config Status ===")
        print(f"  Config file      : {cfg._path}")
        print(f"  Calibrated       : {'YES' if cfg.is_calibrated() else 'NO  ← run: python main.py calibrate'}")
        print(f"  Username         : {cfg.username or '(chưa đặt)'}")
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
        print("\n⚠️  Chưa hiệu chỉnh! Hãy chạy trước:")
        print("     python main.py calibrate\n")
        sys.exit(1)

    # Thread-safe queue cho events
    ui_queue = queue.Queue()

    # Tạo popup + terminal updater
    terminal = TerminalStatus()
    status_window = StatusWindow(cfg)
    combined = CombinedUpdater(status_window, terminal)

    # Khởi động engine trong thread nền
    engine = WorkflowEngine(cfg, log, on_update=combined.update)
    engine_thread = threading.Thread(target=engine.start, daemon=True, name="WorkflowEngine")
    engine_thread.start()

    # Đăng ký hotkeys toàn hệ thống
    hk_manager = HotkeyManager(cfg.get("hotkeys", {}), engine)
    hk_manager.start()

    print("\n" + "="*50)
    print("  🤖 Teleops Auto Claim — Running")
    print("="*50)
    print(f"  User      : {cfg.username or '(chưa đặt)'}")
    print(f"  Blocklist : {cfg.site_blocklist or 'Không có'}")
    print()
    hk = cfg.get("hotkeys", {})
    print(f"  {hk.get('toggle', 'F8').upper():6} — Bật / Tắt")
    print(f"  {hk.get('emergency_stop', 'F9').upper():6} — Dừng khẩn cấp")
    print(f"  {hk.get('pause_resume', 'F10').upper():6} — Tạm dừng / Tiếp tục")
    print(f"  {'ESC':6} — Thoát")
    print("="*50 + "\n")

    # Xử lý queue từ popup (chỉ EXIT)
    def process_queue_callback(q: queue.Queue):
        try:
            while True:
                msg = q.get_nowait()
                if msg == "EXIT":
                    engine.safe_exit()
                    hk_manager.stop()
                    status_window.stop()
        except queue.Empty:
            # Nếu engine thread chết, thoát popup
            if not engine_thread.is_alive():
                status_window.stop()

    # Xử lý Ctrl+C
    def _sigint(sig, frame):
        print("\n[!] Ctrl+C — đang thoát...")
        engine.safe_exit()
        hk_manager.stop()
        status_window.stop()

    signal.signal(signal.SIGINT, _sigint)

    # Chạy popup trên main thread (blocking)
    # Terminal vẫn in song song qua TerminalStatus
    status_window.build_and_run(ui_queue, process_queue_callback)

    # Sau khi popup đóng
    engine.safe_exit()
    hk_manager.stop()
    print("[✓] Đã thoát.")


if __name__ == "__main__":
    main()
