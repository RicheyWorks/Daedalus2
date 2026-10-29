# SPDX-License-Identifier: MIT
"""Tests for the DSB1 leaderboard feed. No network. Mirrors the host good and bad files."""
import ast
import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import leaderboard_feed as feed  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
SLOTS = ROOT / "engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DesktopGames/DaedalusDesktopSaveSlots.h"

# The eight bad files from best_scores_test.cpp. A bad file is refused whole.
BAD_FILES = (
    "",
    "DSB2\n",
    "DSB1\ntwinwake\n",
    "DSB1\ntwinwake -1\n",
    "DSB1\ntwinwake 1 2\n",
    "DSB1\nTwin 1\n",
    "DSB1\ntwinwake 1000000000001\n",
    "DSB1\ntwinwake x\n",
)

TITLES = {
    "beacon_sweep": "Beacon Sweep",
    "twinwake": "Twinwake Volley",
    "reedbeat": "Reedbeat",
    "football": "Football / Soccer",
    "dodge_ball": "Courtyard Clash",
}


def lines_for(rows):
    return "DSB1\n" + "".join(f"{gid} {score}\n" for gid, score in rows)


class Parse(unittest.TestCase):
    def setUp(self):
        self.aliases = feed.load_aliases(SLOTS.read_text(encoding="utf-8"))

    def test_valid_file_round_trip_and_replace(self):
        current = {"keep": 9}
        text = lines_for([("zed", 1), ("alpha", 2)])
        ok, table = feed.restore(text, current, {})
        self.assertTrue(ok)
        self.assertEqual(table, {"alpha": 2, "zed": 1})
        self.assertEqual(current, {"keep": 9})
        self.assertEqual(feed.dumps_dsb1(table), "DSB1\nalpha 2\nzed 1\n")
        again, replaced = feed.restore(feed.dumps_dsb1(table), table, {})
        self.assertTrue(again)
        self.assertEqual(replaced, table)

    def test_empty_table(self):
        for text in ("DSB1", "DSB1\n", "DSB1\n\n"):
            ok, table = feed.restore(text, {"twinwake": 1}, {})
            self.assertTrue(ok, text)
            self.assertEqual(table, {})

    def test_ties_break_on_canonical_id_and_ignore_input_order(self):
        forward = lines_for([("twinwake", 5), ("reedbeat", 5), ("beacon_sweep", 9)])
        backward = lines_for([("beacon_sweep", 9), ("reedbeat", 5), ("twinwake", 5)])
        entries = feed.build_entries(forward, TITLES, {})
        self.assertEqual(feed.to_json(entries), feed.to_json(feed.build_entries(backward, TITLES, {})))
        self.assertEqual([e["rank"] for e in entries], [1, 2, 3])
        self.assertEqual([e["game_id"] for e in entries], ["beacon_sweep", "reedbeat", "twinwake"])
        self.assertEqual([e["score"] for e in entries], [9, 5, 5])
        self.assertEqual(entries[1]["name"], "Reedbeat")
        self.assertEqual(entries[2]["name"], "Twinwake Volley")
        self.assertEqual(
            feed.to_text(entries),
            "DLB1\n"
            "1 beacon\\_sweep 9 Beacon Sweep\n"
            "2 reedbeat 5 Reedbeat\n"
            "3 twinwake 5 Twinwake Volley\n",
        )
        blob = feed.to_json(entries)
        self.assertTrue(blob.startswith('{\n  "format": "daedalus.leaderboard.feed/v1"'))
        loaded = json.loads(blob)
        self.assertEqual(loaded["tie_break"], "score_desc_then_game_id_asc")
        self.assertEqual(loaded["rank_rule"], "ordinal")
        self.assertEqual(loaded["source"], "DSB1")
        self.assertNotIn("network", loaded)

    def test_aliases_merge_and_keep_the_higher_score(self):
        self.assertEqual(self.aliases["pong"], "twinwake")
        self.assertEqual(self.aliases["minesweeper"], "beacon_sweep")
        for text in (
            "DSB1\npong 9\ntwinwake 4\n",
            "DSB1\ntwinwake 4\npong 9\n",
            "DSB1\npong 4\ntwinwake 9\n",
        ):
            entries = feed.build_entries(text, TITLES, self.aliases)
            self.assertEqual(len(entries), 1, text)
            self.assertEqual(entries[0]["game_id"], "twinwake")
            self.assertEqual(entries[0]["name"], "Twinwake Volley")
            self.assertEqual(entries[0]["score"], 9)
        both = feed.build_entries("DSB1\nminesweeper 3\nbeacon_sweep 8\npong 1\n", TITLES, self.aliases)
        self.assertEqual([(e["game_id"], e["score"]) for e in both], [("beacon_sweep", 8), ("twinwake", 1)])

    def test_record_clamps_and_file_over_max_is_refused(self):
        table = {}
        self.assertTrue(feed.record(table, "reedbeat", feed.MAX_SCORE + 5, self.aliases))
        self.assertEqual(table["reedbeat"], feed.MAX_SCORE)
        saved = feed.dumps_dsb1(table)
        self.assertIn("reedbeat 1000000000000\n", saved)
        ok, restored = feed.restore(saved, {}, self.aliases)
        self.assertTrue(ok)
        self.assertEqual(restored["reedbeat"], feed.MAX_SCORE)
        self.assertEqual(feed.build_entries(saved, TITLES, self.aliases)[0]["score"], feed.MAX_SCORE)
        self.assertTrue(feed.restore("DSB1\nreedbeat 1000000000000\n", {}, {})[0])
        self.assertTrue(feed.restore("DSB1\nreedbeat +7\n", {}, {})[0])
        self.assertEqual(feed.parse_dsb1("DSB1\nreedbeat +7\n", {}), {"reedbeat": 7})

    def test_bad_files_match_host_fixtures_and_leave_the_table(self):
        current = {"twinwake": 51, "reedbeat": 3}
        saved = feed.dumps_dsb1(current)
        for bad in BAD_FILES:
            ok, table = feed.restore(bad, current, self.aliases)
            self.assertFalse(ok, repr(bad))
            self.assertEqual(table, current)
            self.assertEqual(feed.dumps_dsb1(table), saved)

    def test_more_malformed_files_are_refused(self):
        current = {"twinwake": 1}
        samples = (
            "DSB1\r\ntwinwake 1\n",
            "DSB1\n@everyone 1\n",
            "DSB1\n@here 1\n",
            "DSB1\n<@123> 1\n",
            "DSB1\ntwin*wake 1\n",
            "DSB1\n../x 1\n",
            "DSB1\n  \n",
            "DSB1\n" + ("a" * 33) + " 1\n",
            "DSB1\ntwinwake 1\nextra\n",
            "x" * (feed.MAX_TEXT + 1),
            "DSB1\ntwinwake 1 2 3\n",
            "DSB1\ntwinwake\n1\n",
        )
        for bad in samples:
            ok, table = feed.restore(bad, current, {})
            self.assertFalse(ok, repr(bad[:40]))
            self.assertEqual(table, current)
        self.assertTrue(feed.restore("DSB1\n" + ("a" * 32) + " 1\n", {}, {})[0])
        with self.assertRaises(feed.FeedRefused) as big:
            feed.parse_dsb1("n" * (feed.MAX_TEXT + 1), {})
        self.assertEqual(big.exception.reason, "too_large")
        with self.assertRaises(feed.FeedRefused) as header:
            feed.parse_dsb1("n" * feed.MAX_TEXT, {})
        self.assertEqual(header.exception.reason, "header")

    def test_sixty_four_game_cap(self):
        def text(count, extra=""):
            body = "".join(f"g{i} 1\n" for i in range(count))
            return "DSB1\n" + body + extra

        ok, table = feed.restore(text(64), {"nope": 1}, {})
        self.assertTrue(ok)
        self.assertEqual(len(table), 64)
        self.assertNotIn("nope", table)
        current = {"twinwake": 4}
        self.assertFalse(feed.restore(text(65), current, {})[0])
        self.assertEqual(current, {"twinwake": 4})
        merged = text(64, "g0 9\n")
        ok, table = feed.restore(merged, {}, {})
        self.assertTrue(ok)
        self.assertEqual(len(table), 64)
        self.assertEqual(table["g0"], 9)
        # pong is a new canonical id (twinwake) on top of 64 other games.
        self.assertFalse(feed.restore(text(64) + "pong 5\n", {}, self.aliases)[0])
        held = {}
        for n in range(70):
            feed.record(held, f"g{n}", 1, {})
        self.assertEqual(len(held), feed.MAX_GAMES)
        self.assertIn("g63", held)
        self.assertNotIn("g64", held)
        self.assertTrue(feed.record(held, "g0", 2, {}))
        self.assertEqual(held["g0"], 2)
        self.assertFalse(feed.record(held, "g64", 9, {}))
        self.assertFalse(feed.record(held, "twinwake", -1, {}))
        self.assertFalse(feed.record(held, "", 5, {}))
        self.assertFalse(feed.record(held, "Bad Id", 5, {}))
        self.assertFalse(feed.record(held, "../x", 5, {}))
        self.assertFalse(feed.record(held, "@everyone", 5, {}))
        self.assertEqual(len(held), 64)

    def test_ids_and_names_cannot_inject_mentions_or_markdown(self):
        hostile = {
            "twinwake": "@everyone @here **bold** _em_ `code` ||hide|| <@123> <#456> [x](y)",
            "beacon_sweep": "Beacon\n@everyone",
            "reedbeat": "***",
        }
        text = lines_for([("twinwake", 3), ("beacon_sweep", 2), ("reedbeat", 1)])
        entries = feed.build_entries(text, hostile, {})
        js = feed.to_json(entries)
        tx = feed.to_text(entries)
        for blob in (js, tx):
            self.assertNotIn("@everyone", blob)
            self.assertNotIn("@here", blob)
            self.assertNotIn("<@", blob)
            self.assertNotIn("<#", blob)
            self.assertNotIn("**", blob)
            self.assertNotIn("`", blob)
            self.assertNotIn("||", blob)
            self.assertNotIn("\n@", blob)
        by_id = {e["game_id"]: e for e in entries}
        self.assertEqual(by_id["twinwake"]["game_id"], "twinwake")
        self.assertEqual(by_id["twinwake"]["name"], "everyone here bold em code hide 123 456 x y")
        self.assertNotRegex(by_id["twinwake"]["name"], r"[^A-Za-z0-9 ]")
        self.assertEqual(by_id["beacon_sweep"]["name"], "Beacon everyone")
        self.assertEqual(by_id["reedbeat"]["name"], "reedbeat")
        self.assertIn("beacon\\_sweep", tx)
        self.assertEqual(json.loads(js)["entries"][1]["game_id"], "beacon_sweep")
        for bad in ("@everyone", "@here", "<@99>", "twin*wake", "twin`wake", "every**one", "||x||"):
            self.assertFalse(feed.restore(f"DSB1\n{bad} 1\n", {"twinwake": 1}, {})[0])

    def test_catalog_titles_are_display_safe(self):
        catalog = json.loads(feed.CATALOG_PATH.read_text(encoding="utf-8"))
        titles = feed.load_titles(catalog)
        self.assertEqual(feed.display_name("football", titles), "Football Soccer")
        self.assertEqual(feed.display_name("dodge_ball", titles), "Pebblecourt Rally")
        self.assertEqual(feed.display_name("twinwake", titles), "Twinwake Volley")
        for gid in feed.scoreboard_ids(catalog):
            name = feed.display_name(gid, titles)
            self.assertRegex(name, r"^[A-Za-z0-9]+(?: [A-Za-z0-9]+)*$")
            self.assertNotIn("@", name)
            self.assertNotIn("_", name)

    def test_hook_accepts_the_repo_catalog(self):
        catalog = json.loads(feed.CATALOG_PATH.read_text(encoding="utf-8"))
        self.assertEqual(feed.hook_errors(catalog, SLOTS.read_text(encoding="utf-8")), [])
        self.assertEqual(catalog["leaderboard_feed"], feed.CATALOG_HOOK)
        self.assertEqual(catalog["leaderboard_feed"]["network"], "none")

    def test_hook_flags_a_missing_block_and_a_dangling_alias(self):
        header = "inline constexpr std::array<GameAlias,0> GameAliases{{}};"
        catalog = {
            "leaderboard_feed": dict(feed.CATALOG_HOOK),
            "games": [{"id": "twinwake", "title": "Twinwake Volley", "capabilities": ["scoreboard"]}],
        }
        self.assertEqual(feed.hook_errors(catalog, header), [])
        broken = dict(catalog)
        broken.pop("leaderboard_feed")
        self.assertTrue(any("leaderboard_feed" in e for e in feed.hook_errors(broken, header)))
        dangling = 'inline constexpr std::array<GameAlias,1> GameAliases{{{"pong","missing_game","pong.dgs"},}};'
        problems = feed.hook_errors(catalog, dangling)
        self.assertTrue(any("missing_game" in e for e in problems))

    def test_module_imports_nothing_that_can_post(self):
        src = pathlib.Path(feed.__file__).read_text(encoding="utf-8")
        modules = []
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Import):
                modules.extend(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module.split(".")[0])
        self.assertEqual(sorted(set(modules)), ["__future__", "argparse", "json", "pathlib", "re", "sys"])
        for banned in ("https://", "http://", "discord.com", "api/webhooks", "import socket", "import urllib"):
            self.assertNotIn(banned, src)

    def test_cli_check_and_export(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(feed.main(["--check"]), 0)
        self.assertIn("leaderboard feed ok", out.getvalue())
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "best_scores.dgs"
            # Host Save() uses LF only. write_text would rewrite those as CRLF on Windows.
            path.write_bytes(b"DSB1\npong 9\ntwinwake 4\nfootball 2\n")
            exported = io.StringIO()
            with contextlib.redirect_stdout(exported):
                self.assertEqual(feed.main([str(path)]), 0)
            loaded = json.loads(exported.getvalue())
            self.assertEqual([e["game_id"] for e in loaded["entries"]], ["twinwake", "football"])
            self.assertEqual(loaded["entries"][0]["score"], 9)
            self.assertEqual(loaded["entries"][0]["name"], "Twinwake Volley")
            self.assertEqual(loaded["entries"][1]["name"], "Football Soccer")
            text_out = io.StringIO()
            with contextlib.redirect_stdout(text_out):
                self.assertEqual(feed.main(["--text", str(path)]), 0)
            self.assertTrue(text_out.getvalue().startswith("DLB1\n"))
            self.assertNotIn("@everyone", text_out.getvalue())
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(feed.main([str(pathlib.Path(tmp) / "missing.dgs")]), 1)
            path.write_bytes(b"DSB1\n@everyone 1\n")
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(feed.main([str(path)]), 1)
            self.assertIn("refused:", err.getvalue())


if __name__ == "__main__":
    unittest.main()
