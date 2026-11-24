"""Tests for the pure mode logic without Home Assistant runtime."""
import ast
import re
import unittest
import unicodedata
from enum import IntEnum
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "custom_components/music_plus_lyrics/__init__.py"
module = ast.parse(SOURCE.read_text())
names = {"is_english", "LyricsMode", "lyrics_mode"}
nodes = [node for node in module.body if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names]
scope = {"re": re, "unicodedata": unicodedata, "IntEnum": IntEnum}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"), scope)
mode = scope["lyrics_mode"]


class ModeTests(unittest.TestCase):
    def test_all_five_modes(self):
        cases = [
            (("not_found", "", False, 0, 0), 0),
            (("found", "A small test", True, 100, 100), 1),
            (("found", "Український текст", True, 100, 100), 2),
            (("found", "A small test", False, 100, 100), 3),
            (("found", "Український текст", False, 100, 100), 4),
        ]
        for args, expected in cases:
            with self.subTest(args=args):
                self.assertEqual(mode(*args), expected)

    def test_disabled_translation_uses_original_mode(self):
        self.assertEqual(mode("found", "English text", True, 100, 100, False), 2)
        self.assertEqual(mode("found", "English text", False, 100, 100, False), 4)

    def test_duration_and_tolerance(self):
        self.assertEqual(mode("found", "English", True, 100, 104), 3)
        self.assertEqual(mode("found", "English", True, 100, 104, True, 5), 1)
        self.assertEqual(mode("found", "English", True, 0, 104), 3)

    def test_non_english_letters_are_not_translated(self):
        self.assertFalse(scope["is_english"]("Привіт"))
        self.assertFalse(scope["is_english"]("canción"))


if __name__ == "__main__":
    unittest.main()
