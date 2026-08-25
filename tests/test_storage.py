import tempfile
import unittest
from pathlib import Path

from auto_io.storage import MacroStore, safe_macro_name

EVENTS = [{"type": "mouse_move", "time": 0.0, "x": 10, "y": 20}]


class MacroStoreTests(unittest.TestCase):
    def test_names_are_portable_to_windows(self) -> None:
        self.assertEqual(safe_macro_name("report: daily.json"), "report_ daily")
        for name in ("", "CON", "lpt1", "..."):
            with self.subTest(name=name), self.assertRaises(ValueError):
                safe_macro_name(name)

    def test_save_list_load_and_delete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = MacroStore(Path(directory))
            path = store.save("demo", EVENTS)
            self.assertEqual(store.list(), [path])
            self.assertEqual(store.load(path), EVENTS)
            store.delete(path)
            self.assertEqual(store.list(), [])

    def test_delete_is_limited_to_store(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            store = MacroStore(base / "macros")
            outside = base / "outside.json"
            outside.write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                store.delete(outside)
            self.assertTrue(outside.exists())


if __name__ == "__main__":
    unittest.main()
