"""Tests for tools/minigames/game_dossier.py: the PDF/Excel pair builds from the JSON and reads back."""
import json
import os
import pathlib
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import game_dossier as gd  # noqa: E402


class Dossier(unittest.TestCase):
    def test_every_dossier_builds(self):
        names = sorted(p.stem for p in pathlib.Path(gd.DOSSIERS).glob("*.json"))
        self.assertTrue(names)
        with tempfile.TemporaryDirectory() as tmp:
            for name in names:
                gd.main([name, "--out", tmp])
                pdf = pathlib.Path(tmp, name + ".pdf").read_bytes()
                self.assertTrue(pdf.startswith(b"%PDF-1.4"))
                self.assertTrue(pdf.rstrip().endswith(b"%%EOF"))
                self.assertIn(b"/Type /Page ", pdf)
                with zipfile.ZipFile(os.path.join(tmp, name + ".xlsx")) as z:
                    wb = z.read("xl/workbook.xml").decode()
                for sheet in ("About", "Mechanics", "Items", "Storyline", "Placement", "Blender items"):
                    self.assertIn('name="%s"' % sheet, wb)

    def test_dossier_json_has_the_required_sections(self):
        for p in pathlib.Path(gd.DOSSIERS).glob("*.json"):
            d = json.loads(p.read_text(encoding="utf-8"))
            for key in ("id", "title", "realm", "summary", "mechanics", "items", "storyline", "placement", "blender_items"):
                self.assertIn(key, d, p.name)
            self.assertEqual(d["id"], p.stem)
            self.assertTrue(all(isinstance(x, dict) for x in d["blender_items"]))

    def test_no_secret_like_strings(self):
        for p in pathlib.Path(gd.DOSSIERS).glob("*.json"):
            text = p.read_text(encoding="utf-8").lower()
            for bad in ("api_key", "secret", "token=", "password", "-----begin"):
                self.assertNotIn(bad, text, p.name)


if __name__ == "__main__":
    unittest.main()
