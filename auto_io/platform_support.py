"""Small, isolated operating-system compatibility helpers."""

from __future__ import annotations

import platform


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
