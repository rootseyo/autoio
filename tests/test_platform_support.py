import contextlib
import unittest
from unittest.mock import patch

from auto_io import platform_support


class MacOSPlatformSupportTests(unittest.TestCase):
    def tearDown(self) -> None:
        platform_support._MACOS_KEYBOARD_CONTEXT_READY = False

    def test_keyboard_context_is_captured_once_on_calling_thread(self) -> None:
        from pynput.keyboard import _darwin as keyboard_backend

        calls = []
        cached_context = (42, b"keyboard-layout")

        @contextlib.contextmanager
        def native_keycode_context():
            calls.append("native")
            yield cached_context

        platform_support._MACOS_KEYBOARD_CONTEXT_READY = False
        with (
            patch("auto_io.platform_support.platform.system", return_value="Darwin"),
            patch("pynput._util.darwin.keycode_context", native_keycode_context),
            patch.object(keyboard_backend, "keycode_context") as backend_context,
        ):
            platform_support.prepare_macos_keyboard_listener()

            self.assertEqual(calls, ["native"])
            self.assertIsNot(keyboard_backend.keycode_context, backend_context)
            with keyboard_backend.keycode_context() as context:
                self.assertEqual(context, cached_context)
            self.assertEqual(calls, ["native"])

            platform_support.prepare_macos_keyboard_listener()
            self.assertEqual(calls, ["native"])

    def test_keyboard_preparation_is_skipped_off_macos(self) -> None:
        platform_support._MACOS_KEYBOARD_CONTEXT_READY = False

        with (
            patch("auto_io.platform_support.platform.system", return_value="Windows"),
            patch("pynput._util.darwin.keycode_context") as native_context,
        ):
            platform_support.prepare_macos_keyboard_listener()

        native_context.assert_not_called()
        self.assertFalse(platform_support._MACOS_KEYBOARD_CONTEXT_READY)


if __name__ == "__main__":
    unittest.main()
