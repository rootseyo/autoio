import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

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
        app._post_ui = Mock()
        key = SimpleNamespace(name="f10")

        app._key_press(key)
        app._key_press(key)

        app._post_ui.assert_called_once_with(app.toggle_autoclick)

        app._key_release(key)
        app._key_press(key)

        self.assertEqual(app._post_ui.call_count, 2)
        app._post_ui.assert_called_with(app.toggle_autoclick)

    def test_keyboard_input_is_recorded_while_app_has_focus(self) -> None:
        app = object.__new__(AutoIOApp)
        app.assigning_hotkey = None
        app.record_hotkey = "f8"
        app.play_hotkey = "f9"
        app.autoclick_hotkey = "f10"
        app._hotkeys_down = set()
        app.recording = True
        app._append_event = Mock()
        key = SimpleNamespace(char="a", vk=0)

        app._key_press(key)
        app._key_release(key)

        serialized = {"kind": "character", "char": "a", "vk": 0}
        self.assertEqual(
            app._append_event.call_args_list,
            [
                call("key_down", key=serialized),
                call("key_up", key=serialized),
            ],
        )

    def test_recorded_io_is_logged_to_activity(self) -> None:
        app = object.__new__(AutoIOApp)
        app.recording_started = 10.0
        app.events = []
        app._event_lock = threading.Lock()
        app._thread_log = Mock()

        with patch("auto_io.app.time.monotonic", return_value=10.25):
            app._append_event("key_down", key={"kind": "special", "name": "enter"})

        self.assertEqual(
            app.events,
            [{"type": "key_down", "time": 0.25, "key": {"kind": "special", "name": "enter"}}],
        )
        app._thread_log.assert_called_once_with("Recorded: Keyboard ENTER down")


if __name__ == "__main__":
    unittest.main()
