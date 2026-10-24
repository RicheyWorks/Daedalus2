"""New source/mock contracts only. No Blender process, rendering or old suites."""
import builtins
import contextlib
import copy
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import types
import unittest
from unittest import mock

SOURCE = Path(__file__).with_name("hearthjaw_color_polish_r1_blender.py")
CODE = compile(SOURCE.read_bytes(), str(SOURCE), "exec")


def subject():
    result = types.ModuleType("color_adapter_subject"); result.__file__ = str(SOURCE)
    exec(CODE, result.__dict__); return result


M = subject()
COLOR, OLD, _ = M.dependencies(SOURCE)
ROLES = ["M_Eco_sky_"+x for x in ("stem", "leaf", "leafLight", "flower", "gill", "glow", "root")]
SLOTS = [[ROLES[1], ROLES[3], ROLES[6]],
         [ROLES[0], ROLES[1]+".001", ROLES[2], ROLES[3]+".001", ROLES[4], ROLES[5], ROLES[6]+".001"],
         [ROLES[0]+".001", ROLES[1]+".002", ROLES[2]+".001", ROLES[3]+".002", ROLES[4]+".001", ROLES[5]+".001", ROLES[6]+".002"]]
NS = types.SimpleNamespace


def fixture():
    fields = dict(objects=[], materials={}, world=dict(fields=dict(session_uid=125, strength=.4)), view=dict(gamma=1, exposure=0))
    for i, slots in enumerate(SLOTS):
        fields["objects"].append(dict(name="Display_Prop_Eco_sky_hearthjaw_G%d" % i, type="MESH", materials=slots[:], geometry_sha256="fixed", matrix=[1, 0], scale=[1, 1, 1]))
    for i in range(3):
        suffix = ".%03d" % i if i else ""
        for name, material in (("Habitat_Platform", "Presentation_Botanical_Plinth"), ("Platform_Edge", "Presentation_Plinth_Rim")):
            fields["objects"].append(dict(name=name+suffix, type="MESH", materials=[material], geometry_sha256="fixed"))
    fields["objects"].append(dict(name="Presentation_Floor", type="MESH", materials=["Presentation_Backdrop"], geometry_sha256="fixed"))
    for i, name in enumerate(sorted(M.UID_OBJECTS)):
        fields["objects"].append(dict(name=name, type="CAMERA" if "Camera" in name else "LIGHT", data=dict(session_uid=121+i, name=name)))
    fields["objects"].sort(key=lambda o:o["name"])
    names = sorted({s for slots in SLOTS for s in slots} | M.PROTECTED_MATERIALS)
    for i, name in enumerate(names):
        fields["materials"][name] = dict(fields=dict(session_uid=101+i, name=name, use_nodes=True,
            users=3 if name in {"Presentation_Botanical_Plinth", "Presentation_Plinth_Rim"} else 1,
            use_fake_user=False, use_extra_user=False, is_library_indirect=False, diffuse_color=[.2, .3, .4, 1]),
            nodes=dict(nodes=[dict(name="Principled BSDF", fields=dict(bl_idname="ShaderNodeBsdfPrincipled", mute=False),
                inputs=[["Base Color", [.2, .3, .4, 1]], ["Alpha", 1], ["Weight", 0], ["Roughness", .68],
                        ["Emission Color", [.04, .11, .08, 1]], ["Emission Strength", 1]]),
                dict(name="Material Output", fields=dict(bl_idname="ShaderNodeOutputMaterial", mute=False, is_active_output=True), inputs=[])],
                links=[["Principled BSDF", "BSDF", "Material Output", "Surface"]]))
    recipe = dict(schema="daedalus.hearthjaw-color-proposal.v1", namespace=M.INTENT, source_only=True,
        color_space=COLOR.COLOR_SPACE, allowed_targets=COLOR.ALLOWED,
        palette_srgb_hex=dict(zip(ROLES, ["#6E4328", "#176A3A", "#6AAA45", "#C84C18", "#F2D59B", "#2DAF9A", "#382B20"])), stages=[])
    docs = {}; objects = {o["name"]:o for o in fields["objects"]}
    for i, slots in enumerate(SLOTS):
        roles = [ROLES[1], ROLES[3], ROLES[6]] if i == 0 else ROLES[:]
        name = "Display_Prop_Eco_sky_hearthjaw_G%d" % i
        recipe["stages"].append(dict(index=i, object_name=name, roles=roles, material_slots=slots[:],
            primitive_materials=list(range(len(slots))), object_sha256=COLOR.fingerprint(objects[name]),
            material_sha256=[COLOR.fingerprint(fields["materials"][n]) for n in slots]))
        docs[i] = dict(materials=[dict(name=r, pbrMetallicRoughness=dict(baseColorFactor=[.2, .3, .4, 1])) for r in roles],
            meshes=[dict(primitives=[dict(material=j) for j in range(len(slots))])], nodes=[dict(mesh=0)])
    bounds = dict(camera=dict(location=[13, -23, 20], ortho_scale=10.538307189941406), objects=[dict(name=o["name"], bounds=[-1, 1]) for o in fields["objects"] if o["type"]=="MESH"])
    quality = dict(engine="CYCLES", device="CPU", samples=40, threads=1, resolution=[1800, 1400])
    inventory = [dict(name=o["name"], type=o["type"]) for o in fields["objects"]]
    presentation = dict(linked=False, compositor=False, strips=0)
    historical = dict(schema="daedalus.hearthjaw-copy-inspection.v2", operation_intent="hearthjaw-camera-r2",
        state="ONE_COPY_INSPECTION_RENDER_RETURNED_FINISHED", before_fields=copy.deepcopy(fields), after_fields=fields,
        terminal_fields=copy.deepcopy(fields), actual_bounds_after=bounds, actual_quality=quality, actual_inventory=inventory,
        presentation_after=dict(conditions=presentation))
    plan = COLOR.make_plan(recipe, historical, docs)
    state = dict(color=COLOR, old=OLD, recipe=recipe, historical=historical, plan=plan, uid_paths=M.uid_paths(fields, recipe),
                 caller=SOURCE, self_sha256=M.digest(SOURCE.read_bytes()), sibling_pins=[])
    fresh = copy.deepcopy(fields)
    for path in state["uid_paths"]:
        node = fresh
        for key in path[:-1]: node = node[key]
        node[path[-1]] += 1000
    before = dict(fields=fresh, bounds=copy.deepcopy(bounds), quality=copy.deepcopy(quality), inventory=copy.deepcopy(inventory),
                  presentation=copy.deepcopy(presentation), extra=dict(uv=[[0, 0]], normal=[[0, 0, 1]], geometry="full-unchanged"))
    return state, before


def change_colors(fields, plan):
    after = copy.deepcopy(fields)
    for e in plan["edits"]:
        mat = after["materials"][e["binding"]["material"]]
        mat["fields"]["diffuse_color"] = e["proposed_linear_rgba"][:]
        mat["nodes"]["nodes"][0]["inputs"][0][1] = e["proposed_linear_rgba"][:]
    return after


class Socket:
    def __init__(self, row): self.row, self.is_linked, self.writes = row, False, 0
    @property
    def default_value(self): return self.row["nodes"]["nodes"][0]["inputs"][0][1]
    @default_value.setter
    def default_value(self, value): self.writes += 1; self.row["nodes"]["nodes"][0]["inputs"][0][1] = list(value)


class Material:
    def __init__(self, name, row):
        self.name, self.row = name, row; self.users=1; self.use_fake_user=False; self.use_extra_user=False
        self.library=None; self.is_editable=True; self.animation_data=None; self.socket=Socket(row)
        self.node_tree=NS(library=None, animation_data=None, nodes={"Principled BSDF":NS(inputs={"Base Color":self.socket})})
    @property
    def diffuse_color(self): return self.row["fields"]["diffuse_color"]
    @diffuse_color.setter
    def diffuse_color(self, value): self.row["fields"]["diffuse_color"] = list(value)


def live_fake(before):
    mats = {name:Material(name, row) for name, row in before["fields"]["materials"].items()}
    objects = {}
    for i, slots in enumerate(SLOTS):
        name="Display_Prop_Eco_sky_hearthjaw_G%d" % i
        objects[name]=NS(name=name,type="MESH",data=NS(materials=[mats[n] for n in slots]),
                         material_slots=[NS(link="DATA",material=mats[n]) for n in slots])
    scene=NS(objects=objects,render=NS(filepath="original-R2.png"),name="Scene")
    return NS(context=NS(scene=scene,view_layer=NS(update=lambda:None)),data=NS(objects=list(objects.values()),filepath=""),
              app=NS(background=True,version=(4,3,1),autoexec_fail=False)),mats


class AdapterContracts(unittest.TestCase):
    def test_bootstrap_without_script_directory_and_no_cache_imports(self):
        original=[p for p in sys.path if p != str(SOURCE.parent.resolve())]
        with mock.patch.object(sys,"path",original[:]):
            s=subject();self.assertEqual(str(SOURCE.parent.resolve()),sys.path[0])
            color,old,raw=s.dependencies(SOURCE)
            self.assertTrue(callable(color.load_plan));self.assertTrue(callable(old.collect));self.assertEqual(4,len(raw))

    def test_sibling_pin_mismatch_precedes_code_execution(self):
        with mock.patch.object(Path,"read_bytes",return_value=b"changed"), mock.patch.object(M,"load_source",side_effect=AssertionError("executed")):
            with self.assertRaisesRegex(ValueError,"pin differs"):M.dependencies(SOURCE)

    def test_exact_25_declared_uid_changes_only_between_sessions(self):
        state,before=fixture();historical=copy.deepcopy(state["historical"]);plan,rows=M.admit_fresh(state,before)
        self.assertEqual(25,len(rows));self.assertTrue(all(x["fresh"]-x["historical"]==1000 for x in rows))
        self.assertEqual(historical,state["historical"]);self.assertNotEqual(plan["protected_scene_sha256"],state["plan"]["protected_scene_sha256"])
        self.assertEqual(state["plan"]["palette_linear_rgba"],plan["palette_linear_rgba"])

    def test_no_generic_uid_stripping_missing_duplicate_or_unknown_refused(self):
        for kind in ("unknown","missing","duplicate","bool"):
            state,before=fixture();f=before["fields"]
            if kind=="unknown":f["view"]["session_uid"]=9000
            if kind=="missing":del f["world"]["fields"]["session_uid"]
            if kind=="duplicate":f["world"]["fields"]["session_uid"]=f["materials"][SLOTS[0][0]]["fields"]["session_uid"]
            if kind=="bool":f["world"]["fields"]["session_uid"]=True
            with self.subTest(kind=kind),self.assertRaises(ValueError):M.admit_fresh(state,before)

    def test_historical_unknown_tag_shader_ui_or_geometry_difference_holds(self):
        for kind in ("tag","node-ui","shader","world","geometry","color"):
            state,before=fixture();f=before["fields"]
            if kind=="tag":f["world"]["fields"]["tag"]=True
            if kind=="node-ui":f["materials"][SLOTS[0][0]]["nodes"]["nodes"][0]["fields"]["dimensions"]=[2,2]
            if kind=="shader":f["materials"][SLOTS[0][0]]["nodes"]["nodes"][0]["inputs"][2][1]=.4
            if kind=="world":f["world"]["fields"]["strength"]=1
            if kind=="geometry":f["objects"][1]["geometry_sha256"]="changed"
            if kind=="color":f["materials"][SLOTS[0][0]]["fields"]["diffuse_color"]=[1,1,1,1]
            with self.subTest(kind=kind),self.assertRaisesRegex(ValueError,"non-UID"):M.admit_fresh(state,before)

    def test_fixed_historical_camera_quality_inventory_presentation_refused(self):
        for key in ("bounds","quality","inventory","presentation"):
            state,before=fixture();before[key]={"changed":True}
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,"fixed R2"):M.admit_fresh(state,before)

    def test_same_process_retains_uids_and_uv_normal_geometry_protection(self):
        state,before=fixture();plan,_=M.admit_fresh(state,before);after=copy.deepcopy(before);after["fields"]=change_colors(before["fields"],plan)
        M.verify_after(state,before,after,plan)
        for kind in ("uid","uv","normal","camera","emission"):
            bad=copy.deepcopy(after)
            if kind=="uid":bad["fields"]["world"]["fields"]["session_uid"]+=1
            if kind in ("uv","normal"):bad["extra"][kind]=[[.2,.3,.4]]
            if kind=="camera":bad["bounds"]["camera"]["ortho_scale"]=24
            if kind=="emission":bad["fields"]["materials"][SLOTS[0][0]]["nodes"]["nodes"][0]["inputs"][-1][1]=8
            with self.subTest(kind=kind),self.assertRaises(ValueError):M.verify_after(state,before,bad,plan)

    def test_extra_collector_records_uv_and_normals_and_refuses_unreadable_attribute(self):
        def rna(**values):
            obj=NS(**values)
            obj.bl_rna=NS(properties=[NS(identifier=k,type="FLOAT" if isinstance(v,list) else "INT" if type(v)is int else "STRING") for k,v in values.items()])
            return obj
        uv=rna(vector=[.1,.2]);vertex=rna(co=[0,0,0],normal=[0,0,1])
        mesh=rna(name="PlantMesh",session_uid=51);mesh.vertices=[vertex];mesh.edges=[rna(vertices=[0,0])]
        mesh.loops=[rna(vertex_index=0)];mesh.polygons=[rna(vertices=[0,0,0],material_index=0)]
        mesh.attributes=[NS(name="UVMap",data_type="FLOAT2",domain="CORNER",data=[uv])]
        obj=rna(name="Plant",type="MESH");obj.data=mesh;obj.matrix_world=[[1,0,0,0]];obj.material_slots=[]
        bpy=NS(context=NS(scene=NS(objects=[obj])))
        first=M.extra_witness(bpy,OLD);self.assertEqual([0,0,1],first["Plant"]["mesh"]["vertices"][0]["normal"])
        self.assertEqual([.1,.2],first["Plant"]["mesh"]["attributes"][0]["data"][0]["vector"])
        uv.vector=[.3,.4];vertex.normal=[0,1,0]
        self.assertNotEqual(first,M.extra_witness(bpy,OLD))
        mesh.attributes[0].data=[NS(bl_rna=NS(properties=[]))]
        with self.assertRaisesRegex(ValueError,"attribute serialization"):M.extra_witness(bpy,OLD)

    def test_all_17_references_validate_before_any_setter(self):
        state,before=fixture();bpy,mats=live_fake(before);targets=M.material_targets(bpy,state,before)
        self.assertEqual(17,len(targets));self.assertEqual(0,sum(m.socket.writes for m in mats.values()))
        mats[SLOTS[-1][-1]].users=2
        with self.assertRaisesRegex(ValueError,"shared"):M.material_targets(bpy,state,before)
        self.assertEqual(0,sum(m.socket.writes for m in mats.values()))

    def test_nonplant_object_linked_socket_and_object_slot_override_hold(self):
        for kind in ("foreign","linked","slot","animation"):
            state,before=fixture();bpy,mats=live_fake(before);mat=mats[SLOTS[0][0]]
            if kind=="foreign":bpy.data.objects.append(NS(name="Floor",material_slots=[NS(material=mat)]))
            if kind=="linked":mat.socket.is_linked=True
            if kind=="slot":next(iter(bpy.context.scene.objects.values())).material_slots[0].link="OBJECT"
            if kind=="animation":mat.node_tree.animation_data=object()
            with self.subTest(kind=kind),self.assertRaises(ValueError):M.material_targets(bpy,state,before)
            self.assertEqual(0,sum(m.socket.writes for m in mats.values()))

    def test_launch_requires_all_exact_fields_and_cannot_create_authority(self):
        state,_=fixture();args=NS(self_sha256=state["self_sha256"],operation=M.INTENT,grant_id=999999)
        M.require_launch(M.launch_prefix(SOURCE),state,args)
        for key,value in (("self_sha256","wrong"),("operation","hearthjaw-camera-r2"),("grant_id",None),("grant_id",0)):
            bad=copy.copy(args);setattr(bad,key,value)
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):M.require_launch(M.launch_prefix(SOURCE),state,bad)
        with self.assertRaises(ValueError):M.require_launch(["--background"],state,args)

    def test_literal_output_parent_and_consumed_partial_root(self):
        with tempfile.TemporaryDirectory() as temp,mock.patch.object(M,"ROOT",Path(temp)/M.INTENT):
            paths=M.paths_for(OLD);self.assertEqual(Path(temp)/M.INTENT,paths["root"])
            paths["root"].mkdir();(paths["root"]/"partial").write_bytes(b"retained")
            with self.assertRaisesRegex(ValueError,"consumed/no replay"):M.paths_for(OLD)
            self.assertEqual(b"retained",(paths["root"]/"partial").read_bytes())

    def test_default_import_cli_has_no_app_process_network_or_writes(self):
        state,_=fixture();state["paths"]={"root":M.ROOT};output=io.StringIO();real_import=builtins.__import__
        def guarded(name,*args,**kwargs):
            if name.split(".")[0] in {"bpy","mathutils","subprocess","socket","http","urllib","requests"}:raise AssertionError("forbidden import")
            return real_import(name,*args,**kwargs)
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch("builtins.__import__",side_effect=guarded));s=subject()
            stack.enter_context(mock.patch.object(s,"preflight",return_value=state));stack.enter_context(mock.patch.object(s,"execute_copy",side_effect=AssertionError("app")))
            for name in ("open","mkdir","write_bytes","write_text","unlink","rename","replace"):
                stack.enter_context(mock.patch.object(Path,name,side_effect=AssertionError("write")))
            with contextlib.redirect_stdout(output):self.assertEqual(0,s.main([]))
        result=json.loads(output.getvalue());self.assertEqual(0,result["app_calls"]);self.assertEqual(0,result["output_writes"])
        self.assertFalse(result["execution_authorized"]);self.assertIsNone(result["fresh_session_compatibility"])
        self.assertTrue(all(v is None for v in result["actual"].values()))

    def test_execute_flags_fail_before_bpy_when_missing_launch_or_sha(self):
        state,_=fixture();state["paths"]={"root":M.ROOT}
        for args in (["--execute"],["--execute","--self-sha256","bad"],["--grant-id","123"],["--output","old"]):
            with self.subTest(args=args),mock.patch.object(M,"preflight",return_value=state),mock.patch.object(M,"execute_copy",side_effect=AssertionError("app")),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(2,M.main(args))

    def runtime_fixture(self,root,cancel=False,mutate=False):
        state,before=fixture();bpy,mats=live_fake(before);state["paths"]={"root":root/"fresh"}
        state["paths"].update(copy=root/"fresh/R2-input-copy.blend",scene=root/"fresh/new.blend",image=root/"fresh/new.png",receipt=root/"fresh/receipt.json")
        source=root/"source.blend";source.write_bytes(b"synthetic scene, never Blender")
        pin=dict(path=str(source),bytes=source.stat().st_size,sha256=M.digest(source.read_bytes()))
        state["recipe"]["inputs"]={"scene":pin};state["recipe"]["source_pins"]=[]
        for stage in state["recipe"]["stages"]:stage["glb"]=pin
        events=[]
        def opened(**kw):events.append(("open",kw));bpy.data.filepath=kw["filepath"];return {"FINISHED"}
        op=mock.Mock(side_effect=opened);op.get_rna_type.return_value=NS(properties=dict.fromkeys(["filepath","load_ui","use_scripts"]))
        def saved(**kw):events.append(("save",kw));Path(kw["filepath"]).write_bytes(b"synthetic saved scene");bpy.data.filepath=kw["filepath"];return {"FINISHED"}
        def rendered(**kw):
            events.append(("render",kw))
            if cancel:return {"CANCELLED"}
            if mutate:before["extra"]["uv"]=[[.9,.9]]
            state["paths"]["image"].write_bytes(b"\x89PNG\r\n\x1a\n"+struct.pack(">I",13)+b"IHDR"+struct.pack(">II",1800,1400)+b"\0"*9)
            return {"FINISHED"}
        bpy.ops=NS(wm=NS(open_mainfile=op,save_as_mainfile=mock.Mock(side_effect=saved)),render=NS(render=mock.Mock(side_effect=rendered)))
        return state,before,bpy,mats,events,source

    def test_mocked_one_copy_save_render_and_exact_17_color_setters(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);state,before,bpy,mats,events,source=self.runtime_fixture(root)
            def snap(*_):return copy.deepcopy(before)
            with mock.patch.dict(sys.modules,{"bpy":bpy}),mock.patch.object(M,"preflight",return_value=state),mock.patch.object(M,"snapshot",side_effect=snap):
                result=M.execute_copy(state,123)
                self.assertEqual("ONE_COPY_COLOR_SAVE_MATCHED_RENDER_RETURNED_FINISHED",result["state"])
                self.assertEqual(["open","save","render"],[x[0] for x in events]);self.assertEqual(17,sum(m.socket.writes for m in mats.values()))
                self.assertEqual(False,events[0][1]["use_scripts"]);self.assertEqual(False,events[0][1]["load_ui"])
                self.assertEqual(b"synthetic scene, never Blender",source.read_bytes())
                receipt=json.loads(state["paths"]["receipt"].read_text());self.assertFalse(receipt["image_quality_accepted"]);self.assertIsNone(receipt["process_exit_code"])
                retained={p.name:p.read_bytes() for p in state["paths"]["root"].iterdir()};bpy.data.filepath=""
                with self.assertRaises(FileExistsError):M.execute_copy(state,123)
                self.assertEqual(retained,{p.name:p.read_bytes() for p in state["paths"]["root"].iterdir()})

    def test_cancelled_render_or_protected_change_retains_partial_without_success(self):
        for cancel,mutate in ((True,False),(False,True)):
            with self.subTest(cancel=cancel,mutate=mutate),tempfile.TemporaryDirectory() as temp:
                state,before,bpy,mats,events,source=self.runtime_fixture(Path(temp),cancel,mutate)
                with mock.patch.dict(sys.modules,{"bpy":bpy}),mock.patch.object(M,"preflight",return_value=state),mock.patch.object(M,"snapshot",side_effect=lambda *_:copy.deepcopy(before)):
                    with self.assertRaises(ValueError):M.execute_copy(state,123)
                self.assertTrue(state["paths"]["scene"].exists());self.assertTrue((state["paths"]["root"]/"failure.json").exists())
                self.assertFalse(state["paths"]["receipt"].exists());self.assertEqual(b"synthetic scene, never Blender",source.read_bytes())

    def test_unknown_safe_open_rna_refuses_before_output_or_operator(self):
        with tempfile.TemporaryDirectory() as temp:
            state,before,bpy,mats,events,source=self.runtime_fixture(Path(temp))
            bpy.ops.wm.open_mainfile.get_rna_type.return_value=NS(properties={"filepath":None})
            with mock.patch.dict(sys.modules,{"bpy":bpy}),self.assertRaisesRegex(ValueError,"safe-open RNA"):M.execute_copy(state,123)
            self.assertFalse(state["paths"]["root"].exists());self.assertFalse(events)

    def test_final_receipt_write_failure_keeps_attempt_and_actual_partial_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            state,before,bpy,mats,events,source=self.runtime_fixture(Path(temp));real=M.durable
            def fail_receipt(path,value):
                if path==state["paths"]["receipt"]:raise OSError("synthetic receipt write failure")
                return real(path,value)
            with mock.patch.dict(sys.modules,{"bpy":bpy}),mock.patch.object(M,"preflight",return_value=state),mock.patch.object(M,"snapshot",side_effect=lambda *_:copy.deepcopy(before)),mock.patch.object(M,"durable",side_effect=fail_receipt):
                with self.assertRaisesRegex(OSError,"receipt write failure"):M.execute_copy(state,123)
            self.assertEqual(1,sum(x[0]=="render" for x in events));self.assertTrue(state["paths"]["image"].exists())
            self.assertTrue((state["paths"]["root"]/"attempt.json").exists());self.assertTrue((state["paths"]["root"]/"failure.json").exists())
            self.assertFalse(state["paths"]["receipt"].exists());self.assertEqual(b"synthetic scene, never Blender",source.read_bytes())


if __name__ == "__main__":
    unittest.main()
