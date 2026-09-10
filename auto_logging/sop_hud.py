"""
sop_hud.py — Floating Status HUD for SOP Logging (Multi-Display & Multi-Type Support)
====================================================================================
Bảng điều khiển nhỏ gọn (Always-On-Top, Draggable) trên màn hình.
Cho phép:
  - Xem trạng thái trực quan (Sẵn sàng, Đang điền, Hoàn tất)
  - Chuyển đổi nhanh Màn hình 4 (Main) <-> Màn hình 3 (Click nút hoặc bấm F6)
  - Chọn Loại SOP qua Dropdown:
      * SUSPECT (6 Cases: Case 1..6)
      * CHRF (4 Cases: Charger Recovery)
    Khi chọn loại nào thì bảng loại đó hiện lên và được lưu nhớ (giữ nguyên ở đó).
  - Nút [▲ Đóng / ▼ Mở] để tuỳ ý thu gọn bảng Case khi cần.
  - Click trực tiếp vào từng Case trên HUD hoặc nhấn Hotkeys tương ứng.
  - Quick Clipboard: Click 1 chạm để copy các từ khoá sự cố (bh_...)
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

# ── Danh sách Keyword sự cố nhanh (Click để Copy vào Clipboard) ────────────────
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

# ── Danh sách Case cho SUSPECT (6 Cases) ───────────────────────────────────────
SUSPECT_DEFS: list[tuple[str, str, str, str]] = [
    ("f1", "Case 1", "Insert", "All cam / Align+Extract / Success"),
    ("f2", "Case 2", "Home",   "No cam / No action / Unsuccessful"),
    ("f3", "Case 3", "PgUp",   "All cam / Not pickable"),
    ("f4", "Case 4", "PgDn",   "All cam / Align+Ext / CHD"),
    ("f5", "Case 5", "End",    "All cam / No action / No case / Success"),
    ("f6", "Case 6", "Del",    "All cam / No action / Rogue / CHD"),
]

# ── Danh sách Case cho CHRF (6 Cases) ──────────────────────────────────────────
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
    Hỗ trợ chuyển đổi giữa 2 màn hình (Màn 4 Main và Màn 3) trên cùng 1 Popup.
    Hỗ trợ Dropdown chuyển đổi giữa loại SUSPECT (6 cases) và CHRF (6 cases).
    Tích hợp Quick Clipboard (Click để Copy từ khoá sự cố).
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
    ) -> None:
        self.cfg = cfg
        self.on_trigger_case = on_trigger_case
        self.on_exit = on_exit
        self.on_switch_display = on_switch_display
        self.on_switch_sop_type = on_switch_sop_type

        self._root: Optional[tk.Tk] = None
        self._running = False
        self._lock = threading.Lock()

        # Display pair: [4, 3]
        self._disp_pair = self.cfg.get_active_pair()
        if len(self._disp_pair) < 2:
            self._disp_pair = [4, 3]

        # Active SOP Type ("SUSPECT" or "CHRF")
        self._active_sop_type = self.cfg.get_active_sop_type()
        self._is_collapsed = False

        # State fields
        self._active_display = self.cfg.get_active_display()
        self._status_text = "SẴN SÀNG"
        self._status_color = _C["green"]
        self._detail_text = f"Màn {self._active_display} [{self._active_sop_type}] — Sẵn sàng"

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
        self._disp_btn_1: Optional[tk.Label] = None
        self._disp_btn_2: Optional[tk.Label] = None
        self._type_btn: Optional[tk.Label] = None
        self._collapse_btn: Optional[tk.Label] = None
        self._suspect_frame: Optional[tk.Frame] = None
        self._chrf_frame: Optional[tk.Frame] = None
        self._footer_label: Optional[tk.Label] = None
        self._buttons: dict[str, tk.Frame] = {}

    # ── Multi-Display Switch ──────────────────────────────────────────────────

    def switch_display(self, display_id: int) -> None:
        """Chuyển màn hình active an toàn giữa các thread."""
        with self._lock:
            self._active_display = display_id
            self.cfg.set_active_display(display_id)
            calibrated = self.cfg.is_calibrated(display_id)
            status_suffix = "" if calibrated else " (Chưa Calib!)"
            self._detail_text = f"Màn {display_id} [{self._active_sop_type}]{status_suffix} — Sẵn sàng"

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
        """Đổi qua lại giữa 2 màn hình trong cặp (vd: Màn 4 <-> Màn 3)."""
        d1, d2 = self._disp_pair[0], self._disp_pair[1]
        new_disp = d2 if self._active_display == d1 else d1
        self.switch_display(new_disp)

    def toggle_sop_type(self) -> None:
        """Đổi qua lại giữa SUSPECT <-> CHRF (bấm F7)."""
        nxt = "CHRF" if self._active_sop_type == "SUSPECT" else "SUSPECT"
        self.switch_sop_type(nxt)

    # ── SOP Type Switch (SUSPECT <-> CHRF) ─────────────────────────────────────

    def switch_sop_type(self, new_type: str) -> None:
        """Chuyển đổi loại SOP (SUSPECT hoặc CHRF), lưu vào config và cập nhật UI."""
        new_type = new_type.upper()
        with self._lock:
            self._active_sop_type = new_type
            self.cfg.set_active_sop_type(new_type)
            self._is_collapsed = False
            self._detail_text = f"Màn {self._active_display} [{new_type}] — Sẵn sàng"

        if not self._root:
            return

        try:
            cur_x = self._root.winfo_x()
            cur_y = self._root.winfo_y()
            d1, d2 = self._disp_pair[0], self._disp_pair[1]

            if self._collapse_btn:
                self._collapse_btn.config(text="▲ Đóng", fg=_C["fg_dim"])

            if new_type == "SUSPECT":
                if self._type_btn:
                    self._type_btn.config(text="▼ SUSPECT (6 Cases)", fg=_C["cyan"])
                if self._chrf_frame:
                    self._chrf_frame.pack_forget()
                if self._suspect_frame:
                    self._suspect_frame.pack(fill="x")
                if self._footer_label:
                    self._footer_label.config(text=f"F6: Màn {d1}/{d2} | F7: Đổi Loại | Ins..Del: Form | ESC")
                self._root.geometry(f"{self.WINDOW_WIDTH}x{self.HEIGHT_SUSPECT}+{cur_x}+{cur_y}")
            else:
                if self._type_btn:
                    self._type_btn.config(text="▼ CHRF (6 Cases)", fg=_C["yellow"])
                if self._suspect_frame:
                    self._suspect_frame.pack_forget()
                if self._chrf_frame:
                    self._chrf_frame.pack(fill="x")
                if self._footer_label:
                    self._footer_label.config(text=f"F6: Màn {d1}/{d2} | Ins..Del: Form | ESC")
                self._root.geometry(f"{self.WINDOW_WIDTH}x{self.HEIGHT_CHRF}+{cur_x}+{cur_y}")
        except Exception as e:
            print(f"[SOP HUD] Lỗi đổi loại SOP: {e}")

        if self.on_switch_sop_type:
            try:
                self.on_switch_sop_type(new_type)
            except Exception:
                pass

    def toggle_collapse(self) -> None:
        """Thu gọn hoặc mở rộng bảng Case."""
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
                self._collapse_btn.config(text="▼ Mở", fg=_C["green"])
            self._root.geometry(f"{self.WINDOW_WIDTH}x{self.HEIGHT_COLLAPSED}+{cur_x}+{cur_y}")
        else:
            self._is_collapsed = False
            if self._collapse_btn:
                self._collapse_btn.config(text="▲ Đóng", fg=_C["fg_dim"])
            if self._active_sop_type == "SUSPECT":
                if self._suspect_frame:
                    self._suspect_frame.pack(fill="x")
                self._root.geometry(f"{self.WINDOW_WIDTH}x{self.HEIGHT_SUSPECT}+{cur_x}+{cur_y}")
            else:
                if self._chrf_frame:
                    self._chrf_frame.pack(fill="x")
                self._root.geometry(f"{self.WINDOW_WIDTH}x{self.HEIGHT_CHRF}+{cur_x}+{cur_y}")

    def _popup_type_menu(self, event: tk.Event) -> None:
        """Hiển thị menu dropdown chọn loại SOP (SUSPECT / CHRF)."""
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

    # ── Thread-safe status update ─────────────────────────────────────────────

    def set_busy(self, case_name: str) -> None:
        with self._lock:
            self._status_text = "ĐANG ĐIỀN FORM..."
            self._status_color = _C["yellow"]
            self._detail_text = f"[Màn {self._active_display}] {case_name}"

    def set_done(self, message: str) -> None:
        with self._lock:
            self._status_text = "HOÀN TẤT!"
            self._status_color = _C["green"]
            self._detail_text = f"[Màn {self._active_display}] {message}"

    def set_ready(self) -> None:
        with self._lock:
            self._status_text = "SẴN SÀNG"
            self._status_color = _C["green"]
            self._detail_text = f"Màn {self._active_display} [{self._active_sop_type}] — Sẵn sàng"

    def set_detail(self, detail_msg: str) -> None:
        with self._lock:
            self._detail_text = detail_msg

    def set_error(self, err_msg: str) -> None:
        with self._lock:
            self._status_text = "LỖI!"
            self._status_color = _C["red"]
            self._detail_text = f"[Màn {self._active_display}] {err_msg}"

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

        # Clamp initial position
        try:
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            if self._x < -3000 or self._x > 5000:
                self._x = 80
            if self._y < -3000 or self._y > 5000:
                self._y = 80
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

        # ── 2. Display Selector Bar (Màn 4 / Màn 3) ────────────────────────────
        disp_bar = tk.Frame(root, bg=_C["bg"], padx=6, pady=3)
        disp_bar.pack(fill="x")

        disp_container = tk.Frame(disp_bar, bg=_C["bg2"], padx=2, pady=2)
        disp_container.pack(fill="x")

        d1, d2 = self._disp_pair[0], self._disp_pair[1]
        name1 = f"🖥️ MÀN {d1} (Main)" if d1 == 4 else f"🖥️ MÀN {d1}"
        name2 = f"🖥️ MÀN {d2} (Main)" if d2 == 4 else f"🖥️ MÀN {d2}"

        # Tab Màn D1
        self._disp_btn_1 = tk.Label(
            disp_container,
            text=name1,
            font=("Segoe UI", 8, "bold"),
            bg=_C["disp_active_bg"],
            fg=_C["disp_active_fg"],
            padx=10, pady=3,
            cursor="hand2",
        )
        self._disp_btn_1.pack(side="left", fill="x", expand=True, padx=1)
        self._disp_btn_1.bind("<Button-1>", lambda _: self.switch_display(d1))

        # Tab Màn D2
        self._disp_btn_2 = tk.Label(
            disp_container,
            text=name2,
            font=("Segoe UI", 8, "bold"),
            bg=_C["btn_bg"],
            fg=_C["fg_dim"],
            padx=10, pady=3,
            cursor="hand2",
        )
        self._disp_btn_2.pack(side="left", fill="x", expand=True, padx=1)
        self._disp_btn_2.bind("<Button-1>", lambda _: self.switch_display(d2))

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
            text="📂 LOẠI SOP:",
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
            text="▲ Đóng",
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

        # Hiển thị đúng bảng loại đã lưu trong config
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
            text="🏷️ QUICK CLIPBOARD (Click để Copy)",
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

        init_hint = f"F6: Màn {d1}/{d2} | Ins..Del: Form | Click KW: Copy | ESC"

        self._footer_label = tk.Label(
            footer, text=init_hint,
            bg=_C["bg"], fg=_C["fg_dim"], font=("Segoe UI", 7)
        )
        self._footer_label.pack(expand=True)

    def _build_case_buttons(self, parent: tk.Frame, case_defs: list[tuple[str, str, str, str]]) -> None:
        """Tạo danh sách các hàng nút Case trong 1 panel."""
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
        """Cập nhật giao diện tab chọn màn hình khi chuyển đổi."""
        if not self._disp_btn_1 or not self._disp_btn_2:
            return

        d1, d2 = self._disp_pair[0], self._disp_pair[1]
        name1 = f"MÀN {d1} (Main)" if d1 == 4 else f"MÀN {d1}"
        name2 = f"MÀN {d2} (Main)" if d2 == 4 else f"MÀN {d2}"

        is_1 = (self._active_display == d1)
        if is_1:
            self._disp_btn_1.config(
                bg=_C["disp_active_bg"],
                fg=_C["disp_active_fg"],
                text=f"● 🖥️ {name1}",
            )
            self._disp_btn_2.config(
                bg=_C["btn_bg"],
                fg=_C["fg_dim"],
                text=f"🖥️ {name2}",
            )
        else:
            self._disp_btn_1.config(
                bg=_C["btn_bg"],
                fg=_C["fg_dim"],
                text=f"🖥️ {name1}",
            )
            self._disp_btn_2.config(
                bg=_C["disp_active_bg"],
                fg=_C["disp_active_fg"],
                text=f"● 🖥️ {name2}",
            )

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
        """Sao chép keyword vào Windows Clipboard và phản hồi trực quan tức thì."""
        if not self._root:
            return
        try:
            self._root.clipboard_clear()
            self._root.clipboard_append(kw)
            self._root.update()
        except Exception:
            pass

        with self._lock:
            self._status_text = "ĐÃ COPY KEYWORD!"
            self._status_color = _C["cyan"]
            self._detail_text = f"📋 Đã chép: {kw}"

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
            self._detail_text = f"Màn {self._active_display} [{self._active_sop_type}] — Sẵn sàng"

    def _trigger(self, case_key: str) -> None:
        """Trigger khi click vào nút trên HUD."""
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
