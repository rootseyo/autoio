"""Interruptible mouse auto-clicking at a fixed or freely moving cursor."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from .platform_support import prepare_macos_accessibility_imports

prepare_macos_accessibility_imports()
from pynput import mouse  # noqa: E402

FinishCallback = Callable[[str | None, bool, int], None]
LogCallback = Callable[[str], None]


class AutoClickController:
    """Click the left mouse button from a worker thread."""

    MIN_INTERVAL_MS = 1.0
    MAX_INTERVAL_MS = 60_000.0

    def __init__(self, mouse_controller: object | None = None) -> None:
        self.mouse = mouse_controller or mouse.Controller()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def active(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(
        self,
        position: tuple[int, int] | None,
        repeat: int,
        interval_ms: float,
        finished: FinishCallback,
        log: LogCallback | None = None,
    ) -> None:
        if self.active:
            raise RuntimeError("auto click is already running")
        if repeat < -1:
            raise ValueError("repeat must be a positive integer, 0, or -1")
        if not self.MIN_INTERVAL_MS <= interval_ms <= self.MAX_INTERVAL_MS:
            raise ValueError(
                f"click interval must be between {self.MIN_INTERVAL_MS:g} "
                f"and {self.MAX_INTERVAL_MS:g} milliseconds"
            )

        normalized_repeat = -1 if repeat == 0 else repeat
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(position, normalized_repeat, interval_ms, finished, log),
            name="auto-click",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(
        self,
        position: tuple[int, int] | None,
        repeat: int,
        interval_ms: float,
        finished: FinishCallback,
        log: LogCallback | None = None,
    ) -> None:
        error: str | None = None
        completed = 0
        interval = interval_ms / 1000.0
        deadline = time.monotonic()
        try:
            while not self._stop.is_set() and (repeat == -1 or completed < repeat):
                if self._stop.wait(max(0.0, deadline - time.monotonic())):
                    break
                if position is not None:
                    self.mouse.position = position
                self.mouse.click(mouse.Button.left)
                completed += 1
                if log is not None:
                    x, y = self.mouse.position
                    log(f"Auto click {completed}: Mouse left click at ({int(x)}, {int(y)})")
                deadline = max(deadline + interval, time.monotonic())
        except Exception as exc:  # Hardware/API failures need to reach the GUI.
            error = str(exc)
        finally:
            finished(error, self._stop.is_set(), completed)
