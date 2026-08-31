import json
import tempfile
import unittest
from pathlib import Path

from auto_io.events import MacroFormatError, describe_event, load_macro, normalize_document, write_macro


class MacroEventTests(unittest.TestCase):
    def test_round_trip_current_schema(self) -> None:
        events = [
            {"type": "mouse_move", "time": 0.0, "x": 10, "y": 20},
            {
                "type": "key_down",
                "time": 0.2,
                "key": {"kind": "character", "char": "a", "vk": None},
            },
            {
                "type": "key_up",
                "time": 0.3,
                "key": {"kind": "character", "char": "a", "vk": None},
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "macro.json"
            write_macro(path, events)
            self.assertEqual(load_macro(path), events)
            document = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(document["schema_version"], 1)

    def test_legacy_bare_list_is_converted(self) -> None:
        legacy = [
            {"type": "m_move", "elapsed": 0, "x": 1, "y": 2},
            {
                "type": "key_down",
                "elapsed": 0.1,
                "key": {"type": "Key", "value": "enter"},
            },
        ]
        self.assertEqual(
            normalize_document(legacy),
            [
                {"type": "mouse_move", "time": 0.0, "x": 1, "y": 2},
                {
                    "type": "key_down",
                    "time": 0.1,
                    "key": {"kind": "special", "name": "enter"},
                },
            ],
        )

    def test_rejects_unknown_event_and_unsorted_time(self) -> None:
        with self.assertRaises(MacroFormatError):
            normalize_document([{"type": "launch_program", "elapsed": 0}])
        with self.assertRaises(MacroFormatError):
            normalize_document(
                [
                    {"type": "mouse_move", "time": 1, "x": 1, "y": 2},
                    {"type": "mouse_move", "time": 0, "x": 1, "y": 2},
                ]
            )

    def test_rejects_non_finite_time(self) -> None:
        with self.assertRaises(MacroFormatError):
            normalize_document([{"type": "mouse_move", "time": float("nan"), "x": 1, "y": 2}])

    def test_describes_every_io_event_type(self) -> None:
        events = [
            ({"type": "mouse_move", "x": 1, "y": 2}, "Mouse moved to (1, 2)"),
            (
                {"type": "mouse_click", "x": 1, "y": 2, "button": "left", "pressed": True},
                "Mouse left button down at (1, 2)",
            ),
            (
                {"type": "mouse_scroll", "x": 1, "y": 2, "dx": 0, "dy": -1},
                "Mouse scrolled dx=0, dy=-1 at (1, 2)",
            ),
            (
                {"type": "key_down", "key": {"kind": "character", "char": "a", "vk": 0}},
                "Keyboard 'a' down",
            ),
            (
                {"type": "key_up", "key": {"kind": "special", "name": "enter"}},
                "Keyboard ENTER up",
            ),
        ]

        for event, expected in events:
            with self.subTest(event_type=event["type"]):
                self.assertEqual(describe_event(event), expected)


if __name__ == "__main__":
    unittest.main()
