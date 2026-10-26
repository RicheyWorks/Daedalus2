"""Engine-free tests for tools/minigames/desktop_save_check.py (stdlib unittest)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import desktop_save_check as d  # noqa: E402

SLOTS_H = (pathlib.Path(__file__).resolve().parents[2] / "engines/unreal/DaedalusLink/Source/DaedalusLink"
           "/Public/DesktopGames/DaedalusDesktopSaveSlots.h")


class PlanTest(unittest.TestCase):
    def test_fourteen_games_one_plan_each(self):
        plan = d.build_plan()
        self.assertEqual([p["game"] for p in plan], d.GAMES)
        self.assertEqual(len(plan), 14)
        self.assertEqual({p["expect"] for p in plan if p["game"] == "star_shooter"}, {"skip_source_menu"})
        self.assertTrue(all(p["expect"] == "manual_save" for p in plan if p["game"] != "star_shooter"))

    def test_games_and_styles_match_cpp_slot_table(self):
        text = SLOTS_H.read_text(encoding="utf-8")
        for g in d.GAMES:
            self.assertIn('{"%s","%s.dgs",' % (g, g), text)
        self.assertIn('{"star_shooter","star_shooter.dgs",SaveStyle::SourceMenu}', text)

    def test_unknown_game_rejected(self):
        with self.assertRaises(ValueError):
            d.build_plan(["nope"])

    def test_dry_run_is_default_and_prints_plan(self):
        self.assertEqual(d.main(["--games", "twinwake"]), 0)

    def test_payload_never_saves_levels(self):
        code = d.payload(d.GAMES)
        for banned in ("save_current_level", "save_dirty", "save_map", "save_packages", "EditorActorSubsystem",
                       "spawn_actor_from_class"):
            self.assertNotIn(banned, code)
        self.assertIn("get_game_world", code)


class JudgeTest(unittest.TestCase):
    def good(self, score=40):
        s = {"id": "twinwake", "score": score, "option": 1}
        return {"saved": True, "file_bytes": 120, "resumed": True, "before": dict(s), "after": dict(s)}

    def test_pass(self):
        self.assertEqual(d.judge("twinwake", self.good()), ("PASS", "restored"))

    def test_weak_pass_on_zero_score(self):
        self.assertEqual(d.judge("twinwake", self.good(0))[0], "PASS")
        self.assertIn("weak", d.judge("twinwake", self.good(0))[1])

    def test_score_mismatch_fails(self):
        r = self.good(); r["after"]["score"] = 3
        v, why = d.judge("twinwake", r)
        self.assertEqual(v, "FAIL"); self.assertIn("score", why)

    def test_missing_file_fails(self):
        r = self.good(); r["file_bytes"] = 0
        self.assertEqual(d.judge("twinwake", r)[0], "FAIL")

    def test_oversize_file_fails(self):
        r = self.good(); r["file_bytes"] = 5000
        self.assertEqual(d.judge("twinwake", r)[0], "FAIL")

    def test_resume_refused_fails(self):
        r = self.good(); r["resumed"] = False
        self.assertEqual(d.judge("twinwake", r)[0], "FAIL")

    def test_source_menu_skip_and_unexpected_accept(self):
        self.assertEqual(d.judge("star_shooter", {"saved": False})[0], "SKIP")
        self.assertEqual(d.judge("star_shooter", {"saved": True})[0], "FAIL")

    def test_error_fails(self):
        self.assertEqual(d.judge("dungeon", {"error": "boom"}), ("FAIL", "boom"))

    def test_compare_ignores_positions(self):
        ok, diffs = d.compare_states({"id": "a", "score": 1, "option": 0, "steps": 9},
                                     {"id": "a", "score": 1, "option": 0, "steps": 0})
        self.assertTrue(ok); self.assertEqual(diffs, {})


class StageTest(unittest.TestCase):
    def test_only_saved_boundaries_are_safe(self):
        self.assertTrue(d.safe_stage({"stage": "paused_saved_boundary"}))
        for s in ("native_running", "source_running", "", None):
            self.assertFalse(d.safe_stage({"stage": s}))


if __name__ == "__main__":
    unittest.main()