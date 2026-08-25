"""Interruptible, rate-limited mouse auto-clicking."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from .platform_support import prepare_macos_accessibility_imports

prepare_macos_accessibility_imports()
from pynput import mouse  # noqa: E402

FinishCallback = Callable[[str | None, bool, int], None]


class AutoClickController:
    """Click the left mouse button at one position from a worker thread."""

    MIN_CPS = 0.1
    MAX_CPS = 100.0

    def __init__(self, mouse_controller: object | None = None) -> None:
        self.mouse = mouse_controller or mouse.Controller()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def active(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(
        self,
        position: tuple[int, int],
        repeat: int,
        clicks_per_second: float,
        finished: FinishCallback,
    ) -> None:
        if self.active:
            raise RuntimeError("auto click is already running")
        if repeat != -1 and repeat < 1:
            raise ValueError("repeat must be a positive integer or -1")
        if not self.MIN_CPS <= clicks_per_second <= self.MAX_CPS:
            raise ValueError(f"click speed must be between {self.MIN_CPS} and {self.MAX_CPS} CPS")

        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(position, repeat, clicks_per_second, finished),
            name="auto-click",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(
        self,
        position: tuple[int, int],
        repeat: int,
        clicks_per_second: float,
        finished: FinishCallback,
    ) -> None:
        error: str | None = None
        completed = 0
        interval = 1.0 / clicks_per_second
        deadline = time.monotonic()
        try:
            while not self._stop.is_set() and (repeat == -1 or completed < repeat):
                if self._stop.wait(max(0.0, deadline - time.monotonic())):
                    break
                self.mouse.position = position
                self.mouse.click(mouse.Button.left)
                completed += 1
                deadline = max(deadline + interval, time.monotonic())
        except Exception as exc:  # Hardware/API failures need to reach the GUI.
            error = str(exc)
        finally:
            finished(error, self._stop.is_set(), completed)
