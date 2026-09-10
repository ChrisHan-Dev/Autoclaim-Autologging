"""
sop_hud.py — Floating Status HUD for SOP Logging (Multi-Display Support)
========================================================================
Bảng điều khiển nhỏ gọn (Always-On-Top, Draggable) trên màn hình.
Cho phép:
  - Xem trạng thái trực quan (Sẵn sàng, Đang điền, Hoàn tất)
  - Chọn chuyển đổi nhanh giữa Màn hình 4 (Main) và Màn hình 3 (Click nút hoặc bấm F6)
  - Click trực tiếp vào nút Case 1..5 bằng chuột
  - Nhấn phím tắt Insert, Home, PgUp, PgDn, End song song
  - Tự động focus vào cửa sổ Teleops trên màn hình đã chọn
"""

from __future__ import annotations

import threading
import time
import tkinter as tk
from typing import Callable, Optional

# Color palette (đồng nhất với giao diện Dark Modern)
_C = {
    "bg":        "#0f0f1a",
    "bg2":       "#1a1a2e",
    "header":    "#16213e",
    "border":    "#2a2a4a",
    "fg":        "#e0e0e0",
    "fg_dim":    "#8a8aab",
    "green":     "#00d084",
    "red":       "#ff4757",
    "yellow":    "#ffa502",
    "blue":      "#1e90ff",
    "cyan":      "#00e5ff",
    "btn_bg":    "#1f2438",
    "btn_hover": "#2d3553",
    "btn_active":"#1652f0",
    "disp_active_bg": "#0f3460",
    "disp_active_fg": "#00e5ff",
}


class SOPStatusHUD:
    """
    Floating always-on-top HUD window for SOP Logging.
    Hỗ trợ chuyển đổi giữa 2 màn hình (Màn 4 Main và Màn 3) trên cùng 1 Popup.
    """

    WINDOW_WIDTH = 320
    WINDOW_HEIGHT = 355

    def __init__(
        self,
        cfg,
        on_trigger_case: Callable[[str], None],
        on_exit: Callable[[], None],
        on_switch_display: Optional[Callable[[int], None]] = None,
    ) -> None:
        self.cfg = cfg
        self.on_trigger_case = on_trigger_case  # callback(case_key: 'f1'|'f2'|'f3'|'f4'|'f5')
        self.on_exit = on_exit
        self.on_switch_display = on_switch_display

        self._root: Optional[tk.Tk] = None
        self._running = False
        self._lock = threading.Lock()

        # Display pair: [4, 3]
        self._disp_pair = self.cfg.get_active_pair()
        if len(self._disp_pair) < 2:
            self._disp_pair = [4, 3]

        # State fields
        self._active_display = self.cfg.get_active_display()
        self._status_text = "SẴN SÀNG"
        self._status_color = _C["green"]
        self._detail_text = f"Màn hình {self._active_display} — Nhấn phím hoặc click nút"

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
        self._buttons: dict[str, tk.Frame] = {}

    # ── Multi-Display Switch ──────────────────────────────────────────────────

    def switch_display(self, display_id: int) -> None:
        """Chuyển màn hình active an toàn giữa các thread."""
        with self._lock:
            self._active_display = display_id
            self.cfg.set_active_display(display_id)
            calibrated = self.cfg.is_calibrated(display_id)
            status_suffix = "" if calibrated else " (Chưa Calibrate!)"
            self._detail_text = f"Màn hình {display_id}{status_suffix} — Nhấn phím hoặc click"

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
            self._detail_text = f"Màn hình {self._active_display} — Nhấn phím hoặc click"

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

        root.title("SOP Auto-Fill HUD")
        root.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}+{self._x}+{self._y}")
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
        # ── Header Bar (Drag zone) ─────────────────────────────────────────────
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

        # ── Display Selector Bar (Màn 4 / Màn 3) ────────────────────────────────
        disp_bar = tk.Frame(root, bg=_C["bg"], padx=6, pady=4)
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
            padx=10, pady=4,
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
            padx=10, pady=4,
            cursor="hand2",
        )
        self._disp_btn_2.pack(side="left", fill="x", expand=True, padx=1)
        self._disp_btn_2.bind("<Button-1>", lambda _: self.switch_display(d2))

        # ── Status Zone ────────────────────────────────────────────────────────
        status_bar = tk.Frame(root, bg=_C["bg2"], padx=8, pady=5)
        status_bar.pack(fill="x", padx=6, pady=(2, 4))

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
        self._detail_label.pack(fill="x", pady=(2, 0))

        # ── Buttons Zone (5 Cases) ─────────────────────────────────────────────
        btn_container = tk.Frame(root, bg=_C["bg"], padx=6, pady=1)
        btn_container.pack(fill="both", expand=True)

        case_defs = [
            ("f1", "Case 1", "Insert", "All cam / Align+Extract / Success"),
            ("f2", "Case 2", "Home",   "No cam / No action / Unsuccessful"),
            ("f3", "Case 3", "PgUp",   "All cam / Not pickable"),
            ("f4", "Case 4", "PgDn",   "All cam / Align+Ext / CHD"),
            ("f5", "Case 5", "End",    "All cam / No action / No case / Success"),
            ("f6", "Case 6", "Del",    "All cam / No action / Rogue / CHD"),
        ]

        for case_key, label_main, key_hint, subtitle in case_defs:
            btn_frame = tk.Frame(btn_container, bg=_C["btn_bg"], cursor="hand2", padx=6, pady=2)
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

        # ── Footer Hint ────────────────────────────────────────────────────────
        d1, d2 = self._disp_pair[0], self._disp_pair[1]
        footer = tk.Frame(root, bg=_C["bg"], height=16)
        footer.pack(fill="x", side="bottom", pady=(0, 2))
        tk.Label(
            footer, text=f"F6: Đổi Màn {d1}/{d2} | Ins..Del: Điền Form | ESC: Thoát",
            bg=_C["bg"], fg=_C["fg_dim"], font=("Segoe UI", 7)
        ).pack(expand=True)

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
