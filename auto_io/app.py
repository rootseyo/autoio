"""Cross-platform CustomTkinter application."""

from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk

from .events import MacroFormatError
from .platform_support import macos_accessibility_granted, prepare_macos_accessibility_imports
from .storage import MacroStore

prepare_macos_accessibility_imports()
from pynput import keyboard, mouse  # noqa: E402

from .playback import PlaybackController  # noqa: E402

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


class AutoIOApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("AutoIO")
        self.geometry("900x680")
        self.minsize(780, 580)

        self.store = MacroStore()
        self.playback = PlaybackController()
        self.events: list[dict[str, Any]] = []
        self.recording = False
        self.recording_started = 0.0
        self.record_hotkey = "f8"
        self.play_hotkey = "f9"
        self.assigning_hotkey: str | None = None
        self._hotkeys_down: set[str] = set()
        self._event_lock = threading.Lock()
        self._ui_queue: queue.Queue[tuple[Callable[..., None], tuple[Any, ...]]] = queue.Queue()
        self._window_bounds = (0, 0, 0, 0)
        self._app_has_focus = True

        self._build_ui()
        self._start_listeners()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Configure>", self._cache_window_bounds)
        self.bind_all("<FocusIn>", self._cache_focus)
        self.bind_all("<FocusOut>", self._cache_focus)
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
        left.grid_rowconfigure(4, weight=1)

        self.record_button = ctk.CTkButton(
            left, text="Record", height=46, fg_color="#D92D20", hover_color="#B42318", command=self.toggle_recording
        )
        self.record_button.grid(row=0, column=0, sticky="ew", padx=(18, 8), pady=(18, 10))
        self.play_button = ctk.CTkButton(left, text="Play", height=46, command=self.toggle_playback)
        self.play_button.grid(row=0, column=1, sticky="ew", padx=(8, 18), pady=(18, 10))

        ctk.CTkButton(left, text="Save macro", command=self.save_current).grid(
            row=1, column=0, sticky="ew", padx=(18, 8), pady=8
        )
        ctk.CTkButton(left, text="Import JSON", command=self.import_macro).grid(
            row=1, column=1, sticky="ew", padx=(8, 18), pady=8
        )

        settings = ctk.CTkFrame(left, fg_color="transparent")
        settings.grid(row=2, column=0, columnspan=2, sticky="ew", padx=18, pady=10)
        ctk.CTkLabel(settings, text="Repeat").pack(side="left")
        self.repeat_entry = ctk.CTkEntry(settings, width=70, justify="center")
        self.repeat_entry.insert(0, "1")
        self.repeat_entry.pack(side="left", padx=(8, 20))
        self.record_hotkey_button = ctk.CTkButton(
            settings, width=105, text="Record: F8", command=lambda: self._assign_hotkey("record")
        )
        self.record_hotkey_button.pack(side="left", padx=4)
        self.play_hotkey_button = ctk.CTkButton(
            settings, width=105, text="Play: F9", command=lambda: self._assign_hotkey("play")
        )
        self.play_hotkey_button.pack(side="left", padx=4)

        ctk.CTkLabel(left, text="Activity", font=ctk.CTkFont(weight="bold")).grid(
            row=3, column=0, columnspan=2, sticky="w", padx=18, pady=(8, 4)
        )
        self.log_box = ctk.CTkTextbox(left, state="disabled")
        self.log_box.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=18, pady=(0, 18))

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
        if name in {self.record_hotkey, self.play_hotkey}:
            if name not in self._hotkeys_down:
                self._hotkeys_down.add(name)
                if name == self.record_hotkey and not self.playback.active:
                    self._post_ui(self.toggle_recording)
                elif name == self.play_hotkey:
                    self._post_ui(self.toggle_playback)
            return
        if self.recording and not self._app_has_focus:
            self._append_event("key_down", key=self._serialize_key(key))

    def _key_release(self, key: Any) -> None:
        name = self._key_name(key)
        if name in {self.record_hotkey, self.play_hotkey}:
            self._hotkeys_down.discard(name)
            return
        if self.recording and not self.assigning_hotkey and not self._app_has_focus:
            self._append_event("key_up", key=self._serialize_key(key))

    def _mouse_move(self, x: int, y: int) -> None:
        if self.recording:
            self._append_event("mouse_move", x=int(x), y=int(y))

    def _mouse_click(self, x: int, y: int, button: Any, pressed: bool) -> None:
        if self.recording and not self._inside_app(x, y):
            self._append_event("mouse_click", x=int(x), y=int(y), button=button.name, pressed=bool(pressed))
            self._thread_log(f"Mouse {button.name} {'down' if pressed else 'up'} at {x}, {y}")

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

    def _cache_focus(self, _event: Any = None) -> None:
        self.after_idle(self._update_focus_cache)

    def _update_focus_cache(self) -> None:
        self._app_has_focus = self.focus_get() is not None

    def _append_event(self, event_type: str, **values: Any) -> None:
        with self._event_lock:
            self.events.append({"type": event_type, "time": time.monotonic() - self.recording_started, **values})

    def toggle_recording(self) -> None:
        if self.playback.active:
            return
        self.recording = not self.recording
        if self.recording:
            with self._event_lock:
                self.events = []
                self.recording_started = time.monotonic()
            self.record_button.configure(text="Stop recording")
            self.play_button.configure(state="disabled")
            self._set_status("● RECORDING", "#D92D20")
            self._log("Recording started")
        else:
            self.record_button.configure(text="Record")
            self.play_button.configure(state="normal")
            self._set_status("● READY", ("#667085", "#98A2B3"))
            self._log(f"Recording stopped ({len(self.events)} events)")

    def toggle_playback(self) -> None:
        if self.playback.active:
            self.playback.stop()
            return
        if self.recording:
            return
        if not self.events:
            messagebox.showwarning("Nothing to play", "Record or load a macro first.")
            return
        try:
            repeat = int(self.repeat_entry.get().strip() or "1")
            if repeat != -1 and repeat < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid repeat", "Enter a positive integer, or -1 for infinite playback.")
            return

        self.record_button.configure(state="disabled")
        self.play_button.configure(text="Stop")
        self._set_status("● PLAYING", "#039855")
        with self._event_lock:
            events = self.events.copy()
        self.playback.start(events, repeat, self._thread_log, self._playback_finished)

    def _playback_finished(self, error: str | None, stopped: bool) -> None:
        self._post_ui(self._finish_playback_ui, error, stopped)

    def _finish_playback_ui(self, error: str | None, stopped: bool) -> None:
        self.record_button.configure(state="normal")
        self.play_button.configure(text="Play")
        self._set_status("● READY", ("#667085", "#98A2B3"))
        if error:
            self._log(f"Playback failed: {error}")
            messagebox.showerror("Playback failed", error)
        else:
            self._log("Playback stopped" if stopped else "Playback finished")

    def _assign_hotkey(self, target: str) -> None:
        self.assigning_hotkey = target
        button = self.record_hotkey_button if target == "record" else self.play_hotkey_button
        button.configure(text="Press a key…")

    def _finish_hotkey_assignment(self, name: str) -> None:
        target = self.assigning_hotkey
        self.assigning_hotkey = None
        if target == "record":
            if name == self.play_hotkey:
                messagebox.showerror("Duplicate hotkey", "Record and play hotkeys must be different.")
            else:
                self.record_hotkey = name
        elif target == "play":
            if name == self.record_hotkey:
                messagebox.showerror("Duplicate hotkey", "Record and play hotkeys must be different.")
            else:
                self.play_hotkey = name
        self.record_hotkey_button.configure(text=f"Record: {self.record_hotkey.upper()}")
        self.play_hotkey_button.configure(text=f"Play: {self.play_hotkey.upper()}")

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
        if self.recording or self.playback.active:
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
                row, text="▶", width=34, command=lambda item=path: self._load_saved(item, True)
            ).pack(side="left", padx=2)
            ctk.CTkButton(
                row,
                text="×",
                width=34,
                fg_color="#D92D20",
                hover_color="#B42318",
                command=lambda item=path: self._delete_saved(item),
            ).pack(side="left", padx=(2, 4))

    def _thread_log(self, message: str) -> None:
        self._post_ui(self._log, message)

    def _post_ui(self, callback: Callable[..., None], *args: Any) -> None:
        self._ui_queue.put((callback, args))

    def _drain_ui_queue(self) -> None:
        try:
            while True:
                callback, args = self._ui_queue.get_nowait()
                callback(*args)
        except queue.Empty:
            pass
        self.after(10, self._drain_ui_queue)

    def _log(self, message: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
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
        self.playback.stop()
        self.keyboard_listener.stop()
        self.mouse_listener.stop()
        self.destroy()


def run() -> None:
    AutoIOApp().mainloop()
