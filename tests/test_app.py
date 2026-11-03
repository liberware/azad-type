"""Exercise the GUI model without starting any system keyboard hook."""
from pathlib import Path
import tempfile
import tkinter as tk
import unittest

from azad_type.app import Application
from azad_type.storage import load_settings, save_settings


class DesktopAppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = Application(self.root, profile=Path(self.temp.name))

    def tearDown(self):
        self.app.close()
        self.temp.cleanup()

    def test_smart_conversion_and_undo(self):
        self.app.editor.delete("1.0", "end")
        self.app.editor.insert("1.0", "sghl GitHub https://example.org")
        self.app.editor.edit_reset()
        self.app.smart_convert()
        self.assertEqual(self.app.editor.get("1.0", "end-1c"), "سلام GitHub https://example.org")
        self.app.undo()
        self.assertEqual(self.app.editor.get("1.0", "end-1c"), "sghl GitHub https://example.org")
        self.assertIsNone(self.app.service)

    def test_selection_mapping_leaves_surrounding_text(self):
        self.app.editor.delete("1.0", "end")
        self.app.editor.insert("1.0", "keep sghl safe")
        self.app.editor.tag_add("sel", "1.5", "1.9")
        self.app.manual_convert()
        self.assertEqual(self.app.editor.get("1.0", "end-1c"), "keep سلام safe")

    def test_preferences_persist_but_typed_text_does_not(self):
        self.app.editor.insert("end", "private scratchpad text")
        self.app.digits.set(True)
        self.app._options()
        loaded = load_settings(self.app.config_path)
        self.assertTrue(loaded["persian_digits"])
        self.assertNotIn("private", self.app.config_path.read_text())
        self.assertEqual(list(Path(self.temp.name).iterdir()), [self.app.config_path])

    def test_add_word_updates_engine_and_disk(self):
        self.app.language.set("fa")
        self.app.add_word("آزادانه")
        self.assertTrue(self.app.dictionary.contains("آزادانه", "fa"))
        self.assertTrue((Path(self.temp.name) / "dictionary.json").is_file())


class SettingsTests(unittest.TestCase):
    def test_settings_reject_invalid_app_names(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            save_settings(path, {"allowed_apps": ["../secret.exe"]})
            with self.assertRaises(ValueError):
                load_settings(path)


if __name__ == "__main__":
    unittest.main()
