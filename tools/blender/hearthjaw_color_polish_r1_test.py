"""Portable color-plan regressions. Synthetic records are not application/render proof."""
import builtins
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import types
import unittest
from unittest import mock

SOURCE = Path(__file__).with_name("hearthjaw_color_polish_r1.py")
CODE = compile(SOURCE.read_bytes(), str(SOURCE), "exec")


def module():
    result = types.ModuleType("color_proposal_test_subject")
    result.__file__ = str(SOURCE)
    exec(CODE, result.__dict__)
    return result


M = module()
ROLES = ["M_Eco_sky_stem", "M_Eco_sky_leaf", "M_Eco_sky_leafLight",
         "M_Eco_sky_flower", "M_Eco_sky_gill", "M_Eco_sky_glow", "M_Eco_sky_root"]
HEX = dict(zip(ROLES, ["#6E4328", "#176A3A", "#6AAA45", "#C84C18", "#F2D59B", "#2DAF9A", "#382B20"]))
SLOTS = [[ROLES[1], ROLES[3], ROLES[6]],
         [ROLES[0], ROLES[1]+".001", ROLES[2], ROLES[3]+".001", ROLES[4], ROLES[5], ROLES[6]+".001"],
         [ROLES[0]+".001", ROLES[1]+".002", ROLES[2]+".001", ROLES[3]+".002", ROLES[4]+".001", ROLES[5]+".001", ROLES[6]+".002"]]


def fixture():
    fields = dict(objects=[], materials={}, world={"color": [.1, .1, .1]},
                  view={"view_transform": "AgX", "exposure": 0, "gamma": 1},
                  render={"engine": "CYCLES", "samples": 40})
    stages, docs = [], {}
    for index, slots in enumerate(SLOTS):
        roles = [ROLES[1], ROLES[3], ROLES[6]] if index == 0 else ROLES[:]
        obj = dict(name="Display_Prop_Eco_sky_hearthjaw_G%d" % index, type="MESH", materials=slots[:],
                   matrix=[1, 0, 0, 1], scale=[1, 1, 1], geometry_sha256="geometry-unchanged")
        fields["objects"].append(obj)
        for name in slots:
            fields["materials"][name] = dict(fields=dict(use_nodes=True, users=1, use_fake_user=False,
                is_library_indirect=False, diffuse_color=[.2, .3, .4, 1], surface_render_method="DITHERED"),
                nodes=dict(nodes=[dict(name="Principled BSDF", fields=dict(bl_idname="ShaderNodeBsdfPrincipled", mute=False),
                    inputs=[["Base Color", [.2, .3, .4, 1]], ["Alpha", 1], ["Weight", 0.0], ["Roughness", .68],
                            ["Metallic", .05], ["IOR", 1.5], ["Coat Weight", .15], ["Transmission Weight", 0.0],
                            ["Emission Color", [.04, .11, .08, 1]], ["Emission Strength", 1.0]]),
                    dict(name="Material Output", fields=dict(bl_idname="ShaderNodeOutputMaterial", mute=False,
                         is_active_output=True), inputs=[])], links=[["Principled BSDF", "BSDF", "Material Output", "Surface"]]))
        stages.append(dict(index=index, asset_id="Prop_Eco_sky_hearthjaw_G%d" % index, object_name=obj["name"],
            roles=roles, material_slots=slots[:], primitive_materials=list(range(len(slots))),
            object_sha256=M.fingerprint(obj), material_sha256=[M.fingerprint(fields["materials"][s]) for s in slots]))
        docs[index] = dict(materials=[dict(name=r, pbrMetallicRoughness=dict(baseColorFactor=[.2, .3, .4, 1])) for r in roles],
                           meshes=[dict(primitives=[dict(material=i) for i in range(len(slots))])], nodes=[dict(mesh=0)])
    fields["materials"]["Pedestal"] = copy.deepcopy(fields["materials"][SLOTS[0][0]])
    fields["objects"].append(dict(name="Presentation_Floor", type="MESH", materials=["Pedestal"], geometry_sha256="floor"))
    receipt = dict(schema="daedalus.hearthjaw-copy-inspection.v2", operation_intent="hearthjaw-camera-r2",
                   state="ONE_COPY_INSPECTION_RENDER_RETURNED_FINISHED", before_fields=copy.deepcopy(fields),
                   after_fields=fields, terminal_fields=copy.deepcopy(fields),
                   actual_bounds_after=dict(camera=dict(type="ORTHO", scale=10.538307189941406, location=[13, -23, 20]),
                                            objects=[dict(name=o["name"], bounds=[-1, 1]) for o in fields["objects"]]))
    recipe = dict(schema="daedalus.hearthjaw-color-proposal.v1", source_only=True, namespace="hearthjaw-color-polish-r1",
                  color_space="scene_linear_RGBA_float32", allowed_targets=["Principled BSDF.inputs.Base Color", "material.diffuse_color"],
                  palette_srgb_hex=HEX.copy(), stages=stages)
    return recipe, receipt, docs


def resync(recipe, receipt):
    """Let semantic rejection tests pass the preliminary record fingerprints."""
    fields = receipt["after_fields"]
    receipt["before_fields"] = copy.deepcopy(fields); receipt["terminal_fields"] = copy.deepcopy(fields)
    objects = {o["name"]: o for o in fields["objects"]}
    for stage in recipe["stages"]:
        stage["object_sha256"] = M.fingerprint(objects[stage["object_name"]])
        stage["material_sha256"] = [M.fingerprint(fields["materials"][n]) for n in stage["material_slots"]]


def glb(doc):
    raw = json.dumps(doc).encode(); raw += b" "*((-len(raw)) % 4)
    return b"glTF"+struct.pack("<II", 2, 20+len(raw))+struct.pack("<II", len(raw), 0x4E4F534A)+raw


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def disk_fixture(root):
    recipe, receipt, docs = fixture(); recipe["job_root"] = str(root)
    rows = []
    for s in recipe["stages"]:
        p = root/("stage%d.glb" % s["index"]); p.write_bytes(glb(docs[s["index"]])); s["glb"] = pin(p)
        g = dict(file=p.name, bytes=s["glb"]["bytes"], sha256=s["glb"]["sha256"])
        rows.append(dict(index=s["index"], assetId=s["asset_id"], lods=[dict(glb=g)]))
    scene, image = root/"copy.blend", root/"reference.png"
    scene.write_bytes(b"synthetic-not-a-Blender-file"); image.write_bytes(b"synthetic-not-pixels")
    receipt["outputs"] = [pin(scene), pin(image)]
    receiptpath, manifestpath = root/"receipt.json", root/"manifest.json"
    receiptpath.write_text(json.dumps(receipt)); manifestpath.write_text(json.dumps(dict(families=[dict(species=[dict(key="sky_hearthjaw", growthStages=rows)])])))
    source = root/"frozen.py"; source.write_text("# preserved\n")
    recipe["inputs"] = dict(scene=pin(scene), image=pin(image), receipt=pin(receiptpath), manifest=pin(manifestpath))
    recipe["source_pins"] = [pin(source)]
    path = root/"hearthjaw_color_polish_r1.recipe.json"; path.write_text(json.dumps(recipe))
    return path, recipe


class ColorProposalTests(unittest.TestCase):
    def setUp(self):
        self.recipe, self.receipt, self.docs = fixture()

    def plan(self):
        return M.make_plan(self.recipe, self.receipt, self.docs)

    def test_exact_actual_stage_slot_shape_and_determinism(self):
        p = self.plan(); self.assertEqual(p, self.plan()); self.assertEqual(17, len(p["edits"]))
        self.assertEqual([3, 7, 7], [sum(e["binding"]["stage"] == i for e in p["edits"]) for i in range(3)])
        self.assertEqual([ROLES[1], ROLES[3], ROLES[6]], [e["binding"]["role"] for e in p["edits"][:3]])
        self.assertEqual(SLOTS[2], [e["binding"]["material"] for e in p["edits"][-7:]])

    def test_linear_float32_conversion_known_values_and_transfer_branches(self):
        self.assertEqual([0., 0., 0., 1.], M.srgb_hex_linear("#000000"))
        self.assertEqual([1., 1., 1., 1.], M.srgb_hex_linear("#FFFFFF"))
        self.assertAlmostEqual(.2158605009317398, M.srgb_hex_linear("#808080")[0], places=15)
        self.assertEqual(.04045/12.92, M.srgb_channel(.04045))
        self.assertAlmostEqual(((.04046+.055)/1.055)**2.4, M.srgb_channel(.04046), places=15)
        for rgba in self.plan()["palette_linear_rgba"].values():
            self.assertEqual(1., rgba[3]); self.assertTrue(all(0 <= x <= 1 for x in rgba))
            self.assertEqual(rgba, [struct.unpack("<f", struct.pack("<f", x))[0] for x in rgba])

    def test_invalid_palette_and_rgba_refused(self):
        for bad in ("#aabbcc", "#FFF", "FF0000", "#GG0000", None, 42):
            with self.subTest(bad=bad), self.assertRaises(ValueError): M.srgb_hex_linear(bad)
        for bad in (True, float("nan"), float("inf"), -1, 1.01):
            with self.subTest(bad=bad), self.assertRaises(ValueError): M.srgb_channel(bad)
        for bad in ([0, 0, 0, .9], [True, 0, 0, 1], [float("nan"), 0, 0, 1], [0, 1, 2, 1], [0, 0, 1]):
            with self.subTest(bad=bad), self.assertRaises(ValueError): M.rgba(bad)

    def test_one_palette_identity_and_numeric_separation_only(self):
        p = self.plan(); self.assertEqual(HEX, p["palette_srgb_hex"])
        colors, lum = p["palette_linear_rgba"], p["numeric_palette_luminance"]
        self.assertGreater(colors[ROLES[3]][0], colors[ROLES[3]][1])
        self.assertGreater(colors[ROLES[1]][1], colors[ROLES[1]][0])
        self.assertGreater(lum[ROLES[4]], lum[ROLES[3]])
        self.assertGreater(lum[ROLES[2]], lum[ROLES[1]])
        self.assertLess(lum[ROLES[6]], lum[ROLES[0]])
        self.assertIsNone(p["actual"]["quality"])

    def test_inputs_immutable_and_all_execution_fields_null(self):
        before = copy.deepcopy((self.recipe, self.receipt, self.docs)); p = self.plan()
        self.assertEqual(before, (self.recipe, self.receipt, self.docs))
        self.assertTrue(all(v is None for v in p["actual"].values()))
        self.assertEqual(0, p["app_calls"]); self.assertEqual(0, p["output_writes"])
        self.assertFalse(p["runtime_ready"]); self.assertFalse(p["render_authorized"])
        for e in p["edits"]:
            self.assertEqual(0, e["recorded_bsdf_weight_retained"])
            self.assertEqual(1, e["recorded_emission_retained"]["Emission Strength"])

    def test_unknown_role_or_changed_slot_order_refused(self):
        for change in ("unknown", "reverse"):
            with self.subTest(change=change):
                recipe, receipt, docs = fixture()
                if change == "unknown": recipe["stages"][0]["roles"][0] = "Other"
                else: receipt["after_fields"]["objects"][0]["materials"].reverse(); resync(recipe, receipt)
                with self.assertRaises(ValueError): M.make_plan(recipe, receipt, docs)

    def test_glb_mapping_change_refused(self):
        for key in ("primitive", "name", "factor"):
            with self.subTest(key=key):
                docs = copy.deepcopy(self.docs)
                if key == "primitive": docs[0]["meshes"][0]["primitives"][0]["material"] = 2
                if key == "name": docs[0]["materials"][0]["name"] = "Unknown"
                if key == "factor": docs[0]["materials"][0]["pbrMetallicRoughness"]["baseColorFactor"][0] = .8
                with self.assertRaises(ValueError): M.make_plan(self.recipe, self.receipt, docs)

    def test_shared_nonplant_and_shared_plant_slot_refused(self):
        for index in (-1, 1):
            with self.subTest(owner=index):
                recipe, receipt, docs = fixture()
                receipt["after_fields"]["objects"][index]["materials"].append(SLOTS[0][0]); resync(recipe, receipt)
                with self.assertRaisesRegex(ValueError, "shared|slot"): M.make_plan(recipe, receipt, docs)

    def test_unknown_or_linked_ownership_refused(self):
        for key, value in (("users", 2), ("use_fake_user", True), ("is_library_indirect", True)):
            with self.subTest(key=key):
                recipe, receipt, docs = fixture()
                receipt["after_fields"]["materials"][SLOTS[0][0]]["fields"][key] = value; resync(recipe, receipt)
                with self.assertRaisesRegex(ValueError, "ownership"): M.make_plan(recipe, receipt, docs)

    def test_changed_hash_and_witness_refused(self):
        self.recipe["stages"][0]["material_sha256"][0] = "0"*64
        with self.assertRaisesRegex(ValueError, "recorded material"): self.plan()
        self.recipe, self.receipt, self.docs = fixture(); self.receipt["before_fields"]["render"]["samples"] = 1
        with self.assertRaisesRegex(ValueError, "witnesses"): self.plan()

    def test_unsupported_graphs_and_alpha_refused_after_repin(self):
        for kind in ("node", "base-link", "duplicate", "mute", "inactive", "alpha", "viewport", "nonfinite"):
            with self.subTest(kind=kind):
                recipe, receipt, docs = fixture(); mat = receipt["after_fields"]["materials"][SLOTS[0][0]]
                if kind == "node": mat["nodes"]["nodes"].append(copy.deepcopy(mat["nodes"]["nodes"][0]))
                if kind == "base-link": mat["nodes"]["links"].append(["Unknown", "Color", "Principled BSDF", "Base Color"])
                if kind == "duplicate": mat["nodes"]["nodes"][0]["inputs"].append(["Weight", 0.0])
                if kind == "mute": mat["nodes"]["nodes"][0]["fields"]["mute"] = True
                if kind == "inactive": mat["nodes"]["nodes"][1]["fields"]["is_active_output"] = False
                if kind == "alpha": mat["nodes"]["nodes"][0]["inputs"][1][1] = .5
                if kind == "viewport": mat["fields"]["diffuse_color"][0] = .5
                if kind == "nonfinite": mat["fields"]["some_scalar"] = float("nan")
                with self.assertRaises(ValueError):
                    resync(recipe, receipt); M.make_plan(recipe, receipt, docs)

    def hypothetical(self, plan):
        after = copy.deepcopy(self.receipt["after_fields"])
        for edit in plan["edits"]:
            mat = after["materials"][edit["binding"]["material"]]
            mat["fields"]["diffuse_color"] = edit["proposed_linear_rgba"][:]
            mat["nodes"]["nodes"][0]["inputs"][0][1] = edit["proposed_linear_rgba"][:]
        return after

    def test_hypothetical_color_only_record_accepts_without_application(self):
        p = self.plan(); before = self.receipt["after_fields"]; after = self.hypothetical(p); bounds = self.receipt["actual_bounds_after"]
        self.assertTrue(M.verify_color_only(before, after, bounds, copy.deepcopy(bounds), p))
        self.assertEqual([.2, .3, .4, 1], before["materials"][SLOTS[0][0]]["fields"]["diffuse_color"])

    def test_noncolor_shader_and_scene_changes_refused(self):
        p = self.plan(); bounds = self.receipt["actual_bounds_after"]
        for kind in ("Weight", "Roughness", "Emission Strength", "Coat Weight", "geometry", "view", "world", "floor"):
            with self.subTest(kind=kind):
                after = self.hypothetical(p)
                if kind in ("Weight", "Roughness", "Emission Strength", "Coat Weight"):
                    for socket in after["materials"][SLOTS[0][0]]["nodes"]["nodes"][0]["inputs"]:
                        if socket[0] == kind: socket[1] = .123
                if kind == "geometry": after["objects"][0]["geometry_sha256"] = "different"
                if kind == "view": after["view"]["gamma"] = 2
                if kind == "world": after["world"]["color"] = [1, 1, 1]
                if kind == "floor": after["materials"]["Pedestal"]["fields"]["diffuse_color"][0] = .8
                with self.assertRaises(ValueError): M.verify_color_only(self.receipt["after_fields"], after, bounds, bounds, p)

    def test_camera_bounds_and_wrong_planned_color_refused(self):
        p = self.plan(); after = self.hypothetical(p); bounds = self.receipt["actual_bounds_after"]
        for key in ("camera", "objects"):
            changed = copy.deepcopy(bounds); changed[key] = {"unexpected": True}
            with self.subTest(key=key), self.assertRaises(ValueError): M.verify_color_only(self.receipt["after_fields"], after, bounds, changed, p)
        mat = after["materials"][SLOTS[0][0]]; mat["fields"]["diffuse_color"] = [.5, .5, .5, 1]; mat["nodes"]["nodes"][0]["inputs"][0][1] = [.5, .5, .5, 1]
        with self.assertRaisesRegex(ValueError, "planned color"): M.verify_color_only(self.receipt["after_fields"], after, bounds, bounds, p)

    def test_exact_disk_pins_and_manifest_binding(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); path, recipe = disk_fixture(root)
            self.assertEqual(17, len(M.load_plan(path)["edits"]))
            (root/"stage0.glb").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "pinned input"): M.load_plan(path)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); path, recipe = disk_fixture(root); recipe["stages"][0]["asset_id"] = "Other"; path.write_text(json.dumps(recipe))
            with self.assertRaisesRegex(ValueError, "manifest-bound"): M.load_plan(path)

    def test_every_fixed_input_and_source_tamper_holds(self):
        for key in ("scene", "image", "receipt", "manifest", "source"):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); path, recipe = disk_fixture(root)
                target = recipe["source_pins"][0] if key == "source" else recipe["inputs"][key]
                Path(target["path"]).write_bytes(b"tampered")
                with self.assertRaisesRegex(ValueError, "pinned input"): M.load_plan(path)

    def test_glb_header_chunk_malformation_holds(self):
        raw = glb(self.docs[0]); self.assertEqual(self.docs[0], M.glb_json(raw))
        for bad in (b"", b"xxxx"+raw[4:], raw[:-1], raw[:12]+struct.pack("<II", 3, 0x4E4F534A)+b"{} ",
                    raw[:16]+b"BIN\0"+raw[20:]):
            with self.subTest(size=len(bad)), self.assertRaises(ValueError): M.glb_json(bad)

    def test_import_default_cli_reads_and_prints_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); path, _ = disk_fixture(root); stdout = io.StringIO(); original_import = builtins.__import__; original_open = io.open
            def safe_import(name, *args, **kwargs):
                if name.split(".")[0] in {"bpy", "mathutils", "subprocess", "socket", "requests", "http", "urllib"}:
                    raise AssertionError("application/process/network import: "+name)
                return original_import(name, *args, **kwargs)
            def safe_open(file, mode="r", *args, **kwargs):
                if any(flag in mode for flag in "wax+"): raise AssertionError("output write")
                return original_open(file, mode, *args, **kwargs)
            with contextlib.ExitStack() as stack:
                stack.enter_context(mock.patch("builtins.__import__", side_effect=safe_import)); stack.enter_context(mock.patch("io.open", side_effect=safe_open))
                for name in ("write_bytes", "write_text", "mkdir", "touch", "rename", "replace", "unlink"):
                    stack.enter_context(mock.patch.object(Path, name, side_effect=AssertionError("filesystem mutation")))
                subject = module(); subject.__file__ = str(root/SOURCE.name)
                with contextlib.redirect_stdout(stdout): status = subject.main([])
            self.assertEqual(0, status); result = json.loads(stdout.getvalue())
            self.assertEqual(0, result["app_calls"]); self.assertEqual(0, result["output_writes"])
            self.assertTrue(all(x is None for x in result["actual"].values()))

    def test_cli_mutation_flags_and_malformed_input_hold_json(self):
        for args in (["--apply"], ["--output", "forbidden"], ["--recipe", "no-such-recipe.json"]):
            output = io.StringIO()
            with self.subTest(args=args), contextlib.redirect_stdout(output): status = M.main(args)
            self.assertEqual(2, status); result = json.loads(output.getvalue())
            self.assertEqual("HOLD_FILE_ONLY", result["state"]); self.assertEqual(0, result["app_calls"])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"bad.json"; path.write_text("[]"); output = io.StringIO()
            with contextlib.redirect_stdout(output): self.assertEqual(2, M.main(["--recipe", str(path)]))
            self.assertEqual("HOLD_FILE_ONLY", json.loads(output.getvalue())["state"])

    def test_nested_malformed_records_refuse_without_application(self):
        for field, value in (("stages", [None]), ("stages", [{"index": True}]), ("inputs", []), ("source_pins", {})):
            with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as temp:
                path, recipe = disk_fixture(Path(temp)); recipe[field] = value; path.write_text(json.dumps(recipe))
                output = io.StringIO()
                with contextlib.redirect_stdout(output): self.assertEqual(2, M.main(["--recipe", str(path)]))
                self.assertEqual("HOLD_FILE_ONLY", json.loads(output.getvalue())["state"])
        for bad in (None, [], {"objects": [None], "materials": {}}, {"objects": [{"name": "x", "materials": None}], "materials": {}}):
            recipe, receipt, docs = fixture()
            receipt["before_fields"] = receipt["after_fields"] = receipt["terminal_fields"] = bad
            with self.subTest(record=bad), self.assertRaises(ValueError): M.make_plan(recipe, receipt, docs)
        for bad in (None, [], dict(path="x", bytes=True, sha256="0"*64)):
            with self.subTest(pin=bad), self.assertRaises(ValueError): M.checked(bad)

    def test_rehashed_receipt_cannot_change_actual_output_binding(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); path, recipe = disk_fixture(root)
            receipt_path = Path(recipe["inputs"]["receipt"]["path"]); receipt = json.loads(receipt_path.read_text())
            receipt["outputs"][0]["sha256"] = "0"*64; receipt_path.write_text(json.dumps(receipt))
            recipe["inputs"]["receipt"] = pin(receipt_path); path.write_text(json.dumps(recipe))
            with self.assertRaisesRegex(ValueError, "output/receipt"): M.load_plan(path)


if __name__ == "__main__":
    unittest.main()
