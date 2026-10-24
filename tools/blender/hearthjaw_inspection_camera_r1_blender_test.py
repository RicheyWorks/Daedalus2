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


class PresentationRecovery(unittest.TestCase):
    """Run this new class alone for R2; old eleven contracts remain unchanged."""
    def facts(self, identity=False):
        comp = dict(enabled=False, render_enabled=True, tree_present=False, nodes=[], links=[], errors=[])
        if identity:
            rows = [dict(name="Layers", type="CompositorNodeRLayers", muted=False,
                         source_scene_name=None, source_scene_is_current=True, source_layer="ViewLayer"),
                    dict(name="Composite", type="CompositorNodeComposite", muted=False,
                         use_alpha=True, alpha_linked=False)]
            links = [dict(from_node="Layers", from_socket="Image", to_node="Composite", to_socket="Image", valid=True, muted=False)]
            comp.update(enabled=True, tree_present=True, tree_type="CompositorNodeTree", tree_animated=False,
                        scene_animated=False, view_layer="ViewLayer", nodes=rows, links=links,
                        full_graph_witness=dict(nodes=copy.deepcopy(rows), links=copy.deepcopy(links)))
        return dict(linked=dict(count=0, identities=[], errors=[]), composited=comp,
                    sequenced=dict(editor_exists=False, strip_count=0, strips=[], render_enabled=True, errors=[]))

    def test_separate_all_three_refusal_reasons_without_short_circuit(self):
        facts = self.facts()
        facts["linked"] = dict(count=1, identities=[dict(name="external", filepath="linked.blend")], errors=[])
        facts["composited"]["enabled"] = True
        facts["sequenced"].update(editor_exists=True, strip_count=1, strips=[dict(name="Movie")])
        result = caller.classify_presentation(facts)
        self.assertEqual(result["refusal_reasons"], ["LINKED_LIBRARIES_UNSUPPORTED",
                         "COMPOSITOR_NONIDENTITY_OR_UNKNOWN_GRAPH", "SEQUENCER_NONEMPTY_UNSUPPORTED"])
        self.assertFalse(result["safe_to_continue"])

    def test_identity_image_composite_and_empty_sequencer_are_read_only(self):
        facts = self.facts(identity=True)
        facts["sequenced"].update(editor_exists=True)
        before = copy.deepcopy(facts)
        result = caller.classify_presentation(facts)
        self.assertTrue(result["safe_to_continue"])
        self.assertEqual(result["separate_conditions"]["composited"], "PASS_UNIQUE_DIRECT_IMAGE_COMPOSITE")
        self.assertEqual(result["separate_conditions"]["sequenced"], "PASS_EMPTY_SEQUENCER_INACTIVE")
        self.assertEqual(facts, before)

    def test_transform_color_fileoutput_extra_output_and_unknown_graphs_refuse(self):
        for node_type in ("CompositorNodeTransform", "CompositorNodeGamma", "CompositorNodeOutputFile",
                          "CompositorNodeComposite", "CompositorNodeGroup", "UnknownNode"):
            facts = self.facts(identity=True)
            facts["composited"]["nodes"].append(dict(name="Extra", type=node_type, muted=False))
            with self.subTest(node_type=node_type):
                self.assertFalse(caller.classify_presentation(facts)["safe_to_continue"])
        for enabled in (True, False):
            facts = self.facts(identity=True)
            facts["composited"].update(nodes=[], links=[], render_enabled=enabled)
            self.assertFalse(caller.classify_presentation(facts)["safe_to_continue"])

    def test_wrong_scene_layer_alpha_muting_and_link_counterexamples_refuse(self):
        cases = [("source_scene_is_current", False, 0), ("source_layer", "Other", 0),
                 ("muted", True, 0), ("use_alpha", False, 1), ("alpha_linked", True, 1),
                 ("muted", True, 1)]
        for key, value, index in cases:
            facts = self.facts(identity=True)
            facts["composited"]["nodes"][index][key] = value
            with self.subTest(key=key, index=index):
                self.assertFalse(caller.classify_presentation(facts)["safe_to_continue"])
        for key, value in (("from_socket", "Alpha"), ("to_socket", "Alpha"), ("valid", False), ("muted", True)):
            facts = self.facts(identity=True)
            facts["composited"]["links"][0][key] = value
            self.assertFalse(caller.classify_presentation(facts)["safe_to_continue"])
        for key, value in (("tree_animated", True), ("scene_animated", True), ("full_graph_witness", None)):
            facts = self.facts(identity=True)
            facts["composited"][key] = value
            self.assertFalse(caller.classify_presentation(facts)["safe_to_continue"])

    def test_absent_and_empty_only_sequencer_even_when_muted_or_disabled(self):
        for editor, render in ((False, True), (True, True), (True, False)):
            facts = self.facts()
            facts["sequenced"].update(editor_exists=editor, render_enabled=render)
            self.assertTrue(caller.classify_presentation(facts)["safe_to_continue"])
        for render in (True, False):
            facts = self.facts()
            facts["sequenced"].update(editor_exists=True, render_enabled=render, strip_count=1,
                                      strips=[dict(name="Muted", muted=True)])
            self.assertFalse(caller.classify_presentation(facts)["safe_to_continue"])

    def test_partial_observation_and_inconsistent_counts_never_admit(self):
        for category in ("linked", "composited", "sequenced"):
            facts = self.facts(identity=True)
            facts[category]["errors"] = ["unsupported RNA property"]
            result = caller.classify_presentation(facts)
            self.assertFalse(result["safe_to_continue"])
            self.assertIn("FACTS_UNSUPPORTED", result["separate_conditions"][category])
        for category, key in (("linked", "count"), ("sequenced", "strip_count")):
            facts = self.facts()
            facts[category][key] = 2
            self.assertFalse(caller.classify_presentation(facts)["safe_to_continue"])

    def test_diagnostics_are_durable_before_refusal_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "presentation-before.json"
            facts = self.facts()
            facts["linked"] = dict(count=1, identities=[dict(name="Library", filepath="original.blend")], errors=[])
            with self.assertRaises(caller.PresentationRefused) as raised:
                caller.record_presentation(facts, path, context="synthetic_contract_test")
            raw = path.read_bytes()
            saved = json.loads(raw)
            self.assertEqual(saved["conditions"], facts)
            self.assertEqual(raised.exception.report, saved)
            self.assertEqual(saved["observation_context"], "synthetic_contract_test")
            self.assertEqual(saved["classification"]["separate_conditions"]["linked"], "LINKED_LIBRARIES_UNSUPPORTED")
            with self.assertRaises(FileExistsError):
                caller.record_presentation(self.facts(), path, context="synthetic_contract_test")
            self.assertEqual(path.read_bytes(), raw)

    def test_presentation_witness_changes_refuse_without_mutating_either(self):
        before = dict(conditions=self.facts(identity=True), observed_at_utc="before")
        after = copy.deepcopy(before); after["observed_at_utc"] = "after"
        caller.require_same_presentation(before, after)
        after["conditions"]["composited"]["nodes"][1]["use_alpha"] = False
        preserved = copy.deepcopy((before, after))
        with self.assertRaises(ValueError):
            caller.require_same_presentation(before, after)
        self.assertEqual((before, after), preserved)

    def test_literal_r2_binding_preserves_occupied_r1_and_frozen_recipe_proposal(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory).absolute()
            presentation = project / caller.PRESENTATION
            presentation.parent.mkdir(parents=True); presentation.write_bytes(b"synthetic path fixture")
            old = project / caller.PROPOSAL["directory"]
            old.mkdir(parents=True); witness = old / "retained_presentation_copy.blend"; witness.write_bytes(b"retain failed R1")
            proposal = copy.deepcopy(caller.PROPOSAL)
            plan = caller.output_plan(presentation, proposal)
            self.assertEqual(plan["root"], project / "artifacts/ecology/sky-botanical-pilot-r1/inspection/hearthjaw-camera-r2")
            self.assertEqual(plan["scene"].name, "hearthjaw_inspection_r2.blend")
            self.assertEqual(witness.read_bytes(), b"retain failed R1")
            self.assertEqual(proposal, caller.PROPOSAL)
            plan["root"].mkdir()
            with self.assertRaises(ValueError):
                caller.output_plan(presentation, proposal)

    def test_unknown_or_missing_r2_action_intent_cannot_execute(self):
        state = dict(caller_sha256="0"*64, paths={}, caller=SOURCE.absolute())
        for argv in (["--execute", "--operation", "hearthjaw-camera-r1"],
                     ["--operation", caller.INTENT], ["--execute", "--caller-sha256", "0"*64]):
            with mock.patch.object(caller, "preflight", return_value=state), \
                    mock.patch.object(caller, "execute_copy", side_effect=AssertionError("must not execute")), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(caller.main(argv), 2)


if __name__ == "__main__":
    unittest.main()
