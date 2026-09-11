"""
sop_hud.py — Floating Status HUD for SOP Logging (Multi-Display & Multi-Type Support)
====================================================================================
Compact, draggable, always-on-top dashboard on screen.
Features:
  - Live status display (Ready, Filling Form, Done, Error)
  - Fast display switching (Click button or press F6)
  - SOP Type selection via Dropdown:
      * SUSPECT (6 Cases: Case 1..6)
      * CHRF (6 Cases: Charger Recovery)
  - [▲ Collapse / ▼ Expand] button to minimize case buttons.
  - Click case buttons directly on HUD or press hotkeys.
  - Quick Clipboard: Single-click to copy incident keywords (bh_...)
  - Multi-profile support: Switch between Home and Office setups on the fly.
"""

from __future__ import annotations

import threading
import time
import tkinter as tk
from typing import Callable, Optional

# Color palette (Dark Modern)
_C = {
    "bg":             "#0f0f1a",
    "bg2":            "#1a1a2e",
    "header":         "#16213e",
    "border":         "#2a2a4a",
    "fg":             "#e0e0e0",
    "fg_dim":         "#8a8aab",
    "green":          "#00d084",
    "red":            "#ff4757",
    "yellow":         "#ffa502",
    "blue":           "#1e90ff",
    "cyan":           "#00e5ff",
    "btn_bg":         "#1f2438",
    "btn_hover":      "#2d3553",
    "btn_active":     "#1652f0",
    "disp_active_bg": "#0f3460",
    "disp_active_fg": "#00e5ff",
    "kw_bg":          "#151928",
    "kw_hover":       "#242d4a",
    "kw_active":      "#0f4a36",
    "kw_fg":          "#00e5ff",
}

# ── Incident Keywords list (Click to Copy to Clipboard) ────────────────
KEYWORD_DEFS: list[tuple[str, str, str, str]] = [
    ("bh_damage_case_on_payload", "📦", "bh_damage_case",   "Damaged Case on Payload (not shelf)"),
    ("bh_rogue_case_on_payload",  "📦", "bh_rogue_case",    "Rogue Case on Payload"),
    ("bh_debris_on_payload",      "🧹", "bh_debris",        "Debris on Payload"),
    ("bh_tape_on_actuator",       "🩹", "bh_tape_actuator", "Tape on Actuator / COH block"),
    ("bh_coh_fail",               "📡", "bh_coh_fail",      "COH Sensor False Block"),
    ("bh_actuator_stuck",         "⚙️", "bh_actuator_stuck", "Actuator Stuck / Err limit"),
    ("bh_lift_tilts",             "📐", "bh_lift_tilts",    "Lift Tilts / Half moves (Error 1)"),
    ("bh_bot_damaged",            "⚠️", "bh_bot_damaged",   "Actuators Bent / Broken / Missing"),
]

# ── Case list for SUSPECT (6 Cases) ───────────────────────────────────────
SUSPECT_DEFS: list[tuple[str, str, str, str]] = [
    ("f1", "Case 1", "Insert", "All cam / Align+Extract / Success"),
    ("f2", "Case 2", "Home",   "No cam / No action / Unsuccessful"),
    ("f3", "Case 3", "PgUp",   "All cam / Not pickable"),
    ("f4", "Case 4", "PgDn",   "All cam / Align+Ext / CHD"),
    ("f5", "Case 5", "End",    "All cam / No action / No case / Success"),
    ("f6", "Case 6", "Del",    "All cam / No action / Rogue / CHD"),
]

# ── Case list for CHRF (6 Cases) ──────────────────────────────────────────
CHRF_DEFS: list[tuple[str, str, str, str]] = [
    ("c1", "Case 1", "Insert", "Align + Place / Success"),
    ("c2", "Case 2", "Home",   "Home actuator / Success"),
    ("c3", "Case 3", "PgUp",   "Home + Align + Place / Success"),
    ("c4", "Case 4", "PgDn",   "Home / Axes not resp / CHD no payl"),
    ("c5", "Case 5", "End",    "Home / Sensor malf / CHD no payl"),
    ("c6", "Case 6", "Del",    "Align + Ext / Damaged / CHD payl"),
]


class SOPStatusHUD:
    """
    Floating always-on-top HUD window for SOP Logging.
    Supports switching between multiple displays on a single popup.
    Supports Dropdown switching between SUSPECT and CHRF cases.
    Integrated Quick Clipboard (Click to Copy incident keywords).
    Supports Profiles (Home / Office) for instant display layout switching.
    """

    WINDOW_WIDTH = 340
    HEIGHT_SUSPECT = 515
    HEIGHT_CHRF = 515
    HEIGHT_COLLAPSED = 330

    def __init__(
        self,
        cfg,
        on_trigger_case: Callable[[str], None],
        on_exit: Callable[[], None],
        on_switch_display: Optional[Callable[[int], None]] = None,
        on_switch_sop_type: Optional[Callable[[str], None]] = None,
        on_switch_profile: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.cfg = cfg
        self.on_trigger_case = on_trigger_case
        self.on_exit = on_exit
        self.on_switch_display = on_switch_display
        self.on_switch_sop_type = on_switch_sop_type
        self.on_switch_profile = on_switch_profile

        self._root: Optional[tk.Tk] = None
        self._running = False
        self._lock = threading.Lock()

        # Display pair: [2, 3] or configured pair
        self._disp_pair = self.cfg.get_active_pair()
        if len(self._disp_pair) < 2:
            self._disp_pair = [2, 3]

        # Active SOP Type ("SUSPECT" or "CHRF")
        self._active_sop_type = self.cfg.get_active_sop_type()
        self._is_collapsed = False

        # State fields
        self._active_display = self.cfg.get_active_display()
        self._status_text = "READY"
        self._status_color = _C["green"]
        self._detail_text = f"Disp {self._active_display} [{self._active_sop_type}] — Ready"

        # Position
        self._x = self.cfg.get("hud_x", 120)
        self._y = self.cfg.get("hud_y", 120)

        # Drag tracking
        self._drag_x = 0
        self._drag_y = 0

        # UI elements
        self._dot_label: Optional[tk.Label] = None
        self._status_label: Optional[tk.Label] = None
        self._detail_label: Optional[tk.Label] = None
        self._type_btn: Optional[tk.Label] = None
        self._collapse_btn: Optional[tk.Label] = None
        self._suspect_frame: Optional[tk.Frame] = None
        self._chrf_frame: Optional[tk.Frame] = None
        self._footer_label: Optional[tk.Label] = None
        self._buttons: dict[str, tk.Frame] = {}
        # Profile bar buttons  {profile_name: tk.Label}
        self._profile_btns: dict[str, tk.Label] = {}
        # All-monitor display buttons  {monitor_id: tk.Label}
        self._all_disp_btns: dict[int, tk.Label] = {}

    # ── Multi-Display Switch ──────────────────────────────────────────────────

    def switch_display(self, display_id: int) -> None:
        """Switch active display safely across threads."""
        with self._lock:
            self._active_display = display_id
            self.cfg.set_active_display(display_id)
            calibrated = self.cfg.is_calibrated(display_id)
            status_suffix = "" if calibrated else " (Not Calibrated!)"
            self._detail_text = f"Disp {display_id} [{self._active_sop_type}]{status_suffix} — Ready"

        if self._root:
            try:
                self._root.after(0, self._update_display_selector_ui)
            except Exception:
                pass

        if self.on_switch_display:
            try:
                self.on_switch_display(display_id)
            except Exception:
                pass

    def toggle_display(self) -> None:
        """
        Cycle through all monitors currently in the active pair (F6).
        Works for pairs of any size: 2, 3, or 4 monitors.
        """
        pair = self._disp_pair
        if not pair:
            return
        if self._active_display in pair:
            idx = pair.index(self._active_display)
            next_disp = pair[(idx + 1) % len(pair)]
        else:
            next_disp = pair[0]
        self.switch_display(next_disp)

    def toggle_sop_type(self) -> None:
        """Toggle between SUSPECT <-> CHRF (F7)."""
        nxt = "CHRF" if self._active_sop_type == "SUSPECT" else "SUSPECT"
        self.switch_sop_type(nxt)

    # ── SOP Type Switch (SUSPECT <-> CHRF) ─────────────────────────────────────

    def switch_sop_type(self, new_type: str) -> None:
        """Switch SOP Type (SUSPECT or CHRF), save to config and refresh UI."""
        new_type = new_type.upper()
        with self._lock:
            self._active_sop_type = new_type
            self.cfg.set_active_sop_type(new_type)
            self._is_collapsed = False
            self._detail_text = f"Disp {self._active_display} [{new_type}] — Ready"

        if not self._root:
            return

        try:
            cur_x = self._root.winfo_x()
            cur_y = self._root.winfo_y()

            if self._collapse_btn:
                self._collapse_btn.config(text="▲ Collapse", fg=_C["fg_dim"])

            if new_type == "SUSPECT":
                if self._type_btn:
                    self._type_btn.config(text="▼ SUSPECT (6 Cases)", fg=_C["cyan"])
                if self._chrf_frame:
                    self._chrf_frame.pack_forget()
                if self._suspect_frame:
                    self._suspect_frame.pack(fill="x")
                if self._footer_label:
                    pair_str = "/".join(str(d) for d in self._disp_pair)
                    self._footer_label.config(text=f"F6: Disp {pair_str} | F7: Type | Ins..Del: Form | ESC")
                self._root.geometry(f"{self.WINDOW_WIDTH}x{self.HEIGHT_SUSPECT}+{cur_x}+{cur_y}")
            else:
                if self._type_btn:
                    self._type_btn.config(text="▼ CHRF (6 Cases)", fg=_C["yellow"])
                if self._suspect_frame:
                    self._suspect_frame.pack_forget()
                if self._chrf_frame:
                    self._chrf_frame.pack(fill="x")
                if self._footer_label:
                    pair_str = "/".join(str(d) for d in self._disp_pair)
                    self._footer_label.config(text=f"F6: Disp {pair_str} | Ins..Del: Form | ESC")
                self._root.geometry(f"{self.WINDOW_WIDTH}x{self.HEIGHT_CHRF}+{cur_x}+{cur_y}")
        except Exception as e:
            print(f"[SOP HUD] Error switching SOP type: {e}")

        if self.on_switch_sop_type:
            try:
                self.on_switch_sop_type(new_type)
            except Exception:
                pass

    # ── Profile Switch (Home / Office) ────────────────────────────────────

    def switch_profile(self, name: str) -> None:
        """
        Switch to a named profile (e.g. 'home' or 'office').
        Reloads all calibration data from cfg in-process; no restart needed.
        """
        try:
            self.cfg.switch_profile(name)
        except KeyError as exc:
            print(f"[SOP HUD] Profile error: {exc}")
            return

        # Refresh live state from the newly loaded profile
        with self._lock:
            self._disp_pair = self.cfg.get_active_pair()
            if len(self._disp_pair) < 1:
                self._disp_pair = [4]
            self._active_display = self.cfg.get_active_display()
            if self._active_display not in self._disp_pair:
                self._active_display = self._disp_pair[0]
            self._active_sop_type = self.cfg.get_active_sop_type()
            self._is_collapsed = False
            pair_str = "/".join(str(d) for d in self._disp_pair)
            self._detail_text = f"Profile: {name.upper()} | Disp {self._active_display} [{self._active_sop_type}] — Ready"

        if self._root:
            try:
                self._root.after(0, self._update_profile_selector_ui)
                self._root.after(0, self._update_display_selector_ui)
                self._root.after(0, self._update_footer_hint)
            except Exception:
                pass

        if self.on_switch_profile:
            try:
                self.on_switch_profile(name)
            except Exception:
                pass

    # ── Monitor pair toggle ─────────────────────────────────────────────────────

    def toggle_monitor_in_pair(self, monitor_id: int) -> None:
        """
        Add or remove monitor_id from the active pair.
        - Cannot remove if only 1 monitor left.
        - If adding, the monitor becomes the active display.
        """
        pair = list(self._disp_pair)
        if monitor_id in pair:
            if len(pair) <= 1:
                print(f"[SOP HUD] Cannot remove Display {monitor_id}: must keep at least 1 monitor active.")
                return
            pair.remove(monitor_id)
            # If we just removed the active display, switch to first remaining
            if self._active_display == monitor_id:
                new_active = pair[0]
                self.switch_display(new_active)
        else:
            pair.append(monitor_id)
            pair.sort()

        self._disp_pair = pair
        self.cfg.set_active_pair(*pair)

        if self._root:
            try:
                self._root.after(0, self._update_display_selector_ui)
                self._root.after(0, self._update_footer_hint)
            except Exception:
                pass

    def _popup_monitor_menu(self, event: tk.Event, monitor_id: int) -> None:
        """Right-click context menu on a monitor button."""
        if not self._root:
            return
        in_pair = monitor_id in self._disp_pair
        menu = tk.Menu(
            self._root, tearoff=0,
            bg=_C["bg2"], fg=_C["fg"],
            activebackground=_C["disp_active_bg"], activeforeground=_C["cyan"],
            activeborderwidth=0, bd=1, font=("Segoe UI", 9),
        )
        menu.add_command(
            label=f"🖥️ Switch to Display {monitor_id}",
            command=lambda: self.switch_display(monitor_id),
        )
        menu.add_separator()
        if in_pair:
            menu.add_command(
                label=f"❌ Remove from F6 cycle (disable Display {monitor_id})",
                command=lambda: self.toggle_monitor_in_pair(monitor_id),
            )
        else:
            menu.add_command(
                label=f"✅ Add to F6 cycle (enable Display {monitor_id})",
                command=lambda: self.toggle_monitor_in_pair(monitor_id),
            )
        try:
            x = event.widget.winfo_rootx()
            y = event.widget.winfo_rooty() + event.widget.winfo_height() + 2
            menu.post(x, y)
        except Exception:
            pass

    def _save_current_to_profile(self, name: str) -> None:
        """Save current calibration into the named profile and update UI."""
        try:
            self.cfg.save_profile(name)
            self.cfg.switch_profile(name)  # also marks it as active
            if self._root:
                self._root.after(0, self._update_profile_selector_ui)
            print(f"[SOP HUD] Saved profile '{name}'")
        except Exception as exc:
            print(f"[SOP HUD] Error saving profile: {exc}")

    def _update_profile_selector_ui(self) -> None:
        """Highlight the active profile button (call from main thread only)."""
        active = self.cfg.get_active_profile()
        icons = {"home": "🏠", "office": "🏢"}
        for pname, btn in self._profile_btns.items():
            icon = icons.get(pname, "📌")
            label = f"{icon} {pname.upper()}"
            if pname == active:
                btn.config(text=f"{label} ✔", bg=_C["disp_active_bg"], fg=_C["cyan"])
            else:
                btn.config(text=label, bg=_C["btn_bg"], fg=_C["fg_dim"])

    def toggle_collapse(self) -> None:
        """Collapse or expand the Case buttons panel."""
        if not self._root:
            return
        cur_x = self._root.winfo_x()
        cur_y = self._root.winfo_y()

        if not self._is_collapsed:
            self._is_collapsed = True
            if self._suspect_frame:
                self._suspect_frame.pack_forget()
            if self._chrf_frame:
                self._chrf_frame.pack_forget()
            if self._collapse_btn:
                self._collapse_btn.config(text="▼ Expand", fg=_C["green"])
            self._root.geometry(f"{self.WINDOW_WIDTH}x{self.HEIGHT_COLLAPSED}+{cur_x}+{cur_y}")
        else:
            self._is_collapsed = False
            if self._collapse_btn:
                self._collapse_btn.config(text="▲ Collapse", fg=_C["fg_dim"])
            if self._active_sop_type == "SUSPECT":
                if self._suspect_frame:
                    self._suspect_frame.pack(fill="x")
                self._root.geometry(f"{self.WINDOW_WIDTH}x{self.HEIGHT_SUSPECT}+{cur_x}+{cur_y}")
            else:
                if self._chrf_frame:
                    self._chrf_frame.pack(fill="x")
                self._root.geometry(f"{self.WINDOW_WIDTH}x{self.HEIGHT_CHRF}+{cur_x}+{cur_y}")

    def _popup_type_menu(self, event: tk.Event) -> None:
        """Show dropdown menu to select SOP type (SUSPECT / CHRF)."""
        if not self._root:
            return

        menu = tk.Menu(
            self._root,
            tearoff=0,
            bg=_C["bg2"],
            fg=_C["fg"],
            activebackground=_C["disp_active_bg"],
            activeforeground=_C["cyan"],
            activeborderwidth=0,
            bd=1,
            font=("Segoe UI", 9),
        )
        menu.add_command(
            label="📁 SUSPECT (6 Cases: Ins, Home, PgUp, PgDn, End, Del)",
            command=lambda: self.switch_sop_type("SUSPECT"),
        )
        menu.add_command(
            label="⚡ CHRF (6 Cases: Ins, Home, PgUp, PgDn, End, Del)",
            command=lambda: self.switch_sop_type("CHRF"),
        )

        try:
            x = event.widget.winfo_rootx()
            y = event.widget.winfo_rooty() + event.widget.winfo_height() + 2
            menu.post(x, y)
        except Exception:
            pass

    def _popup_profile_save_menu(self, event: tk.Event, profile_name: str) -> None:
        """Right-click context menu on a profile button: switch or save calibration."""
        if not self._root:
            return

        menu = tk.Menu(
            self._root,
            tearoff=0,
            bg=_C["bg2"],
            fg=_C["fg"],
            activebackground=_C["disp_active_bg"],
            activeforeground=_C["cyan"],
            activeborderwidth=0,
            bd=1,
            font=("Segoe UI", 9),
        )
        icon = "🏠" if profile_name == "home" else "🏢"
        menu.add_command(
            label=f"{icon} Switch to {profile_name.upper()} profile",
            command=lambda: self.switch_profile(profile_name),
        )
        menu.add_separator()
        menu.add_command(
            label=f"💾 Save current setup to {profile_name.upper()}",
            command=lambda: self._save_current_to_profile(profile_name),
        )

        try:
            x = event.widget.winfo_rootx()
            y = event.widget.winfo_rooty() + event.widget.winfo_height() + 2
            menu.post(x, y)
        except Exception:
            pass

    # ── Thread-safe status update ─────────────────────────────────────────────

    def set_busy(self, case_name: str) -> None:
        with self._lock:
            self._status_text = "FILLING FORM..."
            self._status_color = _C["yellow"]
            self._detail_text = f"[Disp {self._active_display}] {case_name}"

    def set_done(self, message: str) -> None:
        with self._lock:
            self._status_text = "DONE!"
            self._status_color = _C["green"]
            self._detail_text = f"[Disp {self._active_display}] {message}"

    def set_ready(self) -> None:
        with self._lock:
            self._status_text = "READY"
            self._status_color = _C["green"]
            self._detail_text = f"Disp {self._active_display} [{self._active_sop_type}] — Ready"

    def set_detail(self, detail_msg: str) -> None:
        with self._lock:
            self._detail_text = detail_msg

    def set_error(self, err_msg: str) -> None:
        with self._lock:
            self._status_text = "ERROR!"
            self._status_color = _C["red"]
            self._detail_text = f"[Disp {self._active_display}] {err_msg}"

    def stop(self) -> None:
        self._running = False
        if self._root:
            try:
                self._root.after(0, self._root.quit)
            except Exception:
                pass

    # ── Main UI Build ─────────────────────────────────────────────────────────

    def run(self) -> None:
        self._running = True
        root = tk.Tk()
        self._root = root

        # Clamp initial position to ensure it is always visible on screen
        try:
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            if self._x < -2500 or self._x > 4500:
                self._x = 100
            if self._y < 10 or self._y > (sh - 100):
                self._y = 100
        except Exception:
            pass

        initial_h = self.HEIGHT_SUSPECT if self._active_sop_type == "SUSPECT" else self.HEIGHT_CHRF

        root.title("SOP Auto-Logging HUD")
        root.geometry(f"{self.WINDOW_WIDTH}x{initial_h}+{self._x}+{self._y}")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.96)
        root.overrideredirect(True)
        root.configure(bg=_C["bg"])

        self._build_widgets(root)
        self._bind_drag(root)
        self._update_display_selector_ui()
        self._schedule_refresh()

        try:
            root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self._running = False
            try:
                self.cfg.set("hud_x", root.winfo_x())
                self.cfg.set("hud_y", root.winfo_y())
                self.cfg.save()
            except Exception:
                pass
            try:
                root.destroy()
            except Exception:
                pass
            self._root = None

    def _build_widgets(self, root: tk.Tk) -> None:
        # ── 1. Header Bar (Drag zone) ─────────────────────────────────────────
        header = tk.Frame(root, bg=_C["header"], height=28)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="📋 SOP Auto-Logging HUD",
            bg=_C["header"], fg=_C["fg"],
            font=("Segoe UI", 9, "bold"),
            padx=8,
        ).pack(side="left", pady=4)

        # Close button
        btn_close = tk.Label(
            header, text="✕", bg=_C["header"], fg=_C["fg_dim"],
            font=("Segoe UI", 9, "bold"), padx=8, cursor="hand2"
        )
        btn_close.pack(side="right", pady=4)
        btn_close.bind("<Button-1>", lambda _: self._on_close())
        btn_close.bind("<Enter>", lambda _: btn_close.config(fg=_C["red"]))
        btn_close.bind("<Leave>", lambda _: btn_close.config(fg=_C["fg_dim"]))

        # ── 2. Profile Selector Bar (Home / Office) ──────────────────────────────
        profile_bar = tk.Frame(root, bg=_C["bg"], padx=6, pady=2)
        profile_bar.pack(fill="x")

        profile_lbl = tk.Label(
            profile_bar, text="🆔 PROFILE:",
            bg=_C["bg"], fg=_C["fg_dim"],
            font=("Segoe UI", 7, "bold"),
        )
        profile_lbl.pack(side="left", padx=(0, 4))

        profile_container = tk.Frame(profile_bar, bg=_C["bg2"], padx=2, pady=1)
        profile_container.pack(fill="x", expand=True)

        profiles = self.cfg.list_profiles()
        icons = {"home": "🏠", "office": "🏢"}
        active_profile = self.cfg.get_active_profile()
        for pname in profiles:
            icon = icons.get(pname, "📌")
            is_active = (pname == active_profile)
            label_text = f"{icon} {pname.upper()}" + (" ✔" if is_active else "")
            pbtn = tk.Label(
                profile_container,
                text=label_text,
                font=("Segoe UI", 8, "bold"),
                bg=_C["disp_active_bg"] if is_active else _C["btn_bg"],
                fg=_C["cyan"] if is_active else _C["fg_dim"],
                padx=8, pady=2, cursor="hand2",
            )
            pbtn.pack(side="left", fill="x", expand=True, padx=1)
            # Bind left-click to switch
            pbtn.bind("<Button-1>", lambda _, n=pname: self.switch_profile(n))
            # Bind right-click to save context menu
            pbtn.bind("<Button-3>", lambda e, n=pname: self._popup_profile_save_menu(e, n))
            pbtn.bind("<Enter>", lambda e, b=pbtn, a=(pname == active_profile):
                      b.config(bg=_C["btn_hover"] if not a else _C["disp_active_bg"]))
            pbtn.bind("<Leave>", lambda e, b=pbtn, n=pname:
                      b.config(bg=_C["disp_active_bg"] if n == self.cfg.get_active_profile()
                               else _C["btn_bg"]))
            self._profile_btns[pname] = pbtn

        # ── 3. Display Selector Bar (All Monitors) ───────────────────────────
        disp_outer = tk.Frame(root, bg=_C["bg"], padx=6, pady=2)
        disp_outer.pack(fill="x")

        disp_lbl = tk.Label(
            disp_outer, text="🖥️ DISP:",
            bg=_C["bg"], fg=_C["fg_dim"],
            font=("Segoe UI", 7, "bold"),
        )
        disp_lbl.pack(side="left", padx=(0, 4))

        disp_container = tk.Frame(disp_outer, bg=_C["bg2"], padx=2, pady=2)
        disp_container.pack(fill="x", expand=True)

        pair = self._disp_pair
        # Build all 4 monitor buttons
        for mid in [1, 2, 3, 4]:
            in_pair = mid in pair
            is_active = (mid == self._active_display)
            if is_active:
                bg, fg, prefix = _C["disp_active_bg"], _C["disp_active_fg"], "● "
            elif in_pair:
                bg, fg, prefix = "#1a3a1a", "#44cc66", "◦ "
            else:
                bg, fg, prefix = _C["btn_bg"], _C["fg_dim"], ""

            btn = tk.Label(
                disp_container,
                text=f"{prefix}M{mid}",
                font=("Segoe UI", 8, "bold"),
                bg=bg, fg=fg,
                padx=6, pady=3, cursor="hand2",
                width=4,
            )
            btn.pack(side="left", fill="x", expand=True, padx=1)
            btn.bind("<Button-1>", lambda _, m=mid: self.switch_display(m))
            btn.bind("<Button-3>", lambda e, m=mid: self._popup_monitor_menu(e, m))
            self._all_disp_btns[mid] = btn

        # Right-side hint label
        tk.Label(
            disp_outer,
            text="🛈",
            bg=_C["bg"], fg=_C["fg_dim"],
            font=("Segoe UI", 9),
            cursor="hand2",
        ).pack(side="right", padx=(2, 0))

        # Add a small legend below the buttons
        legend = tk.Frame(root, bg=_C["bg"], padx=6)
        legend.pack(fill="x")
        tk.Label(
            legend,
            text="● Active ◦ F6-cycle  • Off  |  Right-click to toggle",
            bg=_C["bg"], fg=_C["fg_dim"],
            font=("Segoe UI", 6, "italic"),
        ).pack(side="left")

        # ── 3. Type Selector Bar (Dropdown SUSPECT / CHRF) ─────────────────────
        type_bar = tk.Frame(root, bg=_C["bg"], padx=6, pady=2)
        type_bar.pack(fill="x")

        type_container = tk.Frame(
            type_bar,
            bg=_C["bg2"],
            padx=4,
            pady=2,
            highlightbackground=_C["border"],
            highlightthickness=1,
        )
        type_container.pack(fill="x")

        tk.Label(
            type_container,
            text="📂 TYPE:",
            font=("Segoe UI", 8, "bold"),
            bg=_C["bg2"],
            fg=_C["fg_dim"],
        ).pack(side="left", padx=(2, 6))

        type_text = "▼ SUSPECT (6 Cases)" if self._active_sop_type == "SUSPECT" else "▼ CHRF (6 Cases)"
        type_fg = _C["cyan"] if self._active_sop_type == "SUSPECT" else _C["yellow"]

        self._type_btn = tk.Label(
            type_container,
            text=type_text,
            font=("Segoe UI", 8, "bold"),
            bg=_C["disp_active_bg"],
            fg=type_fg,
            padx=8,
            pady=3,
            cursor="hand2",
        )
        self._type_btn.pack(side="left", fill="x", expand=True)
        self._type_btn.bind("<Button-1>", self._popup_type_menu)
        self._type_btn.bind("<Enter>", lambda _: self._type_btn.config(bg=_C["btn_hover"]))
        self._type_btn.bind("<Leave>", lambda _: self._type_btn.config(bg=_C["disp_active_bg"]))

        self._collapse_btn = tk.Label(
            type_container,
            text="▲ Collapse",
            font=("Segoe UI", 8),
            bg=_C["btn_bg"],
            fg=_C["fg_dim"],
            padx=6,
            pady=3,
            cursor="hand2",
        )
        self._collapse_btn.pack(side="right", padx=(4, 0))
        self._collapse_btn.bind("<Button-1>", lambda _: self.toggle_collapse())
        self._collapse_btn.bind("<Enter>", lambda _: self._collapse_btn.config(fg=_C["yellow"]))
        self._collapse_btn.bind("<Leave>", lambda _: self._collapse_btn.config(fg=_C["fg_dim"]))

        # ── 4. Status Zone ────────────────────────────────────────────────────
        status_bar = tk.Frame(root, bg=_C["bg2"], padx=8, pady=4)
        status_bar.pack(fill="x", padx=6, pady=(2, 3))

        status_row = tk.Frame(status_bar, bg=_C["bg2"])
        status_row.pack(fill="x")

        self._dot_label = tk.Label(
            status_row, text="●", bg=_C["bg2"], fg=self._status_color, font=("Segoe UI", 10)
        )
        self._dot_label.pack(side="left", padx=(0, 5))

        self._status_label = tk.Label(
            status_row, text=self._status_text, bg=_C["bg2"], fg=_C["fg"],
            font=("Segoe UI", 9, "bold")
        )
        self._status_label.pack(side="left")

        self._detail_label = tk.Label(
            status_bar, text=self._detail_text, bg=_C["bg2"], fg=_C["fg_dim"],
            font=("Segoe UI", 8), anchor="w", justify="left"
        )
        self._detail_label.pack(fill="x", pady=(1, 0))

        # ── 5. Cases Zone (SUSPECT & CHRF Panels) ─────────────────────────────
        cases_container = tk.Frame(root, bg=_C["bg"], padx=6, pady=1)
        cases_container.pack(fill="x")

        # SUSPECT Cases Container
        self._suspect_frame = tk.Frame(cases_container, bg=_C["bg"])
        self._build_case_buttons(self._suspect_frame, SUSPECT_DEFS)

        # CHRF Cases Container
        self._chrf_frame = tk.Frame(cases_container, bg=_C["bg"])
        self._build_case_buttons(self._chrf_frame, CHRF_DEFS)

        # Show the panel matching the active SOP type
        if self._active_sop_type == "SUSPECT":
            self._suspect_frame.pack(fill="x")
        else:
            self._chrf_frame.pack(fill="x")

        # ── 6. Quick Clipboard Zone (Click-to-Copy Keywords) ─────────────────
        kw_section = tk.Frame(root, bg=_C["bg"], padx=6)
        kw_section.pack(fill="x", pady=(3, 1))

        # Header for Keywords
        kw_hdr = tk.Frame(kw_section, bg=_C["bg"])
        kw_hdr.pack(fill="x", pady=(0, 2))

        tk.Label(
            kw_hdr,
            text="🏷️ QUICK CLIPBOARD (Click to Copy)",
            bg=_C["bg"],
            fg=_C["fg_dim"],
            font=("Segoe UI", 7, "bold"),
            anchor="w",
        ).pack(side="left")

        # 2 Columns Grid
        kw_grid = tk.Frame(kw_section, bg=_C["bg"])
        kw_grid.pack(fill="x")
        kw_grid.columnconfigure(0, weight=1)
        kw_grid.columnconfigure(1, weight=1)

        for idx, (kw, icon, display_title, desc) in enumerate(KEYWORD_DEFS):
            row = idx // 2
            col = idx % 2

            btn_f = tk.Frame(
                kw_grid,
                bg=_C.get("kw_bg", "#151928"),
                highlightbackground=_C["border"],
                highlightthickness=1,
                cursor="hand2",
                padx=4,
                pady=2,
            )
            btn_f.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)

            lbl_icon = tk.Label(
                btn_f,
                text=icon,
                bg=_C.get("kw_bg", "#151928"),
                fg=_C["fg"],
                font=("Segoe UI", 7),
            )
            lbl_icon.pack(side="left", padx=(0, 2))

            lbl_txt = tk.Label(
                btn_f,
                text=display_title,
                bg=_C.get("kw_bg", "#151928"),
                fg=_C.get("kw_fg", "#00e5ff"),
                font=("Segoe UI", 7, "bold"),
                anchor="w",
            )
            lbl_txt.pack(side="left", fill="x", expand=True)

            def _make_kw_click(k=kw, lt=lbl_txt, orig=display_title):
                return lambda _: self._copy_keyword(k, lt, orig)

            def _make_kw_hover_in(f=btn_f, d=desc, k=kw):
                return lambda _: self._kw_hover_on(f, d, k)

            def _make_kw_hover_out(f=btn_f):
                return lambda _: self._kw_hover_off(f)

            kw_click_cb = _make_kw_click()
            kw_hin_cb   = _make_kw_hover_in()
            kw_hout_cb  = _make_kw_hover_out()

            for w in (btn_f, lbl_icon, lbl_txt):
                w.bind("<Button-1>", kw_click_cb)
                w.bind("<Enter>", kw_hin_cb)
                w.bind("<Leave>", kw_hout_cb)

        # ── 7. Footer Hint ────────────────────────────────────────────────────
        footer = tk.Frame(root, bg=_C["bg"], height=16)
        footer.pack(fill="x", side="bottom", pady=(0, 2))

        pair_str = "/".join(str(d) for d in self._disp_pair)
        init_hint = f"F6: Disp {pair_str} | Ins..Del: Form | R-click Disp: toggle | ESC"

        self._footer_label = tk.Label(
            footer, text=init_hint,
            bg=_C["bg"], fg=_C["fg_dim"], font=("Segoe UI", 7)
        )
        self._footer_label.pack(expand=True)

    def _build_case_buttons(self, parent: tk.Frame, case_defs: list[tuple[str, str, str, str]]) -> None:
        """Build list of Case button rows in a panel."""
        for case_key, label_main, key_hint, subtitle in case_defs:
            btn_frame = tk.Frame(parent, bg=_C["btn_bg"], cursor="hand2", padx=6, pady=2)
            btn_frame.pack(fill="x", pady=1)

            left_box = tk.Frame(btn_frame, bg=_C["btn_bg"])
            left_box.pack(side="left", fill="y")

            lbl_name = tk.Label(
                left_box, text=f"[{label_main}]", bg=_C["btn_bg"], fg=_C["blue"],
                font=("Segoe UI", 8, "bold")
            )
            lbl_name.pack(side="left")

            lbl_sub = tk.Label(
                left_box, text=f" {subtitle}", bg=_C["btn_bg"], fg=_C["fg"],
                font=("Segoe UI", 8)
            )
            lbl_sub.pack(side="left")

            lbl_key = tk.Label(
                btn_frame, text=f"({key_hint})", bg=_C["btn_bg"], fg=_C["yellow"],
                font=("Segoe UI", 8, "bold")
            )
            lbl_key.pack(side="right")

            def _make_click_cb(k: str):
                return lambda _: self._trigger(k)

            def _make_hover_in(f: tk.Frame):
                return lambda _: self._hover_on(f)

            def _make_hover_out(f: tk.Frame):
                return lambda _: self._hover_off(f)

            click_cb = _make_click_cb(case_key)
            hin_cb = _make_hover_in(btn_frame)
            hout_cb = _make_hover_out(btn_frame)

            for w in (btn_frame, left_box, lbl_name, lbl_sub, lbl_key):
                w.bind("<Button-1>", click_cb)
                w.bind("<Enter>", hin_cb)
                w.bind("<Leave>", hout_cb)

            self._buttons[case_key] = btn_frame

    def _update_display_selector_ui(self) -> None:
        """Refresh all 4 monitor buttons to reflect active display and current pair."""
        if not self._all_disp_btns:
            return
        pair = self._disp_pair
        for mid, btn in self._all_disp_btns.items():
            is_active = (mid == self._active_display)
            in_pair = mid in pair
            try:
                if is_active:
                    btn.config(text=f"● M{mid}", bg=_C["disp_active_bg"], fg=_C["disp_active_fg"])
                elif in_pair:
                    btn.config(text=f"◦ M{mid}", bg="#1a3a1a", fg="#44cc66")
                else:
                    btn.config(text=f"M{mid}", bg=_C["btn_bg"], fg=_C["fg_dim"])
            except Exception:
                pass

    def _update_footer_hint(self) -> None:
        """Update the footer F6 hint to show which monitors are in the cycle."""
        if not self._footer_label:
            return
        try:
            pair_str = "/".join(str(d) for d in self._disp_pair)
            self._footer_label.config(
                text=f"F6: Disp {pair_str} | Ins..Del: Form | R-click Disp: toggle | ESC"
            )
        except Exception:
            pass


    def _hover_on(self, frame: tk.Frame) -> None:
        for w in [frame] + list(frame.winfo_children()):
            try:
                w.config(bg=_C["btn_hover"])
                for sub in w.winfo_children():
                    sub.config(bg=_C["btn_hover"])
            except Exception:
                pass

    def _hover_off(self, frame: tk.Frame) -> None:
        for w in [frame] + list(frame.winfo_children()):
            try:
                w.config(bg=_C["btn_bg"])
                for sub in w.winfo_children():
                    sub.config(bg=_C["btn_bg"])
            except Exception:
                pass

    def _copy_keyword(self, kw: str, lbl: tk.Label, orig_text: str) -> None:
        """Copy keyword to Windows Clipboard with visual feedback."""
        if not self._root:
            return
        try:
            self._root.clipboard_clear()
            self._root.clipboard_append(kw)
            self._root.update()
        except Exception:
            pass

        with self._lock:
            self._status_text = "COPIED KEYWORD!"
            self._status_color = _C["cyan"]
            self._detail_text = f"📋 Copied: {kw}"

        try:
            lbl.config(text="✓ COPIED!", fg=_C["green"])
            self._root.after(700, lambda: self._restore_kw(lbl, orig_text))
        except Exception:
            pass

    def _restore_kw(self, lbl: tk.Label, orig_text: str) -> None:
        try:
            lbl.config(text=orig_text, fg=_C.get("kw_fg", "#00e5ff"))
        except Exception:
            pass

    def _kw_hover_on(self, frame: tk.Frame, desc: str, kw: str) -> None:
        for w in [frame] + list(frame.winfo_children()):
            try:
                w.config(bg=_C.get("kw_hover", "#242d4a"))
            except Exception:
                pass
        with self._lock:
            self._detail_text = f"💡 {desc}"

    def _kw_hover_off(self, frame: tk.Frame) -> None:
        for w in [frame] + list(frame.winfo_children()):
            try:
                w.config(bg=_C.get("kw_bg", "#151928"))
            except Exception:
                pass
        with self._lock:
            self._detail_text = f"Disp {self._active_display} [{self._active_sop_type}] — Ready"

    def _trigger(self, case_key: str) -> None:
        """Trigger when clicking a case button on HUD."""
        if self.on_trigger_case:
            threading.Thread(target=self.on_trigger_case, args=(case_key,), daemon=True).start()

    def _on_close(self) -> None:
        if self.on_exit:
            self.on_exit()
        self.stop()

    # ── Drag Window ───────────────────────────────────────────────────────────

    def _bind_drag(self, root: tk.Tk) -> None:
        root.bind("<ButtonPress-1>", self._on_drag_start)
        root.bind("<B1-Motion>", self._on_drag_motion)

    def _on_drag_start(self, event: tk.Event) -> None:
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag_motion(self, event: tk.Event) -> None:
        if not self._root:
            return
        dx = event.x - self._drag_x
        dy = event.y - self._drag_y
        new_x = self._root.winfo_x() + dx
        new_y = self._root.winfo_y() + dy
        self._root.geometry(f"+{new_x}+{new_y}")

    # ── Refresh Loop ──────────────────────────────────────────────────────────

    def _schedule_refresh(self) -> None:
        if not self._running or not self._root:
            return
        with self._lock:
            st = self._status_text
            sc = self._status_color
            dt = self._detail_text

        try:
            if self._dot_label:
                self._dot_label.config(fg=sc)
            if self._status_label:
                self._status_label.config(text=st)
            if self._detail_label:
                display_dt = dt if len(dt) <= 40 else dt[:37] + "..."
                self._detail_label.config(text=display_dt)
        except Exception:
            pass

        self._root.after(100, self._schedule_refresh)
