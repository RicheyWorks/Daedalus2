# SPDX-License-Identifier: MIT
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_orchestrator as ro  # noqa: E402

UBT = ["Build.bat", "UnrealEditor", "Win64", "Development", "-Project=X.uproject", "-WaitMutex"]


class Fake:
    def __init__(self, **kw):
        self.calls = []
        self.lock_holder = kw.get("holder", "boss")
        self.editor = kw.get("editor", {"dirty": 0, "play": False})
        self.prod = kw.get("prod", {"pid": 1, "alive": False, "chunks_saved_this_run": 5, "failure_json": [],
                                    "last_chunk": 229, "next_index": 2391})
        self.free = kw.get("ram", 6.0)
        self.rc = kw.get("rc", {})
        self.ubt_out = kw.get("ubt_out", "Result: Succeeded")

    def run(self, cmd, cwd=None, log=None):
        name = "ubt" if cmd and cmd[0] == "Build.bat" else ("delta" if "rebuild_delta.py" in str(cmd) else
               "preflight" if "preflight.py" in str(cmd) else cmd[2])
        self.calls.append(("run", name))
        return self.rc.get(name, 0), (self.ubt_out if name == "ubt" else "fine")

    def locks(self, broker):
        self.calls.append(("locks",))
        return {"unreal": {"holder": self.lock_holder}}

    def bridge_state(self, port):
        self.calls.append(("bridge",))
        return self.editor

    def producer(self, a, b):
        self.calls.append(("producer",))
        return self.prod

    def ram(self):
        self.calls.append(("ram",))
        return self.free

    def backup(self, src, dest):
        self.calls.append(("backup",))
        return [{"path": "Binaries/Win64/x.dll"}]


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        (self.d / "ubt.json").write_text(json.dumps(UBT))

    def tearDown(self):
        self.tmp.cleanup()

    def args(self, *extra, ubt=True):
        base = ["--repo", str(self.d / "repo"), "--base", "abc", "--plugin", str(self.d / "plug"), "--dll", str(self.d / "x.dll"),
                "--backup-root", str(self.d / "bk"), "--run-dir", str(self.d / "run"), "--owner", "boss",
                "--producer-launch-dir", str(self.d / "launch"), "--stamp", "S1"]
        if ubt:
            base += ["--ubt-command-file", str(self.d / "ubt.json")]
        return ro.parse(base + list(extra))

    def test_dry_run_runs_nothing(self):
        f = Fake()
        rep = ro.orchestrate(self.args(), f)
        self.assertEqual(f.calls, [])
        self.assertEqual(rep["result"], "planned")
        self.assertEqual([s["n"] for s in rep["steps"]], [1, 2, 3, 4, 5, 6, 7])
        self.assertFalse((self.d / "run").exists())
        self.assertEqual(rep["steps"][4]["cmd"], UBT)

    def test_dry_run_flags_missing_ubt(self):
        rep = ro.orchestrate(self.args(ubt=False), Fake())
        self.assertIn("missing", rep["steps"][4]["status"])

    def test_phase_a_order_and_stops_before_ubt(self):
        f = Fake()
        rep = ro.orchestrate(self.args("--execute"), f)
        self.assertEqual(rep["result"], "awaiting_editor_close")
        self.assertEqual(f.calls, [("run", "delta"), ("run", "preflight"), ("locks",), ("bridge",), ("producer",), ("ram",), ("backup",)])
        self.assertNotIn(("run", "ubt"), f.calls)

    def refused(self, gate_text, **kw):
        f = Fake(**kw)
        rep = ro.orchestrate(self.args("--execute"), f)
        self.assertEqual(rep["result"], "refused")
        self.assertNotIn(("backup",), f.calls)
        self.assertTrue(any(gate_text in g["gate"] and not g["ok"] for g in rep["gates"]), rep["gates"])
        return rep

    def test_refuses_lease_not_owner(self):
        self.refused("lease", holder="codex-play-guard")

    def test_refuses_dirty_editor(self):
        self.refused("editor state", editor={"dirty": 2, "play": False})

    def test_refuses_play(self):
        self.refused("editor state", editor={"dirty": 0, "play": True})

    def test_refuses_bridge_silent_in_phase_a(self):
        self.refused("editor state", editor=None)

    def test_refuses_producer_mid_chunk(self):
        rep = self.refused("producer", prod={"pid": 49600, "alive": True, "chunks_saved_this_run": 31, "failure_json": [],
                                             "last_chunk": 229, "next_index": 2391})
        self.assertIn("mid-chunk", next(g["detail"] for g in rep["gates"] if "producer" in g["gate"]))

    def test_refuses_producer_failure(self):
        self.refused("producer", prod={"pid": 1, "alive": False, "chunks_saved_this_run": 3, "failure_json": ["f.json"]})

    def test_refuses_low_ram(self):
        self.refused("RAM", ram=2.9)

    def test_preflight_failure_stops(self):
        f = Fake(rc={"preflight": 1})
        rep = ro.orchestrate(self.args("--execute"), f)
        self.assertEqual(rep["result"], "failed")
        self.assertEqual(f.calls, [("run", "delta"), ("run", "preflight")])

    def phase_a(self):
        a = self.args("--execute")
        rep = ro.orchestrate(a, Fake())
        return ro.write_report(a, rep)

    def test_phase_b_full(self):
        path = self.phase_a()
        self.assertTrue(path.with_suffix(".md").exists())
        f = Fake(editor=None)
        rep = ro.orchestrate(self.args("--execute", "--editor-closed", "--resume", str(path)), f)
        self.assertEqual(rep["result"], "ok", rep)
        runs = [c[1] for c in f.calls if c[0] == "run"]
        self.assertEqual(runs, ["ubt", "write", "verify"])

    def test_phase_b_refuses_when_editor_answers(self):
        path = self.phase_a()
        f = Fake()
        rep = ro.orchestrate(self.args("--execute", "--editor-closed", "--resume", str(path)), f)
        self.assertEqual(rep["result"], "refused")
        self.assertNotIn(("run", "ubt"), f.calls)

    def test_phase_b_needs_resume_and_ubt(self):
        f = Fake(editor=None)
        self.assertEqual(ro.orchestrate(self.args("--execute", "--editor-closed"), f)["result"], "refused")
        path = self.phase_a()
        rep = ro.orchestrate(self.args("--execute", "--editor-closed", "--resume", str(path), ubt=False), f)
        self.assertEqual(rep["result"], "refused")
        self.assertNotIn(("run", "ubt"), f.calls)

    def test_ubt_failure_gives_restore_hint_and_no_receipt(self):
        path = self.phase_a()
        f = Fake(editor=None, ubt_out="Result: Failed")
        rep = ro.orchestrate(self.args("--execute", "--editor-closed", "--resume", str(path)), f)
        self.assertEqual(rep["result"], "failed")
        self.assertIn("restore backup", rep["restore_hint"])
        self.assertNotIn(("run", "write"), f.calls)

    def test_editor_closed_requires_execute(self):
        with self.assertRaises(SystemExit):
            self.args("--editor-closed")

    def test_probe_avoids_global_b(self):
        import re
        self.assertIsNone(re.search(r"(^|[^\w])b\s*=", ro.EDITOR_PROBE))

    def test_real_backup_copies_binaries_with_manifest(self):
        src = self.d / "plug"
        (src / "Binaries" / "Win64").mkdir(parents=True)
        (src / "Binaries" / "Win64" / "x.dll").write_bytes(b"dll")
        (src / "DaedalusLink.uplugin").write_text("{}")
        (src / "Source").mkdir()
        (src / "Source" / "a.cpp").write_text("x")
        rows = ro.Env().backup(src, self.d / "bk" / "S1")
        self.assertEqual(sorted(r["path"] for r in rows), ["Binaries/Win64/x.dll", "DaedalusLink.uplugin"])
        self.assertTrue((self.d / "bk" / "S1" / "backup-manifest.json").exists())
        with self.assertRaises(FileExistsError):
            ro.Env().backup(src, self.d / "bk" / "S1")


if __name__ == "__main__":
    unittest.main()
