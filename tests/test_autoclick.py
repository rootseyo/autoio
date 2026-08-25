import unittest

from auto_io.autoclick import AutoClickController


class FakeMouse:
    def __init__(self) -> None:
        self.position = (0, 0)
        self.clicks = []

    def click(self, button: object) -> None:
        self.clicks.append((self.position, button))


class AutoClickTests(unittest.TestCase):
    def test_clicks_requested_number_at_fixed_position(self) -> None:
        mouse = FakeMouse()
        controller = AutoClickController(mouse)
        result = []

        controller._run((120, 340), 3, 100, lambda error, stopped, count: result.append((error, stopped, count)))

        self.assertEqual([position for position, _button in mouse.clicks], [(120, 340)] * 3)
        self.assertEqual(result, [(None, False, 3)])

    def test_validates_repeat_and_speed(self) -> None:
        controller = AutoClickController(FakeMouse())

        def callback(_error: str | None, _stopped: bool, _count: int) -> None:
            pass

        with self.assertRaises(ValueError):
            controller.start((0, 0), 0, 10, callback)
        with self.assertRaises(ValueError):
            controller.start((0, 0), 1, 0, callback)
        with self.assertRaises(ValueError):
            controller.start((0, 0), 1, 101, callback)


if __name__ == "__main__":
    unittest.main()
