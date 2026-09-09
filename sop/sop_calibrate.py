"""
sop_calibrate.py — SOP Form Calibration Tools (Multi-Display 1, 2, 3, 4)
========================================================================
Gồm 2 bước calibration cho từng màn hình:
  1. python sop_main.py calibrate [--display 3|4]        — Ghi toạ độ tâm các Ô dropdown (nút bấm)
  2. python sop_main.py calibrate_options [--display 3|4] — Ghi toạ độ từng OPTION trong dropdown list
"""

from __future__ import annotations

import time
import tkinter as tk
import pyautogui

from .sop_config import SOPConfig
from .sop_display import get_monitor_bounds, get_windows_monitors


# ── Overlay ──────────────────────────────────────────────────────────────────

class SOPCalibrationOverlay(tk.Toplevel):
    """
    Full-screen semi-transparent overlay định vị chính xác trên màn hình chỉ định.
    User click lần lượt vào từng element để ghi lại toạ độ.
    """

    STEPS: list[tuple[str, str]] = [
        ("vision_functionality", "Step 1/6 — CLICK vào tâm ô [Vision Functionality]"),
        ("actions_required",     "Step 2/6 — CLICK vào tâm ô [Actions Required]"),
        ("maintenance_issues",   "Step 3/6 — CLICK vào tâm ô [Maintenance Issues]"),
        ("resolution",           "Step 4/6 — CLICK vào tâm ô [Resolution]"),
        ("comment",              "Step 5/6 — CLICK vào tâm ô [Comment]"),
        ("send_button",          "Step 6/6 — CLICK vào nút [SEND]"),
    ]

    def __init__(self, display_id: int = 4, master=None) -> None:
        if master is None:
            self._temp_root = tk.Tk()
            self._temp_root.withdraw()
            master = self._temp_root
        else:
            self._temp_root = None

        super().__init__(master)
        self.display_id = display_id
        self.results: dict = {}
        self._step_index: int = 0

        # Lấy kích thước và toạ độ thực tế của màn hình (Màn 3, Màn 4...)
        mx, my, mw, mh = get_monitor_bounds(display_id)

        # Định vị overlay bao phủ toàn bộ màn hình chỉ định
        self.geometry(f"{mw}x{mh}+{mx}+{my}")
        self.overrideredirect(True)
        self.attributes("-alpha", 0.28)
        self.configure(bg="#001428")
        self.attributes("-topmost", True)

        self._canvas = tk.Canvas(
            self, bg="#001428", highlightthickness=0, cursor="crosshair"
        )
        self._canvas.pack(fill="both", expand=True)

        # Instruction label
        self._label = tk.Label(
            self,
            text="",
            font=("Segoe UI", 20, "bold"),
            fg="#00e5ff",
            bg="#001428",
            padx=24,
            pady=12,
        )
        self._label.place(relx=0.5, rely=0.06, anchor="center")

        # Step counter & Display info
        self._counter = tk.Label(
            self,
            text="",
            font=("Segoe UI", 13),
            fg="#607d8b",
            bg="#001428",
        )
        self._counter.place(relx=0.5, rely=0.12, anchor="center")

        self._canvas.bind("<ButtonPress-1>", self._on_click)
        self.bind("<Escape>", lambda _: self.destroy())
        self._set_step(0)

    def _set_step(self, index: int) -> None:
        self._step_index = index
        if index >= len(self.STEPS):
            self.destroy()
            if getattr(self, "_temp_root", None):
                self._temp_root.destroy()
            return
        key, instruction = self.STEPS[index]
        self._label.config(text=f"[MÀN HÌNH {self.display_id}] {instruction}")
        self._counter.config(text=f"{index + 1} / {len(self.STEPS)} — Nhấn ESC để huỷ")
        self._canvas.delete("marker")

    def _on_click(self, event: tk.Event) -> None:
        key, _ = self.STEPS[self._step_index]
        # event.x_root, event.y_root là toạ độ tuyệt đối trên virtual desktop
        self.results[key] = {"x": event.x_root, "y": event.y_root}

        # Vẽ marker
        r = 14
        cx, cy = event.x, event.y
        self._canvas.create_line(cx - r, cy, cx + r, cy, fill="#00e5ff", width=2, tags="marker")
        self._canvas.create_line(cx, cy - r, cx, cy + r, fill="#00e5ff", width=2, tags="marker")
        self._canvas.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, outline="#00e5ff", width=2, tags="marker")

        # Label toạ độ
        self._canvas.create_text(
            cx + 20, cy - 18,
            text=f"({event.x_root}, {event.y_root})",
            fill="#00e5ff",
            font=("Segoe UI", 11),
            tags="marker",
            anchor="w",
        )
        self.after(450, lambda: self._set_step(self._step_index + 1))


# ── Calibration Tool ─────────────────────────────────────────────────────────

class SOPCalibrationTool:
    """
    Calibrate toạ độ form SOP Logging cho từng màn hình.
    Kết quả lưu vào sop/sop_config.json -> displays[display_id].
    """

    def __init__(self, cfg: SOPConfig, display_id: int | None = None) -> None:
        self._cfg = cfg
        self._display_id = display_id

    def run(self) -> None:
        monitors = get_windows_monitors()
        if self._display_id is None:
            print("\n" + "=" * 60)
            print("  CHỌN MÀN HÌNH CẦN CALIBRATE FORM")
            print("=" * 60)
            for m in monitors:
                role = "Main" if m["is_primary"] else "Phụ"
                print(f"  [{m['id']}] Màn hình {m['id']} ({role:4}) - {m['width']}x{m['height']} @ ({m['x']}, {m['y']})")
            print("=" * 60)
            choice = input("  >>> Nhập số màn hình muốn calibrate (vd: 3 hoặc 4, mặc định 3): ").strip()
            try:
                self._display_id = int(choice) if choice else 3
            except ValueError:
                self._display_id = 3

        disp_id = self._display_id
        mx, my, mw, mh = get_monitor_bounds(disp_id)

        print("\n" + "=" * 60)
        print(f"  SOP Form Calibration — MÀN HÌNH {disp_id}")
        print(f"  Toạ độ vùng màn hình: x={mx}, y={my}, size={mw}x{mh}")
        print("=" * 60)
        print(f"  1. Mở form 'Logging SOP (SUSPECT)' trên MÀN HÌNH {disp_id}.")
        print("  2. Nhấn Enter để bắt đầu overlay.")
        print("  3. Click vào TÂM của từng ô theo hướng dẫn.")
        print("  4. Nhấn ESC để huỷ.")
        print("=" * 60)
        input(f"\n  >>> Nhấn Enter khi form SOP trên Màn {disp_id} đã sẵn sàng...\n")

        try:
            overlay = SOPCalibrationOverlay(display_id=disp_id)
            overlay.mainloop()
        except Exception as exc:
            print(f"[SOP Calibrate] GUI lỗi: {exc}. Thử CLI mode...")
            self._run_cli(disp_id)
            return

        if not overlay.results:
            print("[SOP Calibrate] Bị huỷ, không lưu.")
            return

        # Lưu vào sop_config.json cho màn hình tương ứng
        coords = self._cfg.get_form_coords(disp_id).copy()
        coords.update(overlay.results)
        self._cfg.set_form_coords(coords, display_id=disp_id)

        print(f"\n[SOP Calibrate] XONG! Toạ độ Màn hình {disp_id} đã lưu:")
        for k, v in overlay.results.items():
            print(f"  {k:22}: x={v['x']:5}, y={v['y']:5}")
        print(f"\n  File: {self._cfg._path}\n")

    def _run_cli(self, disp_id: int) -> None:
        """Fallback CLI nhập tay toạ độ."""
        print(f"\n=== SOP Calibration — CLI mode (Màn hình {disp_id}) ===")
        keys = [
            ("vision_functionality", "Vision Functionality dropdown"),
            ("actions_required",     "Actions Required dropdown"),
            ("maintenance_issues",   "Maintenance Issues dropdown"),
            ("resolution",           "Resolution dropdown"),
            ("comment",              "Comment text box"),
            ("send_button",          "SEND button"),
        ]
        coords = self._cfg.get_form_coords(disp_id).copy()
        for key, label in keys:
            print(f"\n--- {label} ---")
            x = int(input("  x: "))
            y = int(input("  y: "))
            coords[key] = {"x": x, "y": y}
        self._cfg.set_form_coords(coords, display_id=disp_id)
        print(f"\n[SOP Calibrate] Đã lưu toạ độ Màn {disp_id}.")


# ── Option Position Calibrator ───────────────────────────────────────────────

class SOPOptionCalibrator:
    """
    Calibrate vị trí pixel của từng option trong dropdown cho từng màn hình.
    Dùng phương pháp hover + Enter:
      1. Mở dropdown trong form trên màn hình tương ứng
      2. Di chuột đến option (KHÔNG click, để dropdown vẫn mở)
      3. Nhấn ENTER trong terminal để ghi vị trí
    """

    DROPDOWN_INFO = [
        ("vision_functionality", "Vision Functionality",
         "All cameras functional",   "Some cameras functional"),
        ("actions_required",     "Actions Required",
         "Home actuators",           "Align"),
        ("maintenance_issues",   "Maintenance Issues",
         "Axes not responding",      "Sensor malfunction"),
        ("resolution",           "Resolution",
         "Successful",               "Bot STOed"),
    ]

    def __init__(self, cfg: SOPConfig, display_id: int | None = None) -> None:
        self._cfg = cfg
        self._display_id = display_id

    def run(self) -> None:
        monitors = get_windows_monitors()
        if self._display_id is None:
            print("\n" + "=" * 60)
            print("  CHỌN MÀN HÌNH CẦN CALIBRATE DROPDOWN OPTIONS")
            print("=" * 60)
            for m in monitors:
                role = "Main" if m["is_primary"] else "Phụ"
                print(f"  [{m['id']}] Màn hình {m['id']} ({role:4}) - {m['width']}x{m['height']} @ ({m['x']}, {m['y']})")
            print("=" * 60)
            choice = input("  >>> Nhập số màn hình (vd: 3 hoặc 4, mặc định 3): ").strip()
            try:
                self._display_id = int(choice) if choice else 3
            except ValueError:
                self._display_id = 3

        disp_id = self._display_id

        print("\n" + "=" * 60)
        print(f"  Calibrate Dropdown Options — MÀN HÌNH {disp_id}")
        print("=" * 60)
        print(f"  Quy trình cho mỗi dropdown trên Màn {disp_id}:")
        print("  1. Click vào dropdown trong form để MỞ BẢNG OPTION")
        print("  2. Di chuột đến option (KHÔNG click, bảng vẫn mở)")
        print("  3. Nhấn ENTER trong terminal để ghi vị trí")
        print("  4. Di chuột đến option kế tiếp, nhấn ENTER lần nữa")
        print("=" * 60 + "\n")

        geometry = self._cfg.get_dropdown_geometry(disp_id).copy()

        for field, label, opt0_name, opt1_name in self.DROPDOWN_INFO:
            print(f"{'─' * 55}")
            print(f"  [{label}] (Màn {disp_id})")
            print(f"{'─' * 55}")

            # Option 1
            print(f"\n  BƯỚC 1: Mở dropdown [{label}] trên Màn {disp_id}.")
            print(f"          Di chuột đến: '{opt0_name}' (KHÔNG click)")
            input(f"  >>> Nhấn ENTER khi chuột đang nằm trên '{opt0_name}'...")
            x1, y1 = pyautogui.position()
            print(f"      Ghi nhận: ({x1}, {y1})")

            # Option 2
            if label in ("Vision Functionality", "Resolution"):
                print(f"\n  BƯỚC 2: Mở lại dropdown [{label}] (nếu đã bị đóng).")
            else:
                print(f"\n  BƯỚC 2: Dropdown vẫn mở. Di chuột xuống dòng kế tiếp.")
            print(f"          Di chuột đến: '{opt1_name}' (KHÔNG click)")
            input(f"  >>> Nhấn ENTER khi chuột đang nằm trên '{opt1_name}'...")
            x2, y2 = pyautogui.position()
            print(f"      Ghi nhận: ({x2}, {y2})")

            row_height = abs(y2 - y1)
            if row_height < 8:
                print(f"  WARN: row_height={row_height}px quá nhỏ!")
                retry = input("  Thử lại bước này? (y/n): ").strip().lower()
                if retry == "y":
                    continue

            avg_x = (x1 + x2) // 2
            geometry[field] = {
                "first_option_x": avg_x,
                "first_option_y": y1,
                "row_height":     max(row_height, 10),
            }
            print(f"  OK: x={avg_x}, first_y={y1}, row_h={row_height}px")

            pyautogui.press("escape")
            time.sleep(0.3)

        self._cfg.set_dropdown_geometry(geometry, display_id=disp_id)

        print("\n" + "=" * 60)
        print(f"  Calibration XONG! Đã lưu toạ độ options cho Màn hình {disp_id}")
        print("=" * 60)
        for field, label, opt0, opt1 in self.DROPDOWN_INFO:
            g = geometry.get(field, {})
            print(f"  {label:22}: x={g.get('first_option_x', '?')}, first_y={g.get('first_option_y', '?')}, row_h={g.get('row_height', '?')}px")
        print()
