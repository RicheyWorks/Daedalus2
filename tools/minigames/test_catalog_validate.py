"""Unit tests for tools/minigames/catalog_validate.py (stdlib unittest)."""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import catalog_validate as cv  # noqa: E402


def game(gid, **kw):
    g = {"id": gid, "title": gid.title() + " Run", "summary": "An original round.",
         "how_to_play": "HOW Do the thing.", "difficulty": ["easy", "normal", "hard"],
         "default_difficulty": "normal", "daedalus_realm": "r1", "daedalus_spot": "The test row",
         "capabilities": ["scoreboard"]}
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

    def test_difficulty_defaults_to_normal(self):
        errs = cv.validate({"games": [game("alpha", default_difficulty="easy")]}, {"alpha"}, {})
        self.assertTrue(any("difficulty" in e for e in errs))

    def test_every_game_has_a_daedalus_spot(self):
        cat = json.loads(cv.CATALOG.read_text(encoding="utf-8"))
        cabinets = json.loads((cv.CATALOG.parents[2] / "data/minigames/realm-cabinets.json").read_text(encoding="utf-8"))
        by_realm = {r["realm"]: {c["game"] for c in r["cabinets"]} for r in cabinets["realms"]}
        self.assertGreaterEqual(len(cat["games"]), 1)
        for g in cat["games"]:
            self.assertTrue((g.get("daedalus_spot") or "").strip(), g["id"])
            self.assertEqual(cv.trademark_hits(g["daedalus_spot"]), [], g["id"])
            self.assertIn(g["id"], by_realm.get(g.get("daedalus_realm"), set()), g["id"])

    def test_repo_catalog_is_valid(self):
        cat = json.loads(cv.CATALOG.read_text(encoding="utf-8"))
        self.assertEqual(cv.validate(cat, cv.slot_ids(cv.SLOTS_HDR.read_text(encoding="utf-8"))), [])

    def test_every_entry_has_required_fields(self):
        """Score hook, how-to, access marks, difficulty, and placement are present on every cabinet."""
        cat = json.loads(cv.CATALOG.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(cat["games"]), 1)
        for g in cat["games"]:
            gid = g["id"]
            caps = g.get("capabilities") or []
            self.assertTrue((g.get("how_to_play") or "").strip(), gid)
            self.assertTrue(g.get("difficulty"), gid)
            self.assertTrue((g.get("default_difficulty") or "").strip(), gid)
            self.assertIn("scoreboard", caps, gid)
            self.assertIn("key_hint", caps, gid)
            self.assertIn("contrast_mark", caps, gid)
            self.assertTrue((g.get("daedalus_realm") or "").strip(), gid)
            self.assertTrue((g.get("daedalus_spot") or "").strip(), gid)


class Identity(unittest.TestCase):
    def cat(self, games=(), python=(), java=()):
        return {"games": list(games), "python_games": list(python), "java_cabinets": list(java)}

    def errs(self, catalog):
        ids = {g.get("id") for g in catalog["games"]}
        return cv.validate(catalog, ids, {})

    def test_duplicate_desktop_id(self):
        errs = self.errs(self.cat([game("alpha"), game("alpha", title="Other Run")]))
        self.assertTrue(any("id is also used by games[0]" in e for e in errs), errs)

    def test_duplicate_id_across_sections(self):
        errs = self.errs(self.cat([game("alpha")], python=[game("alpha", title="Py Run")]))
        self.assertTrue(any("python game 'alpha' id is also used" in e for e in errs), errs)
        errs = self.errs(self.cat([game("alpha")], java=[{"id": "alpha", "title": "J", "summary": "s"}]))
        self.assertTrue(any("Java cabinet 'alpha' id is also used" in e for e in errs), errs)

    def test_missing_or_bad_id(self):
        errs = self.errs(self.cat(python=[{"title": "T", "summary": "s", "how_to_play": "h", "difficulty": ["normal"]}]))
        self.assertTrue(any("python game at python_games[0] has no id" in e for e in errs), errs)
        for bad in ("Alpha", "al-pha", "a" * 33, "al pha"):
            errs = self.errs(self.cat([game(bad, title="Bad Run")]))
            self.assertTrue(any("must match" in e for e in errs), (bad, errs))
        self.assertFalse(any("must match" in e for e in self.errs(self.cat([game("a" * 32), game("x_9")]))))

    def test_missing_summary(self):
        errs = self.errs(self.cat([game("alpha", summary="  ")]))
        self.assertTrue(any("'alpha' has no summary" in e for e in errs), errs)
        errs = self.errs(self.cat(java=[{"id": "jj", "title": "Jay"}]))
        self.assertTrue(any("Java cabinet 'jj' has no summary" in e for e in errs), errs)

    def test_python_titles_unique_and_against_desktop(self):
        py = dict(how_to_play="h", difficulty=["normal"])
        errs = self.errs(self.cat([game("alpha", title="Glow Run")], python=[game("beta", title="glow run", **py)]))
        self.assertTrue(any("python game 'beta' title 'glow run' is also used by 'alpha'" in e for e in errs), errs)
        errs = self.errs(self.cat(python=[game("p1", title="T", **py), game("p2", title="T", **py)]))
        self.assertTrue(any("'p2' title 'T' is also used by 'p1'" in e for e in errs), errs)

    def test_titles_colliding_on_the_leaderboard(self):
        errs = self.errs(self.cat([game("alpha", title="Rally!"), game("beta", title="Rally")]))
        self.assertTrue(any("same leaderboard name as 'alpha'" in e for e in errs), errs)
        errs = self.errs(self.cat([game("alpha", title="Glow-Run"), game("beta", title="Glow  Run")]))
        self.assertTrue(any("same leaderboard name" in e for e in errs), errs)

    def test_exact_duplicate_title_reported_once(self):
        errs = self.errs(self.cat([game("alpha", title="Same"), game("beta", title="Same")]))
        self.assertEqual(sum("Same" in e for e in errs), 1, errs)

    def test_feed_name_mirrors_leaderboard_feed(self):
        import leaderboard_feed as lf
        for title in ("Pebblecourt Rally", "Wardens' Accord", "Glow--Run!!", "  x  y ", "A" * 70 + " B"):
            self.assertEqual(cv.feed_name(title), lf.sanitize_name(title).lower(), title)
        self.assertEqual(cv.ID_RE.pattern, lf._ID.pattern)


if __name__ == "__main__":
    unittest.main()
