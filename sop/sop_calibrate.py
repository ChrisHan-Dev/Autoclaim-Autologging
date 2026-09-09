"""
sop_calibrate.py — SOP Form Calibration Tools (doc lap)
=======================================================
Gom 2 buoc calibration:
  1. python sop_main.py calibrate        — Ghi toa do tam cac O dropdown (nut bam)
  2. python sop_main.py calibrate_options — Ghi toa do tung OPTION trong dropdown list
"""

from __future__ import annotations

import time
import tkinter as tk

import pyautogui

from .sop_config import SOPConfig


# ── Overlay ──────────────────────────────────────────────────────────────────

class SOPCalibrationOverlay(tk.Toplevel):
    """
    Full-screen semi-transparent overlay.
    User click lan luot vao tung element de ghi lai toa do.
    """

    STEPS: list[tuple[str, str]] = [
        ("vision_functionality", "Step 1/6 — CLICK vao tam o [Vision Functionality]"),
        ("actions_required",     "Step 2/6 — CLICK vao tam o [Actions Required]"),
        ("maintenance_issues",   "Step 3/6 — CLICK vao tam o [Maintenance Issues]"),
        ("resolution",           "Step 4/6 — CLICK vao tam o [Resolution]"),
        ("comment",              "Step 5/6 — CLICK vao tam o [Comment]"),
        ("send_button",          "Step 6/6 — CLICK vao nut [SEND]"),
    ]

    def __init__(self, master=None) -> None:
        if master is None:
            self._temp_root = tk.Tk()
            self._temp_root.withdraw()
            master = self._temp_root
        else:
            self._temp_root = None

        super().__init__(master)
        self.results: dict = {}
        self._step_index: int = 0

        # Full screen, semi-transparent, dark blue
        self.attributes("-fullscreen", True)
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
        self._label.place(relx=0.5, rely=0.05, anchor="center")

        # Step counter
        self._counter = tk.Label(
            self,
            text="",
            font=("Segoe UI", 13),
            fg="#607d8b",
            bg="#001428",
        )
        self._counter.place(relx=0.5, rely=0.10, anchor="center")

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
        self._label.config(text=instruction)
        self._counter.config(text=f"{index + 1} / {len(self.STEPS)} — Nhan ESC de huy")
        self._canvas.delete("marker")

    def _on_click(self, event: tk.Event) -> None:
        key, _ = self.STEPS[self._step_index]
        self.results[key] = {"x": event.x_root, "y": event.y_root}

        # Ve marker
        r = 14
        cx, cy = event.x, event.y
        self._canvas.create_line(cx - r, cy, cx + r, cy, fill="#00e5ff", width=2, tags="marker")
        self._canvas.create_line(cx, cy - r, cx, cy + r, fill="#00e5ff", width=2, tags="marker")
        self._canvas.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, outline="#00e5ff", width=2, tags="marker")

        # Label toa do
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
    Calibrate toa do form SOP Logging.
    Ket qua luu vao sop/sop_config.json, hoan toan doc lap.
    """

    def __init__(self, cfg: SOPConfig) -> None:
        self._cfg = cfg

    def run(self) -> None:
        print("\n" + "=" * 58)
        print("  SOP Form Calibration")
        print("=" * 58)
        print("  1. Mo form 'Logging SOP (SUSPECT)' tren man hinh.")
        print("  2. Nhan Enter de bat dau.")
        print("  3. Click vao TUM cua tung o theo huong dan.")
        print("  4. Nhan ESC de huy.")
        print("=" * 58)
        input("\n  >>> Nhan Enter khi form SOP da san sang...\n")

        try:
            overlay = SOPCalibrationOverlay()
            overlay.mainloop()
        except Exception as exc:
            print(f"[SOP Calibrate] GUI loi: {exc}. Thu CLI mode...")
            self._run_cli()
            return

        if not overlay.results:
            print("[SOP Calibrate] Bi huy, khong luu.")
            return

        # Luu vao sop_config.json
        coords = self._cfg.form_coords.copy()
        coords.update(overlay.results)
        self._cfg.set("form_coords", coords)
        self._cfg.save()

        print("\n[SOP Calibrate] XONG! Toa do da luu:")
        for k, v in overlay.results.items():
            print(f"  {k:22}: x={v['x']:4}, y={v['y']:4}")
        print(f"\n  File: {self._cfg._path}\n")

    def _run_cli(self) -> None:
        """Fallback CLI nhap tay toa do."""
        print("\n=== SOP Calibration — CLI mode ===")
        keys = [
            ("vision_functionality", "Vision Functionality dropdown"),
            ("actions_required",     "Actions Required dropdown"),
            ("maintenance_issues",   "Maintenance Issues dropdown"),
            ("resolution",           "Resolution dropdown"),
            ("comment",              "Comment text box"),
            ("send_button",          "SEND button"),
        ]
        coords = self._cfg.form_coords.copy()
        for key, label in keys:
            print(f"\n--- {label} ---")
            x = int(input("  x: "))
            y = int(input("  y: "))
            coords[key] = {"x": x, "y": y}
        self._cfg.set("form_coords", coords)
        self._cfg.save()
        print("\n[SOP Calibrate] Da luu.")


# ── Option Position Calibrator ───────────────────────────────────────────────

class SOPOptionCalibrator:
    """
    Calibrate vi tri pixel cua tung option trong dropdown.
    Dung phuong phap hover + Enter:
      1. Mo dropdown trong form
      2. Di chuot den option (KHONG click, de dropdown van mo)
      3. Nhan ENTER trong terminal nay
      Lap lai cho option thu 2 de tinh row_height.

    Ket qua luu vao sop_config.json -> "dropdown_geometry".
    """

    # (field_key, ten hien thi, option_0, option_1)
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

    def __init__(self, cfg: SOPConfig) -> None:
        self._cfg = cfg

    def run(self) -> None:
        print("\n" + "=" * 60)
        print("  Calibrate Dropdown Option Positions")
        print("=" * 60)
        print("  Quy trinh cho moi dropdown:")
        print("  1. Click vao dropdown trong form de MO BANG OPTION")
        print("  2. Di chuot den option (KHONG click, bang van mo)")
        print("  3. Nhan ENTER trong terminal nay de ghi vi tri")
        print("  4. Di chuot den option ke tiep, nhan ENTER lan nua")
        print()
        print("  Meo: giu focus tai terminal nay khi nhan Enter")
        print("       Ban co the di chuot sang form ma khong mat focus")
        print("=" * 60 + "\n")

        geometry = self._cfg.get("dropdown_geometry", {})

        for field, label, opt0_name, opt1_name in self.DROPDOWN_INFO:
            print(f"{'─' * 55}")
            print(f"  [{label}]")
            print(f"{'─' * 55}")

            # ── Option dau tien ──
            print(f"\n  BUOC 1: Click dropdown [{label}] de mo bang.")
            print(f"          Di chuot den: '{opt0_name}'")
            print(f"          (KHONG click option, chi di chuot toi do)")
            input(f"  >>> Nhan ENTER khi chuot dang nam tren '{opt0_name}'...")
            x1, y1 = pyautogui.position()
            print(f"      Ghi: ({x1}, {y1})")

            # ── Option thu hai ──
            # Voi single-select (Vision, Resolution): dropdown da dong neu user
            # vo tinh click. Huong dan mo lai neu can.
            if label in ("Vision Functionality", "Resolution"):
                print(f"\n  BUOC 2: Mo lai dropdown [{label}] (neu no da dong).")
            else:
                print(f"\n  BUOC 2: Dropdown van mo. Di chuot xuong dong ke tiep.")
            print(f"          Di chuot den: '{opt1_name}'")
            print(f"          (KHONG click, chi di chuot toi do)")
            input(f"  >>> Nhan ENTER khi chuot dang nam tren '{opt1_name}'...")
            x2, y2 = pyautogui.position()
            print(f"      Ghi: ({x2}, {y2})")

            row_height = abs(y2 - y1)
            if row_height < 8:
                print(f"  WARN: row_height={row_height}px qua nho!")
                print(f"  Thu lai: can di chuot chinh xac den 2 option khac nhau.")
                retry = input("  Thu lai buoc nay? (y/n): ").strip().lower()
                if retry == "y":
                    # Recursive retry for this dropdown
                    print(f"\n  [Thu lai {label}]")
                    continue

            # x: trung binh cua 2 lan click (option list thuong thang hang)
            avg_x = (x1 + x2) // 2
            geometry[field] = {
                "first_option_x": avg_x,
                "first_option_y": y1,
                "row_height":     max(row_height, 10),
            }
            print(f"  OK: x={avg_x}, first_y={y1}, row_h={row_height}px")

            # Dong dropdown neu van con mo
            pyautogui.press("escape")
            time.sleep(0.3)

        # Luu
        self._cfg.set("dropdown_geometry", geometry)
        self._cfg.save()

        print("\n" + "=" * 60)
        print("  Calibration XONG! Da luu vao sop_config.json")
        print("=" * 60)
        print("\n  Tom tat:")
        for field, label, opt0, opt1 in self.DROPDOWN_INFO:
            g = geometry.get(field, {})
            rh = g.get("row_height", "?")
            fy = g.get("first_option_y", "?")
            fx = g.get("first_option_x", "?")
            print(f"  {label:22}: x={fx}, first_y={fy}, row_h={rh}px")
        print()

