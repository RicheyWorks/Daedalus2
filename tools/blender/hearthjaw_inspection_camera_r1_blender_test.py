"""Focused ordinary-Python file/metadata tests. No bpy, fake renderer or old suite."""
import builtins
import contextlib
import copy
import io
import json
from pathlib import Path
import stat
import tempfile
import types
import unittest
from unittest import mock

SOURCE = Path(__file__).with_name("hearthjaw_inspection_camera_r1_blender.py")
caller = types.ModuleType("inspection_caller_under_test")
caller.__file__ = str(SOURCE)
exec(compile(SOURCE.read_bytes(), str(SOURCE), "exec"), caller.__dict__)


class CopyCallerContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name).absolute() / "project"
        self.presentation = self.project / caller.PRESENTATION
        self.presentation.parent.mkdir(parents=True)
        self.presentation.write_bytes(b"synthetic pinned copy-contract fixture; NOT a blend")
        self.here = self.project / "tools" / "blender" / caller.CALLER
        self.here.parent.mkdir(parents=True)
        self.here.write_bytes(SOURCE.read_bytes())
        self.inputs = [self.presentation]
        for index in range(8):
            path = self.presentation.parent / ("fixture-%d.bin" % index)
            path.write_bytes(("pinned fixture %d" % index).encode())
            self.inputs.append(path)
        def pin(path):
            raw = path.read_bytes()
            return dict(path=str(path), bytes=len(raw), sha256=caller.digest(raw))
        self.recipe = dict(source_only=True, runtime_ready=False, render_authorized=False,
                           input_pins=[pin(p) for p in self.inputs[:3]],
                           frozen_source_pins=[pin(p) for p in self.inputs[3:]],
                           future_output_proposal=caller.PROPOSAL)
        self.frozen = {}
        for name in caller.FROZEN:
            raw = json.dumps(self.recipe).encode() if name.endswith(".json") else b"# pinned source fixture\n"
            (self.here.parent / name).write_bytes(raw)
            self.frozen[name] = (len(raw), caller.digest(raw))
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(caller, "__file__", str(self.here)).start()
        mock.patch.object(caller, "FROZEN", self.frozen).start()

    @contextlib.contextmanager
    def no_apps_or_writes(self):
        original_import, original_open = builtins.__import__, Path.open
        def import_guard(name, *args, **kwargs):
            if name.split(".")[0] in ("bpy", "mathutils"):
                raise AssertionError("app import during file-only/refusal path")
            return original_import(name, *args, **kwargs)
        def open_guard(path, mode="r", *args, **kwargs):
            if any(flag in mode for flag in "wax+"):
                raise AssertionError("write during file-only/refusal path")
            return original_open(path, mode, *args, **kwargs)
        with mock.patch("builtins.__import__", side_effect=import_guard), mock.patch.object(Path, "open", open_guard), \
                mock.patch.object(Path, "mkdir", side_effect=AssertionError("mkdir before admission")):
            yield

    def invoke(self, argv):
        output = io.StringIO()
        with self.no_apps_or_writes(), contextlib.redirect_stdout(output):
            code = caller.main(argv)
        return code, json.loads(output.getvalue())

    def test_default_validates_only_and_leaves_actual_fields_null(self):
        before = sorted(str(p) for p in self.project.rglob("*"))
        code, result = self.invoke([])
        self.assertEqual(code, 0)
        self.assertEqual(result["app_calls"], 0)
        for key in ("actual_bounds", "actual_camera", "actual_sensor_fit", "fit"):
            self.assertIsNone(result[key])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["runtime_ready"])
        self.assertEqual(before, sorted(str(p) for p in self.project.rglob("*")))

    def test_unknown_arguments_and_unguarded_execute_refuse_before_app_or_write(self):
        sha = caller.digest(self.here.read_bytes())
        for argv in (["--recipe", "elsewhere"], ["--render"], ["--exe"], ["--execute"],
                     ["--caller-sha256", sha], ["--execute", "--caller-sha256", sha]):
            with self.subTest(argv=argv):
                self.assertEqual(self.invoke(argv)[0], 2)

    def test_changed_published_sources_refuse_even_with_valid_execute_arguments(self):
        for name in self.frozen:
            path = self.here.parent / name
            raw = path.read_bytes()
            path.write_bytes(raw + b" ")
            state = {"caller": self.here, "caller_sha256": caller.digest(self.here.read_bytes())}
            argv = caller.launch_prefix(self.here) + ["--", "--execute", "--caller-sha256", state["caller_sha256"]]
            self.assertEqual(self.invoke(argv)[0], 2)
            path.write_bytes(raw)

    def test_changed_canonical_or_producer_pin_refuses_before_app_or_write(self):
        for path in (self.inputs[0], self.inputs[-1]):
            raw = path.read_bytes()
            path.write_bytes(raw + b"change")
            self.assertEqual(self.invoke([])[0], 2)
            path.write_bytes(raw)

    def test_root_replay_and_unknown_path_proposal_refuse(self):
        plan = caller.output_plan(self.presentation, caller.PROPOSAL)
        self.assertEqual(len(set(plan.values())), 5)
        self.assertTrue(all(p.parent == plan["root"] for k, p in plan.items() if k != "root"))
        self.assertNotIn(self.presentation, plan.values())
        for key, value in (("directory", "../elsewhere"), ("image", "../canonical.png"),
                           ("scene", self.presentation.name), ("approved", True)):
            proposal = dict(caller.PROPOSAL, **{key: value})
            with self.assertRaises(ValueError):
                caller.output_plan(self.presentation, proposal)
        plan["root"].mkdir(parents=True)
        self.assertEqual(self.invoke([])[0], 2)

    def test_reparse_and_symlink_ancestors_refuse_without_real_junctions(self):
        leaf = self.presentation
        for link_kind in ("junction", "symlink"):
            def inspect(path):
                mode = stat.S_IFREG if path == leaf else stat.S_IFDIR
                flags = 0
                if path == leaf.parent:
                    if link_kind == "junction":
                        flags = stat.FILE_ATTRIBUTE_REPARSE_POINT
                    else:
                        mode = stat.S_IFLNK
                return types.SimpleNamespace(st_mode=mode, st_file_attributes=flags)
            with self.subTest(kind=link_kind), self.assertRaises(ValueError):
                caller.safe_path(leaf, lstat=inspect)
        with self.assertRaises(ValueError):
            caller.safe_path(leaf.parent / ".." / "escape")

    def test_exclusive_byte_verified_copy_retains_original_and_refuses_replay(self):
        original = self.presentation.read_bytes()
        target = self.presentation.parent / "private-copy.blend"
        source = self.recipe["input_pins"][0]
        caller.copy_presentation(source, target)
        self.assertEqual(target.read_bytes(), original)
        self.assertEqual(self.presentation.read_bytes(), original)
        with self.assertRaises(ValueError):
            caller.copy_presentation(source, target)
        self.assertEqual(target.read_bytes(), original)
        fresh = target.with_name("fresh.blend")
        with self.assertRaises(ValueError):
            caller.copy_presentation(dict(source, sha256="0" * 64), fresh)
        self.assertFalse(fresh.exists())

    def test_exact_guarded_launch_and_self_hash_are_required(self):
        state = caller.preflight()
        prefix = caller.launch_prefix(state["caller"])
        caller.require_launch(prefix, state, state["caller_sha256"])
        for changed in (prefix[1:], prefix + ["--python-expr", "bad"],
                        [x for x in prefix if x != "--disable-autoexec"], None):
            with self.assertRaises(ValueError):
                caller.require_launch(changed, state, state["caller_sha256"])
        with self.assertRaises(ValueError):
            caller.require_launch(prefix, state, "0" * 64)

    def inventory(self):
        plants = ["Display_Prop_Eco_sky_hearthjaw_G%d" % stage for stage in range(3)]
        names = list(plants)
        for base in ("Habitat_Platform", "Platform_Edge"):
            names.extend(base + (".%03d" % stage if stage else "") for stage in range(3))
        names.append("Presentation_Floor")
        corners = [[x, y, z] for x in (0, 1) for y in (0, 1) for z in (0, 1)]
        return plants, [dict(name=n, type="MESH", visible_render=True, world_corners=copy.deepcopy(corners)) for n in names]

    def test_complete_inventory_assigns_nine_roles_and_only_floor_is_excluded(self):
        plants, rows = self.inventory()
        rows += [dict(name="Camera", type="CAMERA"), dict(name="Key", type="LIGHT")]
        before = copy.deepcopy(rows)
        result = caller.staged_inventory(rows, plants)
        self.assertEqual(len(result), 10)
        self.assertEqual({(r["stage"], r["role"]) for r in result if r["stage"] is not None},
                         {(s, role) for s in range(3) for role in ("plant", "pedestal", "rim")})
        self.assertEqual([r["name"] for r in result if r["role"] == "background"], ["Presentation_Floor"])
        self.assertEqual(rows, before)

    def test_missing_duplicate_unassigned_hidden_and_nonfinite_meshes_refuse(self):
        plants, original = self.inventory()
        variants = [original[:-1], original + [original[0]],
                    original + [dict(original[0], name="Unexpected")],
                    original + [dict(name="Text", type="FONT")]]
        hidden = copy.deepcopy(original)
        hidden[0]["visible_render"] = False
        bad = copy.deepcopy(original)
        bad[0]["world_corners"][0][0] = float("nan")
        variants += [hidden, bad]
        for rows in variants:
            with self.subTest(rows=len(rows)), self.assertRaises(ValueError):
                caller.staged_inventory(rows, plants)

    def test_quality_requires_existing_cpu1_samples40_full_frame_and_metres(self):
        quality = dict(engine="CYCLES", device="CPU", samples=40, threads_mode="FIXED", threads=1,
                       resolution=[1800, 1400], percentage=100, full_frame=True, format="PNG", metres=True)
        caller.check_quality(quality)
        for key, value in (("device", "GPU"), ("samples", 24), ("threads", 2), ("threads_mode", "AUTO"),
                           ("resolution", [1100, 825]), ("percentage", 50), ("full_frame", False),
                           ("format", "JPEG"), ("metres", False)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                caller.check_quality(dict(quality, **{key: value}))


if __name__ == "__main__":
    unittest.main()
