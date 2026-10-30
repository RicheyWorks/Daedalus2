"""Offline tests for tools/capture (no Unreal): schema validation, camera maths, manifest, and the Unreal runner
against a mocked `unreal` module (checks temp actor cleanup, one export per view, manifest written)."""
import json, math, os, sys, tempfile, unittest, unittest.mock as um
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import capture_job as cj

JOB = json.load(open(os.path.join(HERE, "jobs", "ytm_island.json")))

class Schema(unittest.TestCase):
    def test_example_job_valid(self):
        j = cj.load(JOB); self.assertEqual(len(j["views"]), 8); self.assertEqual(j["width"], 1600); self.assertEqual(j["clip"]["fps"], 30)
    def bad(self, **kw):
        d = json.loads(json.dumps(JOB)); d.update(kw)
        with self.assertRaises(cj.JobError): cj.load(d)
    def test_rejects(self):
        self.bad(schema="capture/v0"); self.bad(name="Bad Name"); self.bad(origin=[0, 0]); self.bad(views=[])
        self.bad(views=[JOB["views"][0], JOB["views"][0]]); self.bad(width=10)
        self.bad(views=[{"name": "same", "eye": [1, 2, 3], "target": [1, 2, 3]}])
        self.bad(clip={"sequence": "Seq/X"}); self.bad(clip={"sequence": "/Game/X", "frames": 5000})
    def test_clip_optional(self):
        d = dict(JOB); d.pop("clip"); self.assertNotIn("clip", cj.load(d))

class Maths(unittest.TestCase):
    def test_rotation(self):
        self.assertEqual(cj.rotation([0, 0, 0], [100, 0, 0]), (0.0, 0.0))
        p, y = cj.rotation([0, 0, 0], [0, 100, 0]); self.assertAlmostEqual(y, 90)
        p, y = cj.rotation([0, 0, 100], [100, 0, 0]); self.assertAlmostEqual(p, -45)
    def test_plan_world_space(self):
        pl = cj.plan(cj.load(JOB)); self.assertEqual(pl[0]["eye"], [-9000.0, -2609000.0, 7000.0])
        self.assertEqual(pl[0]["file"], "ytm_island_overview.png")
        for p in pl:  # every view looks down or level, never up into sky
            self.assertLessEqual(p["pitch"], 0.5)

class Manifest(unittest.TestCase):
    def test_complete_flag(self):
        j = cj.load(JOB); files = [p["file"] for p in cj.plan(j)]
        self.assertTrue(cj.manifest(j, files, "abc")["complete"]); self.assertFalse(cj.manifest(j, files[:-1])["complete"])
        self.assertTrue(cj.manifest(j, files)["captured_at"].endswith("PT"))

class RunnerMocked(unittest.TestCase):
    def test_runner(self):
        u = um.MagicMock(); u.Vector = lambda *a: a; u.Rotator = lambda **k: k
        act = um.MagicMock(); spawned = []; destroyed = []; exported = []
        act.get_all_level_actors.return_value = []
        def sp(cls, l, r): a = um.MagicMock(); spawned.append(a); return a
        act.spawn_actor_from_class.side_effect = sp; act.destroy_actor.side_effect = destroyed.append
        act.is_in_play_in_editor.return_value = False
        u.get_editor_subsystem.return_value = act
        u.RenderingLibrary.export_render_target.side_effect = lambda w, rt, d, f: exported.append(f)
        with tempfile.TemporaryDirectory() as td, um.patch.dict(sys.modules, {"unreal": u}):
            jp = os.path.join(td, "job.json"); d = dict(JOB); d["out_dir"] = td; json.dump(d, open(jp, "w"))
            g = {"__name__": "capture_ue", "__file__": os.path.join(HERE, "capture_ue.py")}
            exec(open(os.path.join(HERE, "capture_ue.py")).read(), g)
            m = g["run"](jp)
            self.assertEqual(len(spawned), 1); self.assertEqual(destroyed, spawned)  # temp capture removed
            self.assertEqual(len(exported), 9); self.assertTrue(m["complete"]); self.assertIsNone(m["clip"])
            self.assertTrue(os.path.exists(os.path.join(td, "ytm_island", "manifest.json")))
    def test_refuses_during_pie(self):
        u = um.MagicMock(); act = um.MagicMock(); act.is_in_play_in_editor.return_value = True; u.get_editor_subsystem.return_value = act
        with um.patch.dict(sys.modules, {"unreal": u}):
            g = {"__name__": "capture_ue", "__file__": os.path.join(HERE, "capture_ue.py")}
            exec(open(os.path.join(HERE, "capture_ue.py")).read(), g)
            with self.assertRaises(RuntimeError): g["stills"](cj.load(JOB))

if __name__ == "__main__":
    unittest.main()
