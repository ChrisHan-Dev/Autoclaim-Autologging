"""
sop_calibrate.py — Interactive Calibration Tool for SOP Logging
===============================================================
Two-step calibration process for each display:
1. python sop_main.py calibrate [--display 3|4]        — Record center coordinates for dropdown fields
2. python sop_main.py calibrate_options [--display 3|4] — Record geometry for options in dropdown lists
"""

import time
import tkinter as tk
import pyautogui

from auto_logging.sop_config import SOPConfig
from auto_logging.sop_display import (
    get_windows_monitors,
    get_monitor_bounds,
)


# ── Full-Screen Overlay Calibration ──────────────────────────────────────────

class SOPCalibrationOverlay(tk.Toplevel):
    """
    Full-screen semi-transparent overlay positioned precisely on the target display.
    User clicks on each element in sequence to record coordinates.
    """

    STEPS: list[tuple[str, str]] = [
        ("vision_functionality", "Step 1/6 — CLICK center of [Vision Functionality]"),
        ("actions_required",     "Step 2/6 — CLICK center of [Actions Required]"),
        ("maintenance_issues",   "Step 3/6 — CLICK center of [Maintenance Issues]"),
        ("resolution",           "Step 4/6 — CLICK center of [Resolution]"),
        ("comment",              "Step 5/6 — CLICK center of [Comment]"),
        ("send_button",          "Step 6/6 — CLICK the [SEND] button"),
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

        # Retrieve real coordinates of target display
        mx, my, mw, mh = get_monitor_bounds(display_id)

        # Position overlay covering the entire target display
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
        self._label.config(text=f"[DISPLAY {self.display_id}] {instruction}")
        self._counter.config(text=f"{index + 1} / {len(self.STEPS)} — Press ESC to cancel")
        self._canvas.delete("marker")

    def _on_click(self, event: tk.Event) -> None:
        key, _ = self.STEPS[self._step_index]
        self.results[key] = {"x": event.x_root, "y": event.y_root}

        # Draw marker
        r = 14
        cx, cy = event.x, event.y
        self._canvas.create_line(cx - r, cy, cx + r, cy, fill="#00e5ff", width=2, tags="marker")
        self._canvas.create_line(cx, cy - r, cx, cy + r, fill="#00e5ff", width=2, tags="marker")
        self._canvas.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, outline="#00e5ff", width=2, tags="marker")

        # Coordinate label
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
    Calibrate SOP Logging form coordinates for each display.
    Results are saved into sop_config.json -> displays[display_id].
    """

    def __init__(self, cfg: SOPConfig, display_id: int | None = None) -> None:
        self._cfg = cfg
        self._display_id = display_id

    def run(self) -> None:
        monitors = get_windows_monitors()
        if self._display_id is None:
            print("\n" + "=" * 60)
            print("  SELECT DISPLAY TO CALIBRATE FORM")
            print("=" * 60)
            for m in monitors:
                role = "Main" if m["is_primary"] else "Secondary"
                print(f"  [{m['id']}] Display {m['id']} ({role:9}) - {m['width']}x{m['height']} @ ({m['x']}, {m['y']})")
            print("=" * 60)
            choice = input("  >>> Enter display number to calibrate (e.g. 3 or 4, default 3): ").strip()
            try:
                self._display_id = int(choice) if choice else 3
            except ValueError:
                self._display_id = 3

        disp_id = self._display_id
        mx, my, mw, mh = get_monitor_bounds(disp_id)

        print("\n" + "=" * 60)
        print(f"  SOP Form Calibration — DISPLAY {disp_id}")
        print(f"  Display bounds: x={mx}, y={my}, size={mw}x{mh}")
        print("=" * 60)
        print(f"  1. Open 'Logging SOP (SUSPECT)' form on DISPLAY {disp_id}.")
        print("  2. Press Enter to start overlay.")
        print("  3. CLICK the CENTER of each field following instructions.")
        print("  4. Press ESC to cancel.")
        print("=" * 60)
        input(f"\n  >>> Press Enter when SOP form on Display {disp_id} is ready...\n")

        try:
            overlay = SOPCalibrationOverlay(display_id=disp_id)
            overlay.mainloop()
        except Exception as exc:
            print(f"[SOP Calibrate] GUI error: {exc}. Trying CLI mode...")
            self._run_cli(disp_id)
            return

        if not overlay.results:
            print("[SOP Calibrate] Cancelled, not saved.")
            return

        # Save into sop_config.json for target display
        coords = self._cfg.get_form_coords(disp_id).copy()
        coords.update(overlay.results)
        self._cfg.set_form_coords(coords, display_id=disp_id)

        print(f"\n[SOP Calibrate] DONE! Coordinates for Display {disp_id} saved:")
        for k, v in overlay.results.items():
            print(f"  {k:22}: x={v['x']:5}, y={v['y']:5}")
        print(f"\n  File: {self._cfg._path}\n")

        # Offer to save into profile
        _prompt_save_profile_sop(self._cfg)

    def _run_cli(self, disp_id: int) -> None:
        """Fallback CLI manual coordinate entry."""
        print(f"\n=== SOP Calibration — CLI mode (Display {disp_id}) ===")
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
        print(f"\n[SOP Calibrate] Saved coordinates for Display {disp_id}.")
        _prompt_save_profile_sop(self._cfg)


# ── Option Position Calibrator ───────────────────────────────────────────────

class SOPOptionCalibrator:
    """
    Calibrate pixel geometry of options within dropdowns for each display.
    Uses hover + Enter method:
      1. Open dropdown in form on target display
      2. Hover mouse over option (DO NOT click, leave list open)
      3. Press ENTER in terminal to record position
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
            print("  SELECT DISPLAY TO CALIBRATE DROPDOWN OPTIONS")
            print("=" * 60)
            for m in monitors:
                role = "Main" if m["is_primary"] else "Secondary"
                print(f"  [{m['id']}] Display {m['id']} ({role:9}) - {m['width']}x{m['height']} @ ({m['x']}, {m['y']})")
            print("=" * 60)
            choice = input("  >>> Enter display number (e.g. 3 or 4, default 3): ").strip()
            try:
                self._display_id = int(choice) if choice else 3
            except ValueError:
                self._display_id = 3

        disp_id = self._display_id

        print("\n" + "=" * 60)
        print(f"  Calibrate Dropdown Options — DISPLAY {disp_id}")
        print("=" * 60)
        print(f"  Procedure for each dropdown on Display {disp_id}:")
        print("  1. Click dropdown in form to OPEN OPTION LIST")
        print("  2. Hover mouse over option (DO NOT click, leave list open)")
        print("  3. Press ENTER in terminal to record position")
        print("  4. Hover mouse over next option, press ENTER again")
        print("=" * 60 + "\n")

        geometry = self._cfg.get_dropdown_geometry(disp_id).copy()

        for field, label, opt0_name, opt1_name in self.DROPDOWN_INFO:
            print(f"{'─' * 55}")
            print(f"  [{label}] (Display {disp_id})")
            print(f"{'─' * 55}")

            # Option 1
            print(f"\n  STEP 1: Open dropdown [{label}] on Display {disp_id}.")
            print(f"          Hover mouse over: '{opt0_name}' (DO NOT click)")
            input(f"  >>> Press ENTER when cursor is over '{opt0_name}'...")
            x1, y1 = pyautogui.position()
            print(f"      Recorded: ({x1}, {y1})")

            # Option 2
            if label in ("Vision Functionality", "Resolution"):
                print(f"\n  STEP 2: Re-open dropdown [{label}] (if closed).")
            else:
                print(f"\n  STEP 2: Dropdown is open. Move cursor down to next row.")
            print(f"          Hover mouse over: '{opt1_name}' (DO NOT click)")
            input(f"  >>> Press ENTER when cursor is over '{opt1_name}'...")
            x2, y2 = pyautogui.position()
            print(f"      Recorded: ({x2}, {y2})")

            row_height = abs(y2 - y1)
            if row_height < 8:
                print(f"  WARN: row_height={row_height}px is too small!")
                retry = input("  Retry this step? (y/n): ").strip().lower()
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
        print(f"  Calibration DONE! Saved options geometry for Display {disp_id}")
        print("=" * 60)
        for field, label, opt0, opt1 in self.DROPDOWN_INFO:
            g = geometry.get(field, {})
            print(f"  {label:22}: x={g.get('first_option_x', '?')}, first_y={g.get('first_option_y', '?')}, row_h={g.get('row_height', '?')}px")
        print()

        # Offer to save into profile
        _prompt_save_profile_sop(self._cfg)


# ── Profile save helper (shared by both calibrators) ────────────────────────────

def _prompt_save_profile_sop(cfg: SOPConfig) -> None:
    """After calibration, ask user to save current setup into a named profile."""
    profiles = cfg.list_profiles()
    active = cfg.get_active_profile()
    print("\n" + "=" * 60)
    print("  🆔 Save setup to Profile?")
    print(f"  Current profile: [{active.upper()}]")
    print(f"  Available profiles: {', '.join(profiles)}")
    print("  Enter profile name to save (e.g. home / office) or press Enter to skip:")
    print("=" * 60)
    choice = input("  >>> ").strip().lower()
    if choice and choice in profiles:
        cfg.save_profile(choice)
        cfg.switch_profile(choice)
        print(f"  ✓ Saved to profile '{choice.upper()}'!")
    elif choice:
        cfg.save_profile(choice)
        cfg.switch_profile(choice)
        print(f"  ✓ Created and saved to new profile '{choice.upper()}'!")
    else:
        print("  (Skipped saving profile)")
