import unittest
from unittest.mock import Mock, call, patch

from auto_io.playback import PlaybackController


class PlaybackTests(unittest.TestCase):
    @patch("auto_io.playback.keyboard.Controller")
    @patch("auto_io.playback.mouse.Controller")
    def test_zero_repeat_is_normalized_to_unlimited(self, _mouse: object, _keyboard: object) -> None:
        controller = PlaybackController()

        with patch("auto_io.playback.threading.Thread") as thread:
            controller.start([], 0, lambda _message: None, lambda _error, _stopped: None)

        self.assertEqual(thread.call_args.kwargs["args"][1], -1)
        thread.return_value.start.assert_called_once_with()

    @patch("auto_io.playback.keyboard.Controller")
    @patch("auto_io.playback.mouse.Controller")
    def test_repeat_below_minus_one_is_rejected(self, _mouse: object, _keyboard: object) -> None:
        controller = PlaybackController()

        with self.assertRaises(ValueError):
            controller.start([], -2, lambda _message: None, lambda _error, _stopped: None)

    @patch("auto_io.playback.keyboard.Controller")
    @patch("auto_io.playback.mouse.Controller")
    def test_repeat_delay_is_used_only_between_loops(self, _mouse: object, _keyboard: object) -> None:
        controller = PlaybackController()
        controller._stop.wait = Mock(return_value=False)
        event = {"type": "mouse_move", "time": 0.0, "x": 10, "y": 20}
        logs = []

        with patch("auto_io.playback.time.monotonic", return_value=0.0):
            controller._run([event], 2, logs.append, lambda _error, _stopped: None, 250)

        self.assertEqual(controller._stop.wait.call_args_list, [call(0.0), call(0.25), call(0.0)])
        self.assertEqual(
            logs,
            [
                "Loop 1 started",
                "Played: Mouse moved to (10, 20)",
                "Loop 2 started",
                "Played: Mouse moved to (10, 20)",
            ],
        )

    @patch("auto_io.playback.keyboard.Controller")
    @patch("auto_io.playback.mouse.Controller")
    def test_invalid_repeat_delay_is_rejected(self, _mouse: object, _keyboard: object) -> None:
        controller = PlaybackController()

        for delay in (-1, float("nan"), float("inf")):
            with self.subTest(delay=delay), self.assertRaises(ValueError):
                controller.start(
                    [],
                    1,
                    lambda _message: None,
                    lambda _error, _stopped: None,
                    repeat_delay_ms=delay,
                )

    @patch("auto_io.playback.keyboard.Controller")
    @patch("auto_io.playback.mouse.Controller")
    def test_keyboard_press_and_release_are_played_back(self, _mouse: object, keyboard_controller: Mock) -> None:
        controller = PlaybackController()
        key_value = {"kind": "character", "char": "a", "vk": 0}

        controller._execute({"type": "key_down", "key": key_value})
        controller._execute({"type": "key_up", "key": key_value})

        played_key = keyboard_controller.return_value.press.call_args.args[0]
        keyboard_controller.return_value.press.assert_called_once_with(played_key)
        keyboard_controller.return_value.release.assert_called_once_with(played_key)
        self.assertEqual(controller._held_keys, [])


if __name__ == "__main__":
    unittest.main()
