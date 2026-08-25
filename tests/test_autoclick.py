import unittest
from unittest.mock import patch

from auto_io.autoclick import AutoClickController


class FakeMouse:
    def __init__(self) -> None:
        self._position = (0, 0)
        self.positions_set = []
        self.clicks = []

    @property
    def position(self) -> tuple[int, int]:
        return self._position

    @position.setter
    def position(self, value: tuple[int, int]) -> None:
        self._position = value
        self.positions_set.append(value)

    def click(self, button: object) -> None:
        self.clicks.append((self.position, button))


class AutoClickTests(unittest.TestCase):
    def test_clicks_requested_number_at_fixed_position(self) -> None:
        mouse = FakeMouse()
        controller = AutoClickController(mouse)
        result = []

        controller._run((120, 340), 3, 1, lambda error, stopped, count: result.append((error, stopped, count)))

        self.assertEqual([position for position, _button in mouse.clicks], [(120, 340)] * 3)
        self.assertEqual(mouse.positions_set, [(120, 340)] * 3)
        self.assertEqual(result, [(None, False, 3)])

    def test_free_click_does_not_overwrite_cursor_position(self) -> None:
        mouse = FakeMouse()
        mouse._position = (42, 84)
        controller = AutoClickController(mouse)
        result = []

        controller._run(None, 3, 1, lambda error, stopped, count: result.append((error, stopped, count)))

        self.assertEqual([position for position, _button in mouse.clicks], [(42, 84)] * 3)
        self.assertEqual(mouse.positions_set, [])
        self.assertEqual(result, [(None, False, 3)])

    def test_validates_repeat_and_interval(self) -> None:
        controller = AutoClickController(FakeMouse())

        def callback(_error: str | None, _stopped: bool, _count: int) -> None:
            pass

        with self.assertRaises(ValueError):
            controller.start((0, 0), -2, 10, callback)
        with self.assertRaises(ValueError):
            controller.start((0, 0), 1, 0, callback)
        with self.assertRaises(ValueError):
            controller.start((0, 0), 1, 60_001, callback)

    def test_zero_repeat_is_normalized_to_unlimited(self) -> None:
        controller = AutoClickController(FakeMouse())

        with patch("auto_io.autoclick.threading.Thread") as thread:
            controller.start((0, 0), 0, 10, lambda _error, _stopped, _count: None)

        self.assertEqual(thread.call_args.kwargs["args"][1], -1)
        thread.return_value.start.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
