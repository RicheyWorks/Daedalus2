"""Unit tests for tools/minigames/catalog_validate.py (stdlib unittest)."""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import catalog_validate as cv  # noqa: E402


def game(gid, **kw):
    g = {"id": gid, "title": gid.title() + " Run", "summary": "An original round.",
         "how_to_play": "HOW Do the thing.", "capabilities": ["scoreboard"]}
    g.update(kw)
    return g


class Validate(unittest.TestCase):
    def test_clean_catalog_passes(self):
        self.assertEqual(cv.validate({"games": [game("alpha"), game("beta")]}, {"alpha", "beta"}, {}), [])

    def test_missing_slot_howto_scoreboard(self):
        errs = cv.validate({"games": [game("alpha", how_to_play="", capabilities=[])]}, set(), {})
        self.assertEqual(len(errs), 3)
        self.assertTrue(any("save slot" in e for e in errs))
        self.assertTrue(any("how-to" in e for e in errs))
        self.assertTrue(any("scoreboard" in e for e in errs))

    def test_pending_slot_allowed_then_must_be_removed(self):
        self.assertEqual(cv.validate({"games": [game("alpha")]}, set(), {"alpha": "PR 1"}), [])
        errs = cv.validate({"games": [game("alpha")]}, {"alpha"}, {"alpha": "PR 1"})
        self.assertIn("remove it from SAVE_SLOT_PENDING", errs[0])
        self.assertTrue(cv.validate({"games": [game("alpha")]}, {"alpha"}, {"ghost": "PR 1"}))

    def test_trademarks_caught_in_every_field(self):
        for field, text in (("id", "zelda"), ("title", "Super Mario Dash"), ("summary", "Like Pac-Man"),
                            ("how_to_play", "HOW Play it like Contra.")):
            errs = cv.validate({"games": [game("alpha", **{field: text})]}, {"alpha", "zelda"}, {})
            self.assertTrue(any("trademarked" in e for e in errs), (field, errs))

    def test_spelling_variants(self):
        for text in ("PacMan", "pac_man", "SEGA", "Mega-Man", "space invaders", "Q*bert"[0:0] + "qbert"):
            self.assertTrue(cv.trademark_hits(text), text)

    def test_no_false_positives_on_original_words(self):
        for text in ("Twinwake Volley", "Linked lanterns", "Ponger", "Segment", "Contrast marks",
                     "Beacon Sweep", "Mariner", "Sonics", "Gloam Latch", "Reedbeat"):
            self.assertEqual(cv.trademark_hits(text), [], text)

    def test_duplicate_titles(self):
        errs = cv.validate({"games": [game("a", title="Same"), game("b", title="same")]}, {"a", "b"}, {})
        self.assertTrue(any("also used" in e for e in errs))

    def test_java_titles_checked(self):
        errs = cv.validate({"games": [], "java_cabinets": [{"id": "x", "title": "Tetris Pro", "summary": ""}]}, set(), {})
        self.assertTrue(errs)

    def test_repo_catalog_is_valid(self):
        cat = json.loads(cv.CATALOG.read_text(encoding="utf-8"))
        self.assertEqual(cv.validate(cat, cv.slot_ids(cv.SLOTS_HDR.read_text(encoding="utf-8"))), [])


if __name__ == "__main__":
    unittest.main()
