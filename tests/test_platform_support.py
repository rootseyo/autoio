import contextlib
import sys
import unittest
from types import ModuleType
from unittest.mock import patch

from auto_io import platform_support


class MacOSPlatformSupportTests(unittest.TestCase):
    def tearDown(self) -> None:
        platform_support._MACOS_KEYBOARD_CONTEXT_READY = False

    def test_keyboard_context_is_captured_once_on_calling_thread(self) -> None:
        calls = []
        cached_context = (42, b"keyboard-layout")

        @contextlib.contextmanager
        def native_keycode_context():
            calls.append("native")
            yield cached_context

        pynput_module = ModuleType("pynput")
        pynput_module.__path__ = []
        util_module = ModuleType("pynput._util")
        util_module.__path__ = []
        darwin_util_module = ModuleType("pynput._util.darwin")
        darwin_util_module.keycode_context = native_keycode_context
        keyboard_module = ModuleType("pynput.keyboard")
        keyboard_module.__path__ = []
        keyboard_backend = ModuleType("pynput.keyboard._darwin")
        original_backend_context = object()
        keyboard_backend.keycode_context = original_backend_context
        keyboard_module._darwin = keyboard_backend
        fake_modules = {
            "pynput": pynput_module,
            "pynput._util": util_module,
            "pynput._util.darwin": darwin_util_module,
            "pynput.keyboard": keyboard_module,
            "pynput.keyboard._darwin": keyboard_backend,
        }

        platform_support._MACOS_KEYBOARD_CONTEXT_READY = False
        with (
            patch("auto_io.platform_support.platform.system", return_value="Darwin"),
            patch.dict(sys.modules, fake_modules),
        ):
            platform_support.prepare_macos_keyboard_listener()

            self.assertEqual(calls, ["native"])
            self.assertIsNot(keyboard_backend.keycode_context, original_backend_context)
            with keyboard_backend.keycode_context() as context:
                self.assertEqual(context, cached_context)
            self.assertEqual(calls, ["native"])

            platform_support.prepare_macos_keyboard_listener()
            self.assertEqual(calls, ["native"])

    def test_keyboard_preparation_is_skipped_off_macos(self) -> None:
        platform_support._MACOS_KEYBOARD_CONTEXT_READY = False

        with patch("auto_io.platform_support.platform.system", return_value="Windows"):
            platform_support.prepare_macos_keyboard_listener()

        self.assertFalse(platform_support._MACOS_KEYBOARD_CONTEXT_READY)


if __name__ == "__main__":
    unittest.main()
