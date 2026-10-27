"""Parity: the browser Shardring (web/shardring/index.html) matches prism_shard.py exactly.

Builds fixtures from the Python rules (shard sequence, greedy game moves, final state) and runs
shard_web_test.js under node. Skips when node is not installed.
"""
import hashlib
import json
import re
import pathlib
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import prism_shard as ps  # noqa: E402

PAGE = HERE / "web" / "shardring" / "index.html"
PAD_REL = "../../../../daedalus-server/src/main/resources/static/controllers/daedalus-pad.js"


def fixtures():
    cases = []
    for d in ps.DIFFICULTY:
        for seed in (0, 1, 7, 42, 2024, 123456789):
            g = ps.start(seed, d)
            r = random.Random(f"{ps.GAME_ID}:{seed}:{d}")
            seq = [r.choice(g.hues) for _ in range(80)]
            moves = []
            while not g.over:
                f = ps.greedy_move(g)
                moves.append(f)
                g.place(f)
            cases.append({"seed": seed, "difficulty": d, "sequence": seq, "moves": moves, "final": g.status()})
    return {"cases": cases, "sha512_abc": hashlib.sha512(b"abc").hexdigest()}


class WebPage(unittest.TestCase):
    def test_page_is_self_contained(self):
        html = PAGE.read_text(encoding="utf-8")
        self.assertIn('<script id="shardring-core">', html)
        for bad in ("http://", "https://", "<link "):
            self.assertNotIn(bad, html)
        srcs = re.findall(r'src="([^"]+)"', html)
        self.assertEqual(srcs, [PAD_REL])  # only the optional, repo-local controller module
        self.assertTrue((PAGE.parent / PAD_REL).resolve().exists())
        self.assertIn("if (window.DaedalusPad)", html)  # feature-detected, never required

    def test_page_mirrors_rule_constants(self):
        html = PAGE.read_text(encoding="utf-8")
        for d, cfg in ps.DIFFICULTY.items():
            self.assertIn(f'{d}: {{ facets: {cfg["facets"]}, hues: {cfg["hues"]}, shards: {cfg["shards"]} }}', html)
        self.assertIn(f"RUN = {ps.RUN}, SPIRIT_EVERY = {ps.SPIRIT_EVERY}, SPIRIT_BONUS = {ps.SPIRIT_BONUS}", html)
        for h, name in ps.SPIRITS.items():
            self.assertIn(f'{h}: "{name}"', html)

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_node_parity_with_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = pathlib.Path(tmp) / "fx.json"
            fx.write_text(json.dumps(fixtures()), encoding="utf-8")
            r = subprocess.run(["node", str(HERE / "shard_web_test.js"), str(fx)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("OK", r.stdout)


    def test_pad_action_map(self):
        html = PAGE.read_text(encoding="utf-8")
        self.assertIn('PAD_ACTIONS = { left: "prev", up: "prev", right: "next", down: "next", confirm: "place", menu: "restart" }', html)

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_node_controller_with_shared_pad(self):
        r = subprocess.run(["node", str(HERE / "shard_pad_test.js")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("OK", r.stdout)


if __name__ == "__main__":
    unittest.main()
