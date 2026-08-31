"""Interruptible macro playback with input cleanup."""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Callable
from typing import Any

from .events import describe_event
from .platform_support import prepare_macos_accessibility_imports

prepare_macos_accessibility_imports()
from pynput import keyboard, mouse  # noqa: E402

LogCallback = Callable[[str], None]
FinishCallback = Callable[[str | None, bool], None]


class PlaybackController:
    def __init__(self) -> None:
        self.mouse = mouse.Controller()
        self.keyboard = keyboard.Controller()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._held_keys: list[Any] = []
        self._held_buttons: list[Any] = []

    @property
    def active(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(
        self,
        events: list[dict],
        repeat: int,
        log: LogCallback,
        finished: FinishCallback,
        repeat_delay_ms: float = 0.0,
    ) -> None:
        if self.active:
            raise RuntimeError("playback is already running")
        if repeat < -1:
            raise ValueError("repeat must be a positive integer, 0, or -1")
        if not math.isfinite(repeat_delay_ms) or repeat_delay_ms < 0:
            raise ValueError("repeat delay must be a non-negative finite number")
        normalized_repeat = -1 if repeat == 0 else repeat
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(events, normalized_repeat, log, finished, repeat_delay_ms),
            name="macro-playback",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(
        self,
        events: list[dict],
        repeat: int,
        log: LogCallback,
        finished: FinishCallback,
        repeat_delay_ms: float = 0.0,
    ) -> None:
        error: str | None = None
        loop = 0
        try:
            while not self._stop.is_set() and (repeat == -1 or loop < repeat):
                loop += 1
                log(f"Loop {loop} started")
                started = time.monotonic()
                for event in events:
                    delay = max(0.0, event["time"] - (time.monotonic() - started))
                    if self._stop.wait(delay):
                        break
                    self._execute(event)
                    log(f"Played: {describe_event(event)}")
                if self._stop.is_set() or (repeat != -1 and loop >= repeat):
                    break
                if self._stop.wait(repeat_delay_ms / 1000.0):
                    break
        except Exception as exc:  # Hardware/API failures need to reach the GUI.
            error = str(exc)
        finally:
            stopped = self._stop.is_set()
            self._release_inputs()
            finished(error, stopped)

    def _execute(self, event: dict) -> None:
        event_type = event["type"]
        if event_type == "mouse_move":
            self.mouse.position = (event["x"], event["y"])
        elif event_type == "mouse_click":
            button = mouse.Button[event["button"]]
            self.mouse.position = (event["x"], event["y"])
            if event["pressed"]:
                self.mouse.press(button)
                self._held_buttons.append(button)
            else:
                self.mouse.release(button)
                self._discard_one(self._held_buttons, button)
        elif event_type == "mouse_scroll":
            self.mouse.scroll(event["dx"], event["dy"])
        elif event_type in {"key_down", "key_up"}:
            key = self._decode_key(event["key"])
            if event_type == "key_down":
                self.keyboard.press(key)
                self._held_keys.append(key)
            else:
                self.keyboard.release(key)
                self._discard_one(self._held_keys, key)

    @staticmethod
    def _decode_key(value: dict) -> Any:
        if value["kind"] == "special":
            return keyboard.Key[value["name"]]
        return keyboard.KeyCode(char=value.get("char"), vk=value.get("vk"))

    @staticmethod
    def _discard_one(items: list[Any], value: Any) -> None:
        try:
            items.remove(value)
        except ValueError:
            pass

    def _release_inputs(self) -> None:
        for key in reversed(self._held_keys):
            try:
                self.keyboard.release(key)
            except Exception:
                pass
        for button in reversed(self._held_buttons):
            try:
                self.mouse.release(button)
            except Exception:
                pass
        self._held_keys.clear()
        self._held_buttons.clear()
