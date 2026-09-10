"""
status_window.py — Floating Status HUD
A compact, draggable, always-on-top window showing live automation status.

Runs on the main thread and polls a ui_queue for events.
"""

from __future__ import annotations

import threading
import time
import tkinter as tk
from typing import Callable, Optional
import queue

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
_C = {
    "bg":       "#0f0f1a",
    "bg2":      "#1a1a2e",
    "header":   "#16213e",
    "border":   "#2a2a4a",
    "fg":       "#e0e0e0",
    "fg_dim":   "#8a8aab",
    "green":    "#00d084",
    "red":      "#ff4757",
    "yellow":   "#ffa502",
    "blue":     "#1e90ff",
    "gray":     "#747d8c",
    "white":    "#ffffff",
}

# State → (dot colour, status message)
_STATE_INFO: dict[str, tuple[str, str]] = {
    "IDLE":           (_C["gray"],   "Idle"),
    "SCANNING":       (_C["green"],  "Watching for available bots..."),
    "CLAIM_FOUND":    (_C["yellow"], "Bot found!"),
    "CLICK_CLAIM":    (_C["yellow"], "Clicking CLAIM cell..."),
    "WAIT_USERNAME":  (_C["yellow"], "Waiting for username confirmation..."),
    "CLAIM_SUCCESS":  (_C["green"],  "Successfully claimed!"),
    "CLICK_SELECT":   (_C["blue"],   "Clicking Select button..."),
    "CLICK_CONNECT":  (_C["blue"],   "Clicking Connect button..."),
    "CONNECTED":      (_C["green"],  "Connected! stopped scanning."),
    "STOPPED":        (_C["gray"],   "Stopped — press F8 to restart"),
    "ERROR":          (_C["red"],    "Error — recovering..."),
    "PAUSED":         (_C["yellow"], "Paused — press F10 to resume"),
}


class StatusWindow:
    """
    A persistent, floating 'always-on-top' status overlay.
    Runs on the main thread and polls a ui_queue for events.
    """

    WINDOW_WIDTH = 270
    WINDOW_HEIGHT = 150

    def __init__(self, cfg) -> None:
        self.cfg = cfg
        self._root: Optional[tk.Tk] = None
        self._running = False

        # State fields
        self._state: str = "IDLE"
        self._automation_on: bool = False
        self._paused: bool = False
        self._fps: float = 0.0
        self._ocr_text: str = ""
        self._last_event: str = ""

        # UI elements
        self._dot: Optional[tk.Label] = None
        self._auto_label: Optional[tk.Label] = None
        self._state_label: Optional[tk.Label] = None
        self._msg_label: Optional[tk.Label] = None
        self._fps_label: Optional[tk.Label] = None
        self._ocr_label: Optional[tk.Label] = None

        # Drag variables
        self._drag_x = 0
        self._drag_y = 0

        # Initial position from config
        self._x = self.cfg.get("status_window_x", 100)
        self._y = self.cfg.get("status_window_y", 100)
        
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public thread-safe API
    # ------------------------------------------------------------------

    def update(
        self,
        state: Optional[str] = None,
        automation_on: Optional[bool] = None,
        paused: Optional[bool] = None,
        fps: Optional[float] = None,
        ocr_text: Optional[str] = None,
        last_event: Optional[str] = None,
    ) -> None:
        with self._lock:
            if state is not None:
                self._state = state
            if automation_on is not None:
                self._automation_on = automation_on
            if paused is not None:
                self._paused = paused
            if fps is not None:
                self._fps = fps
            if ocr_text is not None:
                self._ocr_text = ocr_text
            if last_event is not None:
                self._last_event = last_event

    def stop(self) -> None:
        self._running = False
        if self._root:
            try:
                self._root.after(0, self._root.quit)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Main Thread Run
    # ------------------------------------------------------------------

    def build_and_run(self, ui_queue: queue.Queue, process_queue_callback: Callable) -> None:
        self._running = True
        root = tk.Tk()
        self._root = root

        # Clamp position to active screen bounds to prevent rendering off-screen
        try:
            screen_w = root.winfo_screenwidth()
            screen_h = root.winfo_screenheight()
            if self._x < 0 or self._x + self.WINDOW_WIDTH > screen_w:
                self._x = 100
            if self._y < 0 or self._y + self.WINDOW_HEIGHT > screen_h:
                self._y = 100
        except Exception:
            pass

        # Window styling
        root.title("Teleops Status HUD")
        root.geometry(
            f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}+{self._x}+{self._y}"
        )
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.95)
        root.overrideredirect(True)
        root.configure(bg=_C["bg"])

        self._build_ui(root)
        self._bind_drag(root)
        self._schedule_refresh()

        def _queue_loop():
            if not self._running:
                return
            process_queue_callback(ui_queue)
            root.after(200, _queue_loop)
            
        root.after(200, _queue_loop)

        try:
            root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self._running = False
            try:
                x = root.winfo_x()
                y = root.winfo_y()
                self.cfg.set("status_window_x", x)
                self.cfg.set("status_window_y", y)
                self.cfg.save()
            except Exception:
                pass
            try:
                root.destroy()
            except Exception:
                pass
            self._root = None

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self, root: tk.Tk) -> None:
        # ── Header Bar (Drag zone) ─────────────────────────────────────
        header = tk.Frame(root, bg=_C["header"], height=28)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="🤖 Teleops Auto Claim",
            bg=_C["header"], fg=_C["fg"],
            font=("Segoe UI", 9, "bold"),
            padx=10,
        ).pack(side="left", pady=4)

        # ── Body Content ───────────────────────────────────────────────
        body = tk.Frame(root, bg=_C["bg"], padx=10, pady=8)
        body.pack(fill="both", expand=True)

        # Row 1: Auto (Left) & State (Right)
        row1 = tk.Frame(body, bg=_C["bg"])
        row1.pack(fill="x", pady=1)
        
        # Auto
        f_auto = tk.Frame(row1, bg=_C["bg"])
        f_auto.pack(side="left")
        tk.Label(f_auto, text="Auto: ", bg=_C["bg"], fg=_C["fg_dim"], font=("Segoe UI", 9)).pack(side="left")
        self._auto_label = tk.Label(f_auto, text="OFF", bg=_C["bg"], fg=_C["red"], font=("Segoe UI", 9, "bold"))
        self._auto_label.pack(side="left")

        # State
        f_state = tk.Frame(row1, bg=_C["bg"])
        f_state.pack(side="right")
        self._dot = tk.Label(f_state, text="●", bg=_C["bg"], fg=_C["gray"], font=("Segoe UI", 9))
        self._dot.pack(side="left", padx=(0, 3))
        self._state_label = tk.Label(f_state, text="IDLE", bg=_C["bg"], fg=_C["fg"], font=("Segoe UI", 9, "bold"))
        self._state_label.pack(side="left")

        # Row 2: User (Left) & Avoid Sites (Right)
        row2 = tk.Frame(body, bg=_C["bg"])
        row2.pack(fill="x", pady=2)
        
        # User
        f_user = tk.Frame(row2, bg=_C["bg"])
        f_user.pack(side="left")
        username = self.cfg.get("username", "—")
        tk.Label(f_user, text=f"User: {username}", bg=_C["bg"], fg=_C["fg"], font=("Segoe UI", 9)).pack(side="left")

        # Avoid
        f_avoid = tk.Frame(row2, bg=_C["bg"])
        f_avoid.pack(side="right")
        blocklist = self.cfg.get("site_blocklist", [])
        avoid_str = ",".join(blocklist) if blocklist else "None"
        if len(avoid_str) > 12:
            avoid_str = avoid_str[:10] + ".."
        tk.Label(f_avoid, text=f"Né: {avoid_str}", bg=_C["bg"], fg=_C["yellow"], font=("Segoe UI", 9)).pack(side="left")

        # Row 3: Status Message (wrapped)
        row3 = tk.Frame(body, bg=_C["bg"])
        row3.pack(fill="x", pady=(4, 2))
        self._msg_label = tk.Label(
            row3, text="Idle",
            bg=_C["bg"], fg=_C["fg_dim"],
            font=("Segoe UI", 9, "italic"),
            anchor="w", justify="left"
        )
        self._msg_label.pack(fill="x")

        # Divider
        tk.Frame(body, bg=_C["border"], height=1).pack(fill="x", pady=4)

        # Row 4: OCR (Left) & FPS (Right)
        row4 = tk.Frame(body, bg=_C["bg"])
        row4.pack(fill="x", pady=1)

        f_ocr = tk.Frame(row4, bg=_C["bg"])
        f_ocr.pack(side="left")
        tk.Label(f_ocr, text="OCR: ", bg=_C["bg"], fg=_C["fg_dim"], font=("Courier", 8)).pack(side="left")
        self._ocr_label = tk.Label(f_ocr, text="—", bg=_C["bg"], fg=_C["green"], font=("Courier", 8, "bold"))
        self._ocr_label.pack(side="left")

        f_fps = tk.Frame(row4, bg=_C["bg"])
        f_fps.pack(side="right")
        tk.Label(f_fps, text="FPS: ", bg=_C["bg"], fg=_C["fg_dim"], font=("Courier", 8)).pack(side="left")
        self._fps_label = tk.Label(f_fps, text="0.0", bg=_C["bg"], fg=_C["fg_dim"], font=("Courier", 8))
        self._fps_label.pack(side="left")

        # ── Bottom Hotkey Hint Bar ─────────────────────────────────────
        hint = tk.Frame(root, bg=_C["header"], height=20)
        hint.pack(fill="x", side="bottom")
        hint.pack_propagate(False)
        tk.Label(
            hint,
            text="F8: Start/Stop   F10: Pause   F9: Stop   ESC: Exit",
            bg=_C["header"], fg=_C["fg_dim"],
            font=("Segoe UI", 7),
        ).pack(expand=True)

    def _bind_drag(self, root: tk.Tk) -> None:
        """Make the window draggable by dragging the header or body."""
        root.bind("<ButtonPress-1>", self._on_drag_start)
        root.bind("<B1-Motion>", self._on_drag_motion)

    def _on_drag_start(self, event: tk.Event) -> None:
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag_motion(self, event: tk.Event) -> None:
        if self._root is None:
            return
        dx = event.x - self._drag_x
        dy = event.y - self._drag_y
        x = self._root.winfo_x() + dx
        y = self._root.winfo_y() + dy
        self._root.geometry(f"+{x}+{y}")

    # ------------------------------------------------------------------
    # Refresh loop
    # ------------------------------------------------------------------

    def _schedule_refresh(self) -> None:
        if not self._running or not self._root:
            return
        self._refresh()
        self._root.after(100, self._schedule_refresh)

    def _refresh(self) -> None:
        with self._lock:
            state = self._state
            auto_on = self._automation_on
            paused = self._paused
            fps = self._fps
            ocr = self._ocr_text

        display_state = "PAUSED" if paused and state == "SCANNING" else state
        colour, msg = _STATE_INFO.get(display_state, (_C["gray"], display_state))

        try:
            self._auto_label.config(
                text="ON" if auto_on else "OFF",
                fg=_C["green"] if auto_on else _C["red"],
            )
            self._dot.config(fg=colour)
            self._state_label.config(text=display_state, fg=_C["fg"])
            self._msg_label.config(text=msg, fg=colour)
            
            # Clean and truncate OCR text
            clean_ocr = ocr.strip().replace("\n", " ")
            if len(clean_ocr) > 18:
                clean_ocr = clean_ocr[:16] + ".."
            self._ocr_label.config(text=clean_ocr if clean_ocr else "—")
            self._fps_label.config(text=f"{fps:.1f}")
        except tk.TclError:
            pass  # window being destroyed
