"""Unit tests for tools/minigames/realm_cabinets.py (stdlib unittest)."""
import json
import math
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import realm_cabinets as rc  # noqa: E402

CATALOG = {
    "games": [{"id": g, "title": g.title(), "host": "ADaedalusDesktopArcade", "option_count": n} for g, n in
              (("twinwake", 4), ("beacon_sweep", 3), ("star_shooter", 3), ("riftwing", 2), ("lanternwild", 2))],
    "java_cabinets": [{"id": "sudoku", "title": "SudokuPro", "host": "ADaedalusJavaArcade",
                       "game_enum": "EDaedalusJavaGame::Sudoku", "requires": "java"}],
}


def spec(**realm):
    base = {"realm": "r1"}
    base.update(realm)
    return {"realms": [base]}


class Selection(unittest.TestCase):
    def test_all_by_default_includes_java(self):
        out = rc.build(CATALOG, spec())
        self.assertEqual([c["game"] for c in out["realms"][0]["cabinets"]],
                         ["twinwake", "beacon_sweep", "star_shooter", "riftwing", "lanternwild", "sudoku"])

    def test_patterns_and_exclude(self):
        out = rc.build(CATALOG, spec(include=["*_shooter", "twinwake"], exclude=["riftwing_*"]))
        self.assertEqual([c["game"] for c in out["realms"][0]["cabinets"]], ["twinwake", "star_shooter"])

    def test_java_off(self):
        out = rc.build(CATALOG, spec(java=False))
        self.assertNotIn("sudoku", [c["game"] for c in out["realms"][0]["cabinets"]])

    def test_java_cabinet_fields(self):
        cab = rc.build(CATALOG, spec(include=["sudoku"]))["realms"][0]["cabinets"][0]
        self.assertEqual(cab["host"], "ADaedalusJavaArcade")
        self.assertEqual(cab["game_enum"], "EDaedalusJavaGame::Sudoku")
        self.assertNotIn("start", cab)

    def test_desktop_start_call_uses_seed(self):
        cab = rc.build(CATALOG, spec(include=["twinwake"]))["realms"][0]["cabinets"][0]
        self.assertEqual(cab["start"], f'StartGame("twinwake", {cab["seed"]})')


class Errors(unittest.TestCase):
    def test_unknown_game(self):
        with self.assertRaises(rc.SpecError):
            rc.build(CATALOG, spec(include=["tetris"]))

    def test_empty_selection(self):
        with self.assertRaises(rc.SpecError):
            rc.build(CATALOG, spec(include=["nothing*"]))

    def test_duplicate_realm(self):
        with self.assertRaises(rc.SpecError):
            rc.build(CATALOG, {"realms": [{"realm": "a"}, {"realm": "a"}]})

    def test_missing_realm_id(self):
        with self.assertRaises(rc.SpecError):
            rc.build(CATALOG, {"realms": [{}]})

    def test_bad_layout_and_spacing(self):
        with self.assertRaises(rc.SpecError):
            rc.build(CATALOG, spec(layout="spiral"))
        with self.assertRaises(rc.SpecError):
            rc.build(CATALOG, spec(spacing_m=0.1))


class Options(unittest.TestCase):
    def test_default_option_is_zero(self):
        cabs = rc.build(CATALOG, spec())["realms"][0]["cabinets"]
        self.assertTrue(all(c["option"] == 0 for c in cabs if c["host"] == "ADaedalusDesktopArcade"))
        self.assertTrue(all("option" not in c for c in cabs if c["host"] == "ADaedalusJavaArcade"))

    def test_option_applied(self):
        cabs = rc.build(CATALOG, spec(options={"lanternwild": 1, "twinwake": 3}))["realms"][0]["cabinets"]
        got = {c["game"]: c["option"] for c in cabs if "option" in c}
        self.assertEqual((got["lanternwild"], got["twinwake"], got["beacon_sweep"]), (1, 3, 0))

    def test_option_out_of_range(self):
        for bad in (2, -1, 1.0, True, "1"):
            with self.assertRaises(rc.SpecError, msg=repr(bad)):
                rc.build(CATALOG, spec(options={"lanternwild": bad}))

    def test_option_for_unplaced_or_java(self):
        with self.assertRaises(rc.SpecError):
            rc.build(CATALOG, spec(include=["twinwake"], options={"lanternwild": 1}))
        with self.assertRaises(rc.SpecError):
            rc.build(CATALOG, spec(options={"sudoku": 0}))
        with self.assertRaises(rc.SpecError):
            rc.build(CATALOG, spec(options=[1]))

    def test_repo_catalog_has_option_counts(self):
        catalog = json.loads(rc.CATALOG.read_text(encoding="utf-8"))
        for g in catalog["games"]:
            self.assertGreaterEqual(g["option_count"], 2, g["id"])


class Layouts(unittest.TestCase):
    def test_row_is_centred_and_spaced(self):
        pts = rc.offsets("row", 3, 2.0)
        self.assertEqual([p[1] for p in pts], [-2.0, 0.0, 2.0])
        self.assertTrue(all(p[0] == 0 and p[2] == 180.0 for p in pts))

    def test_grid_rows_and_centring(self):
        pts = rc.offsets("grid", 5, 2.0, columns=2)
        self.assertEqual(len(pts), 5)
        self.assertEqual(sorted({p[0] for p in pts}), [0.0, 2.0, 4.0])
        self.assertEqual(pts[4][1], 0.0)  # lone last cabinet is centred

    def test_arc_faces_anchor_and_keeps_spacing(self):
        pts = rc.offsets("arc", 4, 2.5)
        r = math.hypot(pts[0][0], pts[0][1])
        for x, y, yaw in pts:
            self.assertAlmostEqual(math.hypot(x, y), r, places=2)
            back = math.degrees(math.atan2(-y, -x)) % 360
            self.assertAlmostEqual(yaw, round(back, 3), places=2)
        gaps = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(3)]
        self.assertTrue(all(g >= 2.0 for g in gaps))

    def test_no_overlap_any_layout(self):
        for layout in rc.LAYOUTS:
            for n in range(1, 13):
                pts = rc.offsets(layout, n, 2.5)
                self.assertEqual(len(pts), n)
                for i in range(n):
                    for j in range(i + 1, n):
                        d = math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1])
                        self.assertGreaterEqual(d, 1.9, f"{layout} n={n}")


class Stability(unittest.TestCase):
    def test_seed_stable_and_distinct(self):
        self.assertEqual(rc.stable_seed("r", "twinwake"), rc.stable_seed("r", "twinwake"))
        self.assertNotEqual(rc.stable_seed("r", "twinwake"), rc.stable_seed("s", "twinwake"))
        self.assertTrue(0 <= rc.stable_seed("r", "twinwake") <= 0x7FFFFFFF)

    def test_deterministic_output(self):
        self.assertEqual(rc.render(rc.build(CATALOG, spec())), rc.render(rc.build(CATALOG, spec())))

    def test_repo_spec_builds_against_repo_catalog(self):
        catalog = json.loads(rc.CATALOG.read_text(encoding="utf-8"))
        data = rc.build(catalog, json.loads(rc.SPEC.read_text(encoding="utf-8")))
        self.assertTrue(data["realms"])
        ids = {g["id"] for g in catalog["games"]} | {j["id"] for j in catalog.get("java_cabinets", [])} | {p["id"] for p in catalog.get("python_games", [])}
        for realm in data["realms"]:
            self.assertTrue(all(c["game"] in ids for c in realm["cabinets"]))


class RealmsMd(unittest.TestCase):
    MD = "\n".join([
        "| Realm | Feels like | Status | x |", "|---|---|---|---|",
        "| **The Shattered Planet: Sky Islands** | a | LIVE | b |",
        "| **The Orrery Reach** (domain) | a | LIVE (Unreal) | b |",
        "| **Space (Phase 2)** | - | NAMED | b |",
        "| **Your own realm** | any | PROPOSE ONE | b |",
    ])

    def test_ids_derived_and_propose_skipped(self):
        self.assertEqual([r["id"] for r in rc.parse_realms_md(self.MD)], ["shattered_planet", "orrery_reach", "space"])

    def test_collision_rejected(self):
        with self.assertRaises(rc.SpecError):
            rc.parse_realms_md(self.MD + "\n| **Orrery Reach** | a | LIVE | b |")

    def test_every_md_realm_needs_entry(self):
        md = rc.parse_realms_md(self.MD)
        with self.assertRaises(rc.SpecError) as e:
            rc.build(CATALOG, {"realms": [{"realm": "space"}]}, md)
        self.assertIn("shattered_planet", str(e.exception))

    def test_md_realms_marked_unconfirmed(self):
        md = rc.parse_realms_md(self.MD)
        out = rc.build(CATALOG, {"realms": [{"realm": m["id"]} for m in md] + [{"realm": "extra"}]}, md)
        status = {r["realm"]: r.get("id_status") for r in out["realms"]}
        self.assertEqual(status, {"shattered_planet": "unconfirmed", "orrery_reach": "unconfirmed",
                                  "space": "unconfirmed", "extra": None})
        self.assertEqual(out["realms"][0]["anchor"], "arcade_plaza")

    def test_deterministic(self):
        md = rc.parse_realms_md(self.MD)
        sp = {"realms": [{"realm": m["id"], "layout": "arc"} for m in md]}
        self.assertEqual(rc.render(rc.build(CATALOG, sp, md)), rc.render(rc.build(CATALOG, sp, md)))


class Schema(unittest.TestCase):
    def good(self):
        return rc.build(CATALOG, spec())

    def test_good_passes(self):
        rc.validate(self.good())

    def test_bad_seed_overlap_yaw_host(self):
        for mutate in (lambda c: c.__setitem__("seed", 1), lambda c: c.__setitem__("yaw_deg", 400),
                       lambda c: c.__setitem__("host", "X"), lambda c: c.__setitem__("offset_m", [0, 0])):
            d = self.good(); mutate(d["realms"][0]["cabinets"][0])
            with self.assertRaises(rc.SpecError):
                rc.validate(d)
        d = self.good(); cabs = d["realms"][0]["cabinets"]; cabs[1]["offset_m"] = list(cabs[0]["offset_m"])
        with self.assertRaises(rc.SpecError):
            rc.validate(d)

    def test_repo_realms_md_all_covered(self):
        md = rc.parse_realms_md(rc.REALMS_MD.read_text(encoding="utf-8"))
        out = json.loads(rc.OUT.read_text(encoding="utf-8"))
        ids = {r["realm"] for r in out["realms"]}
        for m in md:
            self.assertIn(m["id"], ids)
        rc.validate(out)



class PythonGames(unittest.TestCase):
    CAT = {"games": [{"id": "alpha", "title": "Alpha", "host": "ADaedalusDesktopArcade", "option_count": 0}],
           "java_cabinets": [],
           "python_games": [{"id": "shardring", "title": "Shardring Resonance", "module": "tools/minigames/prism_shard.py",
                             "start": "prism_shard.start(seed, difficulty)", "default_difficulty": "normal"}]}

    def test_named_python_game_is_placed(self):
        out = rc.build(self.CAT, {"realms": [{"realm": "prismheart_realm", "include": ["alpha", "shardring"]}]})
        cab = out["realms"][0]["cabinets"][-1]
        self.assertEqual((cab["game"], cab["host"], cab["difficulty"]), ("shardring", rc.PY_HOST, "normal"))
        self.assertEqual(cab["seed"], rc.stable_seed("prismheart_realm", "shardring"))
        self.assertIn(str(cab["seed"]), cab["start"])

    def test_glob_does_not_pull_python_games(self):
        out = rc.build(self.CAT, {"realms": [{"realm": "r", "include": ["*"]}]})
        self.assertEqual([c["game"] for c in out["realms"][0]["cabinets"]], ["alpha"])

    def test_python_game_takes_no_option(self):
        with self.assertRaises(rc.SpecError):
            rc.build(self.CAT, {"realms": [{"realm": "r", "include": ["shardring"], "options": {"shardring": 0}}]})

    def test_real_prismheart_has_shardring(self):
        import json
        data = json.loads(rc.OUT.read_text(encoding="utf-8"))
        realm = next(r for r in data["realms"] if r["realm"] == "prismheart_realm")
        self.assertIn("shardring", [c["game"] for c in realm["cabinets"]])

if __name__ == "__main__":
    unittest.main()
