import unittest
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
