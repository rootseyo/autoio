"""Cross-platform CustomTkinter application."""

from __future__ import annotations

import math
import queue
import threading
import time
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk

from .events import MacroFormatError, describe_event
from .platform_support import (
    macos_accessibility_granted,
    prepare_macos_accessibility_imports,
    prepare_macos_keyboard_listener,
)
from .storage import MacroStore

prepare_macos_accessibility_imports()
from pynput import keyboard, mouse  # noqa: E402

from .autoclick import AutoClickController  # noqa: E402
from .playback import PlaybackController  # noqa: E402

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")

RECORD_COLOR = "#AD6670"
RECORD_HOVER_COLOR = "#97545E"
PLAY_COLOR = "#56806E"
PLAY_HOVER_COLOR = "#456E5D"
MACRO_COLOR = "#667EAA"
MACRO_HOVER_COLOR = "#536B97"
AUTOCLICK_COLOR = "#806CA3"
AUTOCLICK_HOVER_COLOR = "#6D598F"


class AutoIOApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        prepare_macos_keyboard_listener()
        self.title("AutoIO")
        self.geometry("920x780")
        self.minsize(820, 680)

        self.store = MacroStore()
        self.playback = PlaybackController()
        self.autoclick = AutoClickController()
        self.events: list[dict[str, Any]] = []
        self.recording = False
        self.recording_started = 0.0
        self.record_hotkey = "f8"
        self.play_hotkey = "f9"
        self.autoclick_hotkey = "f10"
        self.assigning_hotkey: str | None = None
        self._autoclick_pending = False
        self._autoclick_after_id: str | None = None
        self._capture_after_id: str | None = None
        self._hotkeys_down: set[str] = set()
        self._event_lock = threading.Lock()
        self._ui_queue: queue.Queue[tuple[Callable[..., None], tuple[Any, ...]]] = queue.Queue()
        self._window_bounds = (0, 0, 0, 0)

        self._build_ui()
        self._start_listeners()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Configure>", self._cache_window_bounds)
        self.after(10, self._drain_ui_queue)
        self.after(400, self._check_macos_permissions)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=24, pady=(20, 8))
        ctk.CTkLabel(header, text="AutoIO", font=ctk.CTkFont(size=26, weight="bold")).pack(side="left")
        self.status = ctk.CTkLabel(header, text="● READY", text_color=("#667085", "#98A2B3"))
        self.status.pack(side="right")

        left = ctk.CTkFrame(self)
        left.grid(row=1, column=0, sticky="nsew", padx=(24, 8), pady=(8, 24))
        left.grid_columnconfigure((0, 1), weight=1)
        left.grid_rowconfigure(3, weight=1)

        self._build_record_ui(left)
        self._build_autoclick_ui(left)

        ctk.CTkLabel(left, text="Activity", font=ctk.CTkFont(weight="bold")).grid(
            row=2, column=0, columnspan=2, sticky="w", padx=18, pady=(8, 4)
        )
        self.log_box = ctk.CTkTextbox(left, state="disabled")
        self.log_box.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=18, pady=(0, 18))

        right = ctk.CTkFrame(self)
        right.grid(row=1, column=1, sticky="nsew", padx=(8, 24), pady=(8, 24))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(right, text="Saved macros", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=16, pady=(16, 8)
        )
        self.macro_list = ctk.CTkScrollableFrame(right, fg_color="transparent")
        self.macro_list.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self._refresh_macros()

    def _build_record_ui(self, parent: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(
            parent,
            border_width=1,
            border_color=("#D0D5DD", "#3F4652"),
        )
        card.grid(row=0, column=0, columnspan=2, sticky="ew", padx=18, pady=(18, 6))
        card.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(card, text="Record & playback", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=12, pady=(10, 4)
        )
        self.record_button = ctk.CTkButton(
            card,
            text="Record",
            height=46,
            fg_color=RECORD_COLOR,
            hover_color=RECORD_HOVER_COLOR,
            command=self.toggle_recording,
        )
        self.record_button.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(12, 4), pady=(4, 8))
        self.play_button = ctk.CTkButton(
            card,
            text="Play",
            height=46,
            fg_color=PLAY_COLOR,
            hover_color=PLAY_HOVER_COLOR,
            command=self.toggle_playback,
        )
        self.play_button.grid(row=1, column=2, columnspan=2, sticky="ew", padx=(4, 12), pady=(4, 8))

        ctk.CTkButton(
            card,
            text="Save macro",
            fg_color=MACRO_COLOR,
            hover_color=MACRO_HOVER_COLOR,
            command=self.save_current,
        ).grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=(12, 4), pady=4
        )
        ctk.CTkButton(
            card,
            text="Import JSON",
            fg_color=MACRO_COLOR,
            hover_color=MACRO_HOVER_COLOR,
            command=self.import_macro,
        ).grid(
            row=2, column=2, columnspan=2, sticky="ew", padx=(4, 12), pady=4
        )

        ctk.CTkLabel(card, text="Repeat").grid(row=3, column=0, sticky="e", padx=(12, 4), pady=(8, 4))
        self.repeat_entry = ctk.CTkEntry(card, width=70, justify="center")
        self.repeat_entry.insert(0, "1")
        self.repeat_entry.grid(row=3, column=1, sticky="ew", padx=(0, 8), pady=(8, 4))
        ctk.CTkLabel(
            card,
            text="0/-1 = unlimited",
            text_color=("#667085", "#98A2B3"),
            font=ctk.CTkFont(size=11),
        ).grid(row=3, column=2, columnspan=2, sticky="w", padx=(4, 12), pady=(8, 4))

        ctk.CTkLabel(card, text="Repeat delay (ms)").grid(
            row=4, column=0, sticky="e", padx=(12, 4), pady=4
        )
        self.repeat_delay_entry = ctk.CTkEntry(card, width=70, justify="center")
        self.repeat_delay_entry.insert(0, "0")
        self.repeat_delay_entry.grid(row=4, column=1, sticky="ew", padx=(0, 8), pady=4)
        ctk.CTkLabel(
            card,
            text="between loops",
            text_color=("#667085", "#98A2B3"),
            font=ctk.CTkFont(size=11),
        ).grid(row=4, column=2, columnspan=2, sticky="w", padx=(4, 12), pady=4)

        self.record_hotkey_button = ctk.CTkButton(
            card,
            width=105,
            text="Record: F8",
            fg_color=RECORD_COLOR,
            hover_color=RECORD_HOVER_COLOR,
            command=lambda: self._assign_hotkey("record"),
        )
        self.record_hotkey_button.grid(
            row=5, column=0, columnspan=2, sticky="ew", padx=(12, 4), pady=(4, 10)
        )
        self.play_hotkey_button = ctk.CTkButton(
            card,
            width=105,
            text="Play: F9",
            fg_color=PLAY_COLOR,
            hover_color=PLAY_HOVER_COLOR,
            command=lambda: self._assign_hotkey("play"),
        )
        self.play_hotkey_button.grid(
            row=5, column=2, columnspan=2, sticky="ew", padx=(4, 12), pady=(4, 10)
        )

    def _build_autoclick_ui(self, parent: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(
            parent,
            border_width=1,
            border_color=("#D0D5DD", "#3F4652"),
        )
        card.grid(row=1, column=0, columnspan=2, sticky="ew", padx=18, pady=6)
        card.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(card, text="Auto click", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 4)
        )
        self.autoclick_mode = ctk.CTkSegmentedButton(
            card,
            values=["Fixed position", "Free click"],
            selected_color=AUTOCLICK_COLOR,
            selected_hover_color=AUTOCLICK_HOVER_COLOR,
            command=self._autoclick_mode_changed,
        )
        self.autoclick_mode.set("Free click")
        self.autoclick_mode.grid(row=0, column=1, columnspan=3, sticky="ew", padx=12, pady=(10, 4))

        ctk.CTkLabel(card, text="Clicks").grid(row=1, column=0, sticky="e", padx=(10, 4), pady=4)
        self.autoclick_repeat_entry = ctk.CTkEntry(card, width=70, justify="center")
        self.autoclick_repeat_entry.insert(0, "10")
        self.autoclick_repeat_entry.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=4)
        ctk.CTkLabel(card, text="Interval (ms)").grid(row=1, column=2, sticky="e", padx=(10, 4), pady=4)
        self.autoclick_interval_entry = ctk.CTkEntry(card, width=70, justify="center")
        self.autoclick_interval_entry.insert(0, "100")
        self.autoclick_interval_entry.grid(row=1, column=3, sticky="ew", padx=(0, 12), pady=4)

        ctk.CTkLabel(card, text="Position").grid(row=2, column=0, sticky="e", padx=(10, 4), pady=4)
        position = ctk.CTkFrame(card, fg_color="transparent")
        position.grid(row=2, column=1, columnspan=3, sticky="ew", padx=(0, 12), pady=4)
        self.autoclick_x_entry = ctk.CTkEntry(position, width=70, placeholder_text="X", justify="center")
        self.autoclick_x_entry.pack(side="left", padx=(0, 4))
        self.autoclick_y_entry = ctk.CTkEntry(position, width=70, placeholder_text="Y", justify="center")
        self.autoclick_y_entry.pack(side="left", padx=4)
        self.capture_position_button = ctk.CTkButton(
            position,
            text="Capture in 3s",
            fg_color=AUTOCLICK_COLOR,
            hover_color=AUTOCLICK_HOVER_COLOR,
            command=self._capture_position,
        )
        self.capture_position_button.pack(side="left", fill="x", expand=True, padx=(4, 0))

        ctk.CTkLabel(
            card,
            text="Enter 0 or -1 for unlimited clicks",
            text_color=("#667085", "#98A2B3"),
            font=ctk.CTkFont(size=12),
        ).grid(row=3, column=0, columnspan=4, pady=(2, 4))

        self.autoclick_button = ctk.CTkButton(
            card,
            text="Start auto click",
            fg_color=AUTOCLICK_COLOR,
            hover_color=AUTOCLICK_HOVER_COLOR,
            command=self.toggle_autoclick,
        )
        self.autoclick_button.grid(row=4, column=0, columnspan=2, sticky="ew", padx=(12, 4), pady=(4, 10))
        self.autoclick_hotkey_button = ctk.CTkButton(
            card,
            text="Start/Stop: F10",
            width=105,
            fg_color=AUTOCLICK_COLOR,
            hover_color=AUTOCLICK_HOVER_COLOR,
            command=lambda: self._assign_hotkey("autoclick"),
        )
        self.autoclick_hotkey_button.grid(
            row=4, column=2, columnspan=2, sticky="ew", padx=(4, 12), pady=(4, 10)
        )
        self._autoclick_mode_changed("Free click")

    def _start_listeners(self) -> None:
        self.keyboard_listener = keyboard.Listener(on_press=self._key_press, on_release=self._key_release)
        self.mouse_listener = mouse.Listener(
            on_move=self._mouse_move,
            on_click=self._mouse_click,
            on_scroll=self._mouse_scroll,
        )
        self.keyboard_listener.start()
        self.mouse_listener.start()

    @staticmethod
    def _key_name(key: Any) -> str:
        name = getattr(key, "name", None)
        if name:
            return str(name).lower()
        char = getattr(key, "char", None)
        return str(char).lower() if char else str(key).lower()

    @staticmethod
    def _serialize_key(key: Any) -> dict[str, Any]:
        if isinstance(key, keyboard.Key):
            return {"kind": "special", "name": key.name}
        return {"kind": "character", "char": getattr(key, "char", None), "vk": getattr(key, "vk", None)}

    def _key_press(self, key: Any) -> None:
        name = self._key_name(key)
        if self.assigning_hotkey:
            self._post_ui(self._finish_hotkey_assignment, name)
            return
        hotkeys = {self.record_hotkey, self.play_hotkey, self.autoclick_hotkey}
        if name in hotkeys:
            if name not in self._hotkeys_down:
                self._hotkeys_down.add(name)
                if name == self.record_hotkey and not self.playback.active and not self.autoclick.active:
                    self._post_ui(self.toggle_recording)
                elif name == self.play_hotkey:
                    self._post_ui(self.toggle_playback)
                elif name == self.autoclick_hotkey:
                    self._post_ui(self.toggle_autoclick)
            return
        if self.recording:
            self._append_event("key_down", key=self._serialize_key(key))

    def _key_release(self, key: Any) -> None:
        name = self._key_name(key)
        if name in {self.record_hotkey, self.play_hotkey, self.autoclick_hotkey}:
            self._hotkeys_down.discard(name)
            return
        if self.recording and not self.assigning_hotkey:
            self._append_event("key_up", key=self._serialize_key(key))

    def _mouse_move(self, x: int, y: int) -> None:
        if self.recording:
            self._append_event("mouse_move", x=int(x), y=int(y))

    def _mouse_click(self, x: int, y: int, button: Any, pressed: bool) -> None:
        if self.recording and not self._inside_app(x, y):
            self._append_event("mouse_click", x=int(x), y=int(y), button=button.name, pressed=bool(pressed))

    def _mouse_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        if self.recording and not self._inside_app(x, y):
            self._append_event("mouse_scroll", x=int(x), y=int(y), dx=int(dx), dy=int(dy))

    def _inside_app(self, x: int, y: int) -> bool:
        left, top, right, bottom = self._window_bounds
        return left <= x < right and top <= y < bottom

    def _cache_window_bounds(self, _event: Any = None) -> None:
        left = self.winfo_rootx()
        top = self.winfo_rooty()
        self._window_bounds = (left, top, left + self.winfo_width(), top + self.winfo_height())

    def _append_event(self, event_type: str, **values: Any) -> None:
        with self._event_lock:
            event = {"type": event_type, "time": time.monotonic() - self.recording_started, **values}
            self.events.append(event)
            self._thread_log(f"Recorded: {describe_event(event)}")

    def toggle_recording(self) -> None:
        if self.playback.active or self.autoclick.active or self._autoclick_pending:
            return
        self.recording = not self.recording
        if self.recording:
            with self._event_lock:
                self.events = []
                self.recording_started = time.monotonic()
            self.record_button.configure(text="Stop recording")
            self.play_button.configure(state="disabled")
            self.autoclick_button.configure(state="disabled")
            self._set_status("● RECORDING", RECORD_COLOR)
            self._log("Recording started")
        else:
            self.record_button.configure(text="Record")
            self.play_button.configure(state="normal")
            self.autoclick_button.configure(state="normal")
            self._set_status("● READY", ("#667085", "#98A2B3"))
            self._log(f"Recording stopped ({len(self.events)} events)")

    def toggle_playback(self) -> None:
        if self.playback.active:
            self.playback.stop()
            return
        if self.recording or self.autoclick.active or self._autoclick_pending:
            return
        if not self.events:
            messagebox.showwarning("Nothing to play", "Record or load a macro first.")
            return
        try:
            repeat = int(self.repeat_entry.get().strip() or "1")
            repeat_delay_ms = float(self.repeat_delay_entry.get().strip() or "0")
            if repeat < -1:
                raise ValueError
            if not math.isfinite(repeat_delay_ms) or repeat_delay_ms < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Invalid repeat settings",
                "Repeat must be a positive integer, 0, or -1. Repeat delay must be 0 or more milliseconds.",
            )
            return
        repeat = -1 if repeat == 0 else repeat

        self.record_button.configure(state="disabled")
        self.autoclick_button.configure(state="disabled")
        self.play_button.configure(text="Stop")
        self._set_status("● PLAYING", PLAY_COLOR)
        with self._event_lock:
            events = self.events.copy()
        self.playback.start(
            events,
            repeat,
            self._thread_log,
            self._playback_finished,
            repeat_delay_ms=repeat_delay_ms,
        )

    def _playback_finished(self, error: str | None, stopped: bool) -> None:
        self._post_ui(self._finish_playback_ui, error, stopped)

    def _finish_playback_ui(self, error: str | None, stopped: bool) -> None:
        self.record_button.configure(state="normal")
        self.autoclick_button.configure(state="normal")
        self.play_button.configure(text="Play")
        self._set_status("● READY", ("#667085", "#98A2B3"))
        if error:
            self._log(f"Playback failed: {error}")
            messagebox.showerror("Playback failed", error)
        else:
            self._log("Playback stopped" if stopped else "Playback finished")

    def _autoclick_mode_changed(self, mode: str) -> None:
        state = "normal" if mode == "Fixed position" else "disabled"
        self.autoclick_x_entry.configure(state=state)
        self.autoclick_y_entry.configure(state=state)
        self.capture_position_button.configure(state=state)

    def _capture_position(self) -> None:
        if self._capture_after_id or self.autoclick.active or self._autoclick_pending:
            return
        self.capture_position_button.configure(text="Move cursor…", state="disabled")
        self._log("Cursor position will be captured in 3 seconds")
        self._capture_after_id = self.after(3000, self._complete_position_capture)

    def _complete_position_capture(self) -> None:
        self._capture_after_id = None
        x, y = self.autoclick.mouse.position
        for entry, value in ((self.autoclick_x_entry, x), (self.autoclick_y_entry, y)):
            entry.configure(state="normal")
            entry.delete(0, "end")
            entry.insert(0, str(int(value)))
        self.capture_position_button.configure(text="Capture in 3s", state="normal")
        self._autoclick_mode_changed(self.autoclick_mode.get())
        self._log(f"Saved auto-click position: {int(x)}, {int(y)}")

    def toggle_autoclick(self) -> None:
        if self.autoclick.active:
            self.autoclick.stop()
            return
        if self._autoclick_pending:
            self._cancel_autoclick_countdown()
            return
        if self.recording or self.playback.active:
            return

        options = self._read_autoclick_options()
        if options is None:
            return
        repeat, interval_ms = options
        if self.autoclick_mode.get() == "Fixed position":
            try:
                position = (int(self.autoclick_x_entry.get()), int(self.autoclick_y_entry.get()))
            except ValueError:
                messagebox.showerror("Invalid position", "Enter integer X and Y coordinates or capture a position.")
                return
            self._start_autoclick(position, repeat, interval_ms)
            return

        self._autoclick_pending = True
        self.record_button.configure(state="disabled")
        self.play_button.configure(state="disabled")
        self.autoclick_button.configure(text="Cancel countdown")
        self._set_status("● AUTO CLICK IN 3s", "#F79009")
        self._log("Free click starts in 3 seconds; move the cursor outside AutoIO")
        self._autoclick_after_id = self.after(
            3000,
            self._start_free_autoclick,
            repeat,
            interval_ms,
        )

    def _read_autoclick_options(self) -> tuple[int, float] | None:
        try:
            repeat = int(self.autoclick_repeat_entry.get().strip())
            interval_ms = float(self.autoclick_interval_entry.get().strip())
            if repeat < -1:
                raise ValueError
            if not self.autoclick.MIN_INTERVAL_MS <= interval_ms <= self.autoclick.MAX_INTERVAL_MS:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Invalid auto-click settings",
                "Clicks must be a positive integer, 0, or -1. Interval must be between 1 and 60000 ms.",
            )
            return None
        return (-1 if repeat == 0 else repeat), interval_ms

    def _start_free_autoclick(self, repeat: int, interval_ms: float) -> None:
        self._autoclick_pending = False
        self._autoclick_after_id = None
        self._start_autoclick(None, repeat, interval_ms)

    def _start_autoclick(
        self,
        position: tuple[int, int] | None,
        repeat: int,
        interval_ms: float,
    ) -> None:
        if position is not None and self._inside_app(*position):
            self._restore_autoclick_ui()
            messagebox.showwarning("Unsafe position", "Move the cursor outside the AutoIO window and try again.")
            return
        self.record_button.configure(state="disabled")
        self.play_button.configure(state="disabled")
        self.autoclick_button.configure(text="Stop auto click")
        self._set_status("● AUTO CLICKING", AUTOCLICK_COLOR)
        location = f"at {position[0]}, {position[1]}" if position is not None else "at the current cursor"
        self._log(
            f"Auto click started {location} "
            f"({repeat if repeat != -1 else 'infinite'} clicks, {interval_ms:g} ms interval)"
        )
        self.autoclick.start(position, repeat, interval_ms, self._autoclick_finished, self._thread_log)

    def _cancel_autoclick_countdown(self) -> None:
        if self._autoclick_after_id:
            self.after_cancel(self._autoclick_after_id)
        self._autoclick_after_id = None
        self._autoclick_pending = False
        self._restore_autoclick_ui()
        self._log("Auto-click countdown cancelled")

    def _autoclick_finished(self, error: str | None, stopped: bool, completed: int) -> None:
        self._post_ui(self._finish_autoclick_ui, error, stopped, completed)

    def _finish_autoclick_ui(self, error: str | None, stopped: bool, completed: int) -> None:
        self._restore_autoclick_ui()
        if error:
            self._log(f"Auto click failed after {completed} clicks: {error}")
            messagebox.showerror("Auto click failed", error)
        else:
            action = "stopped" if stopped else "finished"
            self._log(f"Auto click {action} ({completed} clicks)")

    def _restore_autoclick_ui(self) -> None:
        self.record_button.configure(state="normal")
        self.play_button.configure(state="normal")
        self.autoclick_button.configure(text="Start auto click", state="normal")
        self._set_status("● READY", ("#667085", "#98A2B3"))

    def _assign_hotkey(self, target: str) -> None:
        self.assigning_hotkey = target
        buttons = {
            "record": self.record_hotkey_button,
            "play": self.play_hotkey_button,
            "autoclick": self.autoclick_hotkey_button,
        }
        button = buttons[target]
        button.configure(text="Press a key…")

    def _finish_hotkey_assignment(self, name: str) -> None:
        target = self.assigning_hotkey
        self.assigning_hotkey = None
        attributes = {
            "record": "record_hotkey",
            "play": "play_hotkey",
            "autoclick": "autoclick_hotkey",
        }
        if target in attributes:
            other_hotkeys = {
                getattr(self, attribute)
                for other_target, attribute in attributes.items()
                if other_target != target
            }
            if name in other_hotkeys:
                messagebox.showerror("Duplicate hotkey", "Record, play, and auto-click hotkeys must be different.")
            else:
                setattr(self, attributes[target], name)
        self.record_hotkey_button.configure(text=f"Record: {self.record_hotkey.upper()}")
        self.play_hotkey_button.configure(text=f"Play: {self.play_hotkey.upper()}")
        self.autoclick_hotkey_button.configure(text=f"Start/Stop: {self.autoclick_hotkey.upper()}")

    def save_current(self) -> None:
        if not self.events:
            messagebox.showwarning("Nothing to save", "Record or load a macro first.")
            return
        dialog = ctk.CTkInputDialog(title="Save macro", text="Macro name")
        name = dialog.get_input()
        if not name:
            return
        try:
            path = self.store.path_for(name)
            if path.exists() and not messagebox.askyesno("Replace macro", f"Replace '{path.stem}'?"):
                return
            with self._event_lock:
                events = self.events.copy()
            self.store.save(name, events)
            self._log(f"Saved {path.name}")
            self._refresh_macros()
        except (OSError, ValueError, MacroFormatError) as exc:
            messagebox.showerror("Save failed", str(exc))

    def import_macro(self) -> None:
        selected = filedialog.askopenfilename(title="Import macro", filetypes=[("JSON macro", "*.json")])
        if not selected:
            return
        try:
            source = Path(selected)
            destination = self.store.path_for(source.stem)
            if destination.exists() and not messagebox.askyesno("Replace macro", f"Replace '{destination.stem}'?"):
                return
            destination = self.store.import_file(source)
            with self._event_lock:
                self.events = self.store.load(destination)
            self._log(f"Imported {destination.name} ({len(self.events)} events)")
            self._refresh_macros()
        except (OSError, ValueError, MacroFormatError) as exc:
            messagebox.showerror("Import failed", str(exc))

    def _load_saved(self, path: Path, play: bool = False) -> None:
        if self.recording or self.playback.active or self.autoclick.active or self._autoclick_pending:
            return
        try:
            with self._event_lock:
                self.events = self.store.load(path)
            self._log(f"Loaded {path.name} ({len(self.events)} events)")
            if play:
                self.toggle_playback()
        except (OSError, MacroFormatError) as exc:
            messagebox.showerror("Load failed", str(exc))

    def _delete_saved(self, path: Path) -> None:
        if not messagebox.askyesno("Delete macro", f"Delete '{path.stem}'?"):
            return
        try:
            self.store.delete(path)
            self._log(f"Deleted {path.name}")
            self._refresh_macros()
        except (OSError, ValueError) as exc:
            messagebox.showerror("Delete failed", str(exc))

    def _refresh_macros(self) -> None:
        for widget in self.macro_list.winfo_children():
            widget.destroy()
        paths = self.store.list()
        if not paths:
            ctk.CTkLabel(self.macro_list, text="No saved macros", text_color="gray").pack(pady=24)
            return
        for path in paths:
            row = ctk.CTkFrame(self.macro_list)
            row.pack(fill="x", pady=4)
            ctk.CTkButton(
                row,
                text=path.stem,
                anchor="w",
                fg_color="transparent",
                command=lambda item=path: self._load_saved(item),
            ).pack(side="left", fill="x", expand=True, padx=4, pady=4)
            ctk.CTkButton(
                row,
                text="▶",
                width=34,
                fg_color=PLAY_COLOR,
                hover_color=PLAY_HOVER_COLOR,
                command=lambda item=path: self._load_saved(item, True),
            ).pack(side="left", padx=2)
            ctk.CTkButton(
                row,
                text="×",
                width=34,
                fg_color=RECORD_COLOR,
                hover_color=RECORD_HOVER_COLOR,
                command=lambda item=path: self._delete_saved(item),
            ).pack(side="left", padx=(2, 4))

    def _thread_log(self, message: str) -> None:
        self._post_ui(self._log, message)

    def _post_ui(self, callback: Callable[..., None], *args: Any) -> None:
        self._ui_queue.put((callback, args))

    def _drain_ui_queue(self) -> None:
        pending_logs: list[str] = []
        for _ in range(500):
            try:
                callback, args = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            if callback == self._log and len(args) == 1:
                pending_logs.append(str(args[0]))
                continue
            self._write_logs(pending_logs)
            pending_logs.clear()
            callback(*args)
        self._write_logs(pending_logs)
        self.after(10, self._drain_ui_queue)

    def _log(self, message: str) -> None:
        self._write_logs([message])

    def _write_logs(self, messages: list[str]) -> None:
        if not messages:
            return
        timestamp = time.strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", "".join(f"[{timestamp}] {message}\n" for message in messages))
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _set_status(self, text: str, color: Any) -> None:
        self.status.configure(text=text, text_color=color)

    def _check_macos_permissions(self) -> None:
        granted = macos_accessibility_granted(prompt=True)
        if granted is False:
            messagebox.showwarning(
                "Accessibility permission required",
                "Allow AutoIO (or your Terminal/Python) in System Settings → Privacy & Security → "
                "Accessibility and Input Monitoring, then restart the app.",
            )

    def _close(self) -> None:
        if self._autoclick_after_id:
            self.after_cancel(self._autoclick_after_id)
        if self._capture_after_id:
            self.after_cancel(self._capture_after_id)
        self.playback.stop()
        self.autoclick.stop()
        self.keyboard_listener.stop()
        self.mouse_listener.stop()
        self.destroy()


def run() -> None:
    AutoIOApp().mainloop()
