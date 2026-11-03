import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from azad_type.dictionary import Dictionary, normalize
from azad_type.engine import Engine, Settings, to_english, to_persian


class EngineTests(unittest.TestCase):
    def test_physical_layout_and_roundtrip_preserve_whitespace(self):
        self.assertEqual(to_persian("sghl ;jhf"), "سلام کتاب")
        self.assertEqual(to_english("  سلام\nکتاب\t"), "  sghl\n;jhf\t")

    def test_automatic_mixed_sentence(self):
        engine = Engine()
        self.assertEqual(engine.convert_text("sghl GitHub API ;jhf"), "سلام GitHub API کتاب")

    def test_known_english_wins_over_valid_persian_mapping(self):
        # 'do' is both ordinary English and the physical keys for Persian یخ.
        decision = Engine().decide("do", previous_persian=True)
        self.assertEqual(decision.output, "do")
        self.assertEqual(decision.reason, "protected-english")

    def test_unknown_words_are_preserved(self):
        decision = Engine().decide("qwerty")
        self.assertFalse(decision.converted)
        self.assertEqual(decision.reason, "no-dictionary-evidence")

    def test_short_word_requires_persian_context(self):
        engine = Engine()
        self.assertEqual(engine.decide("fv").output, "fv")
        self.assertEqual(engine.decide("fv", previous_persian=True).output, "بر")
        self.assertEqual(engine.convert_text("sghl fv"), "سلام بر")
        self.assertEqual(engine.convert_text("sghl\nfv"), "سلام\nfv")
        self.assertEqual(engine.convert_text("sghl hello fv"), "سلام hello fv")

    def test_urls_email_paths_identifiers_and_numbers_preserved(self):
        engine = Engine()
        for token in ("https://sghl.test/a", "a@b.com", "www.sghl.com", "src/sghl", "sghl_api", "sghl2", "foo.bar", "SgHl", "SGHL"):
            with self.subTest(token=token):
                self.assertEqual(engine.decide(token, previous_persian=True).output, token)

    def test_punctuation_fallback_and_letter_punctuation(self):
        engine = Engine(settings=Settings(persian_punctuation=True))
        self.assertEqual(engine.decide("sghl,").output, "سلام،")
        self.assertEqual(engine.decide("(sghl?)").output, "(سلام؟)")
        self.assertEqual(engine.decide(";jhf").output, "کتاب")
        # Internal comma is the physical key for Persian و.
        self.assertEqual(engine.decide("v,c").output, "روز")

    def test_digits_only_converted_in_persian_context(self):
        engine = Engine(settings=Settings(persian_digits=True))
        self.assertEqual(engine.decide("123").output, "123")
        self.assertEqual(engine.decide("123", previous_persian=True).output, "۱۲۳")
        self.assertEqual(engine.convert_text("sghl 123"), "سلام ۱۲۳")

    def test_manual_conversion_is_explicitly_unconditional(self):
        engine = Engine()
        self.assertEqual(engine.manual_convert("GitHub", "fa"), to_persian("GitHub"))
        self.assertEqual(engine.manual_convert("سلام"), "sghl")
        with self.assertRaises(ValueError):
            engine.manual_convert("sghl", "invalid")

    def test_pause_and_normalization(self):
        self.assertEqual(Engine(settings=Settings(auto_convert=False)).decide("sghl").output, "sghl")
        self.assertEqual(normalize("كتاب يکى"), "کتاب یکی")
        self.assertEqual(Engine().decide("كتاب").output, "کتاب")
        self.assertEqual(Engine().decide("GitHubكتاب").output, "GitHubكتاب")

    def test_setting_validation(self):
        for value in (0, 1, 21):
            with self.assertRaises(ValueError):
                Settings(min_word_length=value)


class DictionaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def test_personal_words_persist_and_protect(self):
        path = self.directory / "personal.json"
        dictionary = Dictionary(path)
        dictionary.add("آزادی", "fa")
        dictionary.add("SGHL", "en")
        loaded = Dictionary(path)
        self.assertTrue(loaded.contains("آزادی"))
        self.assertTrue(loaded.contains("Sghl", "en"))
        self.assertEqual(Engine(loaded).decide("sghl").output, "sghl")
        loaded.remove("sghl", "en")
        self.assertEqual(Engine(loaded).decide("sghl").output, "سلام")

    def test_all_export_formats_roundtrip_without_seed_vocabulary(self):
        dictionary = Dictionary()
        dictionary.add("آزادی", "fa")
        dictionary.add("MyTech", "en")
        for suffix in ("json", "csv", "txt"):
            with self.subTest(suffix=suffix):
                path = self.directory / ("export." + suffix)
                dictionary.export_file(path)
                loaded = Dictionary()
                self.assertEqual(loaded.import_file(path), 2)
                self.assertEqual(loaded.personal_words, dictionary.personal_words)
                self.assertEqual(loaded.import_file(path), 0)
                self.assertNotIn("سلام", path.read_text(encoding="utf-8"))

    def test_invalid_import_is_atomic(self):
        path = self.directory / "personal.json"
        dictionary = Dictionary(path)
        dictionary.add("آزادی")
        original = path.read_bytes()
        invalid = self.directory / "invalid.json"
        invalid.write_text(json.dumps({"fa": ["دنیای", "not Persian"], "en": []}), encoding="utf-8")
        with self.assertRaises(ValueError):
            dictionary.import_file(invalid)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(dictionary.personal_words["fa"], ["آزادی"])

    def test_failed_disk_write_does_not_mutate_memory(self):
        dictionary = Dictionary(self.directory / "personal.json")
        with patch("azad_type.dictionary.os.replace", side_effect=OSError("disk unavailable")):
            with self.assertRaises(OSError):
                dictionary.add("MyNewTerm", "en")
        self.assertNotIn("mynewterm", dictionary.protected_words)
        self.assertEqual(list(self.directory.glob("*.tmp")), [])

    def test_reject_invalid_entries_and_csv_formula_prefix(self):
        dictionary = Dictionary()
        for word, language in (("two words", "en"), ("=HYPERLINK", "en"), ("+cmd", "en"), ("\tcmd", "xx"), ("API", "fa"), (123, "en")):
            with self.subTest(word=word, language=language):
                with self.assertRaises(ValueError):
                    dictionary.add(word, language)

    def test_plain_txt_infers_alphabet_and_csv_header_is_checked(self):
        plain = self.directory / "words.txt"
        plain.write_text("# comment\nآزادی\nMyTech\n", encoding="utf-8")
        dictionary = Dictionary()
        self.assertEqual(dictionary.import_file(plain), 2)
        invalid_csv = self.directory / "wrong.csv"
        invalid_csv.write_text("word,type\nsghl,en\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            dictionary.import_file(invalid_csv)


if __name__ == "__main__":
    unittest.main()
