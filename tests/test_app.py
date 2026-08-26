import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from auto_io.app import AutoIOApp


class AutoIOAppHotkeyTests(unittest.TestCase):
    def test_autoclick_hotkey_toggles_once_per_key_press(self) -> None:
        app = object.__new__(AutoIOApp)
        app.assigning_hotkey = None
        app.record_hotkey = "f8"
        app.play_hotkey = "f9"
        app.autoclick_hotkey = "f10"
        app._hotkeys_down = set()
        app.playback = SimpleNamespace(active=False)
        app.autoclick = SimpleNamespace(active=False)
        app.recording = False
        app._app_has_focus = False
        app._post_ui = Mock()
        key = SimpleNamespace(name="f10")

        app._key_press(key)
        app._key_press(key)

        app._post_ui.assert_called_once_with(app.toggle_autoclick)

        app._key_release(key)
        app._key_press(key)

        self.assertEqual(app._post_ui.call_count, 2)
        app._post_ui.assert_called_with(app.toggle_autoclick)


if __name__ == "__main__":
    unittest.main()
