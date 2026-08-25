"""Small, isolated operating-system compatibility helpers."""

from __future__ import annotations

import contextlib
import platform

_MACOS_KEYBOARD_CONTEXT_READY = False


def prepare_macos_accessibility_imports() -> None:
    """Work around lazy pyobjc imports used by pynput on newer Python versions."""
    if platform.system() != "Darwin":
        return
    try:
        import HIServices
        from ApplicationServices import AXIsProcessTrusted

        HIServices.AXIsProcessTrusted = AXIsProcessTrusted
    except (ImportError, AttributeError):
        try:
            import ctypes

            application_services = ctypes.CDLL(
                "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
            )
            application_services.AXIsProcessTrusted.restype = ctypes.c_bool
            application_services.AXIsProcessTrusted.argtypes = []
            import HIServices

            HIServices.AXIsProcessTrusted = application_services.AXIsProcessTrusted
        except (ImportError, AttributeError, OSError):
            return


def macos_accessibility_granted(prompt: bool = False) -> bool | None:
    if platform.system() != "Darwin":
        return None
    try:
        from ApplicationServices import AXIsProcessTrusted, AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt

        if prompt:
            return bool(AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True}))
        return bool(AXIsProcessTrusted())
    except (ImportError, AttributeError):
        return None


def prepare_macos_keyboard_listener() -> None:
    """Cache the keyboard layout on the main thread for pynput's listener.

    macOS 26 requires Text Services Manager layout calls to run on the main
    dispatch queue. Pynput normally performs this lookup inside its listener
    thread, which causes a native SIGTRAP in bundled GUI applications.
    """
    global _MACOS_KEYBOARD_CONTEXT_READY
    if platform.system() != "Darwin" or _MACOS_KEYBOARD_CONTEXT_READY:
        return

    try:
        from pynput._util.darwin import keycode_context
        from pynput.keyboard import _darwin as keyboard_backend

        with keycode_context() as context:
            cached_context = context

        @contextlib.contextmanager
        def cached_keycode_context():
            yield cached_context

        keyboard_backend.keycode_context = cached_keycode_context
        _MACOS_KEYBOARD_CONTEXT_READY = True
    except (ImportError, AttributeError, OSError, TypeError):
        return
