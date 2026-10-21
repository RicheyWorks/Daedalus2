"""Small fake-boundary tests. No Unreal import, source exporter, editor or build."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import types
import unittest
from unittest.mock import patch

import finishline_target_operations as op
import finishline_target_policy as p


def config():
    return p.parse_json((Path(__file__).parent/"fixtures/daedalus_finishline_targets_r2_20261021.json").read_bytes())


def facts(cfg):
    return {"schema":p.FACTS_SCHEMA,"contract_sha256":p.fingerprint(cfg),"capture_id":"synthetic-ops-before",
            "reader_sha256":"a"*64,"policy_sha256":"b"*64,
            "observation":{"phase":"preflight","unit_id":None,"operation_id":None,"package_overrides":{}},
            "world":dict(cfg["world"],state="OBSERVED",partitioned=False),
            "meshes":[dict(x,state="OBSERVED",lods=[{"index":0,"triangles":2,"vertices":4,
                "screen_size":2.0,"build_settings":{k:False for k in p.BUILD_FIELDS}}]) for x in cfg["meshes"]],
            "pcg":{"graph":{"state":"UNKNOWN"},"component":{"state":"UNKNOWN"}},
            "hlod":{"state":"UNKNOWN"},"release":dict(cfg["release"],state="OBSERVED"),"errors":[]}


def glb(points,triangles,name="Floor",material=None):
    positions=b"".join(struct.pack("<fff",*x) for x in points)
    indices=struct.pack("<"+"H"*len(triangles),*triangles)
    binary=positions+indices; binary+=b"\0"*((-len(binary))%4)
    doc={"asset":{"version":"2.0"},"buffers":[{"byteLength":len(binary)}],
         "bufferViews":[{"buffer":0,"byteOffset":0,"byteLength":len(positions)},
                        {"buffer":0,"byteOffset":len(positions),"byteLength":len(indices)}],
         "accessors":[{"bufferView":0,"componentType":5126,"count":len(points),"type":"VEC3"},
                      {"bufferView":1,"componentType":5123,"count":len(triangles),"type":"SCALAR"}],
         "materials":[material or {"name":"Stone","pbrMetallicRoughness":{"metallicFactor":0}}],
         "nodes":[{"name":name,"mesh":0}],"meshes":[{"primitives":[{"attributes":{"POSITION":0},"indices":1,"material":0}]}]}
    js=p.canonical(doc); js+=b" "*((-len(js))%4)
    return struct.pack("<III",0x46546C67,2,28+len(js)+len(binary))+struct.pack("<II",len(js),0x4E4F534A)+js+struct.pack("<II",len(binary),0x004E4942)+binary


def lod_case():
    cfg=config(); before=facts(cfg)
    base=glb([(0,0,0),(1,0,0),(1,1,0),(0,1,0)],[0,1,2,0,2,3])
    reduced=glb([(0,0,0),(1,0,0),(1,1,0)],[0,1,2])
    lineage=op.inspect_lod_exports(base,reduced,"Floor")
    request={"mesh_id":cfg["meshes"][0]["id"],"source":{"base_file":"synthetic-base.glb",
             "lod1_file":"synthetic-lod1.glb","base_sha256":lineage["base_sha256"],
             "lod1_sha256":lineage["lod1_sha256"]},"lineage":lineage}
    cfg["source_exports"]=dict(request["source"])
    cfg["units"][p.UNITS[0]]["desired_policy"]={"kind":"authored_lod_pair","mesh_id":request["mesh_id"],
        "lod1_source_sha256":lineage["lod1_sha256"],"lod1_triangles":1,"lod1_vertices":3,
        "screen_sizes":[2.0,0.4],"lod1_build_settings":{k:False for k in p.BUILD_FIELDS}}
    before["contract_sha256"]=p.fingerprint(cfg)
    return cfg,before,request,{"synthetic-base.glb":base,"synthetic-lod1.glb":reduced}


class Obj:
    def __init__(self,path,cls,outer=None):self.path=path;self.cls=cls;self.outer=outer;self.props={}
    def get_path_name(self):return self.path
    def get_class(self):return types.SimpleNamespace(get_path_name=lambda:self.cls)
    def get_outer(self):return self.outer
    def get_editor_property(self,k):return self.props[k]
    def set_editor_property(self,k,v):self.props[k]=v


def fake_world(cfg):
    world=Obj(cfg["world"]["object_path"],cfg["world"]["class_path"])
    ue=types.SimpleNamespace(UnrealEditorSubsystem="world",StaticMeshEditorSubsystem="mesh",PCGVolume="volume",PCGComponent="component")
    ue.get_editor_subsystem=lambda _:types.SimpleNamespace(get_editor_world=lambda:world)
    return ue,world


def pcg_case():
    cfg=config();cfg["pcg"]["component_path"]=cfg["world"]["object_path"]+":PersistentLevel.BoundVolume.PCGComponent"
    cfg["pcg"]["expected_output_sha256"]="d"*64; before=facts(cfg);ue,world=fake_world(cfg)
    actor=Obj(world.path+":PersistentLevel.BoundVolume","/Script/PCG.PCGVolume",world)
    actor.get_actor_label=lambda create: "PYTH_PCG_Ecology" if create is False else (_ for _ in ()).throw(AssertionError("Creating label"))
    actor.actor_has_tag=lambda tag:tag=="PYTH_Eco"
    graph=Obj(cfg["pcg"]["graph_path"],cfg["pcg"]["graph_class"])
    component=Obj(cfg["pcg"]["component_path"],cfg["pcg"]["component_class"],actor);component.props["seed"]=42
    component.get_owner=lambda:actor;component.get_graph=lambda:graph
    component.local_calls=[];component.generate_local=lambda force:component.local_calls.append(force)
    component.generate=lambda _:(_ for _ in ()).throw(AssertionError("Network call"))
    actor.get_component_by_class=lambda _:component
    ue.GameplayStatics=types.SimpleNamespace(get_all_actors_of_class=lambda *_:[actor])
    old=Obj("/Engine/BasicShapes/Cube.Cube","/Script/Engine.StaticMesh")
    new=Obj(cfg["meshes"][0]["object_path"],"/Script/Engine.StaticMesh")
    settings=Obj(graph.path+":Node.Settings","/Script/PCG.PCGStaticMeshSpawnerSettings",graph)
    node=Obj(graph.path+":Node","/Script/PCG.PCGNode",graph);node.get_settings=lambda:settings
    graph.props["nodes"]=[node]
    selector=Obj(graph.path+":Node.Settings.Selector","/Script/PCG.PCGMeshSelectorWeighted",settings)
    descriptor=Obj("descriptor","struct");descriptor.props["static_mesh"]=old
    entry=Obj("entry","struct");entry.props.update(descriptor=descriptor,weight=7)
    selector.props["mesh_entries"]=[entry]
    settings.props["mesh_selector_parameters"]=selector
    objects={x.path:x for x in (actor,component,graph,selector,new)};ue.find_object=lambda _,path:objects.get(path)
    before["pcg"]={"graph":dict(object_path=graph.path,class_path=graph.cls,state="OBSERVED",asset_file_sha256=cfg["pcg"]["graph_file_sha256"]),
        "component":dict(object_path=component.path,class_path=component.cls,state="OBSERVED",world_path=world.path,graph_path=graph.path,seed=42)}
    request={"node_path":node.path,"settings_path":settings.path,
             "selector_path":selector.path,"selector_class":selector.cls,"entry_index":0,
             "before_mesh_path":old.path,"after_mesh_path":new.path,
             "soft_read_admission":{"selector_path":selector.path,"entry_index":0,
                                    "may_load_current_target_and_dependencies":True}}
    return cfg,before,request,ue,actor,component,selector,entry


def pcg_completion_case(changed=True):
    """Declared synthetic referenced proof, never a native success receipt."""
    cfg,before,request,*_=pcg_case(); unit=p.UNITS[1]; operation="synthetic-pcg"
    plan=op.prepare_operation(cfg,before,operation,op.KINDS[1],request)
    after=copy.deepcopy(before);after["capture_id"]="synthetic-ops-after"
    saved="e"*64 if changed else before["pcg"]["graph"]["asset_file_sha256"]
    after["pcg"]["graph"]["asset_file_sha256"]=saved
    after["observation"]={"phase":"reopen","unit_id":unit,"operation_id":operation,
                          "package_overrides":{"pcg_graph":saved}}
    completion={"unit_id":unit,"target_id":cfg["units"][unit]["target_id"],"operation_id":operation,
                "contract_sha256":p.fingerprint(cfg),"before_sha256":p.fingerprint(before),
                "after_sha256":p.fingerprint(after),"plan_sha256":p.fingerprint(plan),
                "changed":True,"observed_output_count":1,"generated_by_pcg":True,"manual_fallback":False,
                "observed_output_sha256":"d"*64,"repeat_seed_output_sha256":"d"*64,
                "descriptor_mesh_paths":cfg["pcg"]["descriptor_mesh_paths"]}
    for stage in ("operation","save","reopen","consumer"):
        completion[stage]={"unit_id":unit,"target_id":cfg["units"][unit]["target_id"],
                           "operation_id":operation,"completed":True,"receipt_sha256":"c"*64,
                           "record_path":"$.synthetic."+stage}
    change={k:request[k] for k in ("node_path","settings_path","selector_path","entry_index",
                                  "before_mesh_path","after_mesh_path")}
    change.update(completed=True,operation_id=operation,plan_sha256=p.fingerprint(plan),
                  receipt_sha256="f"*64,record_path="$.synthetic.descriptor_change",
                  saved_graph_sha256=saved,reopened_graph_sha256=saved)
    completion["descriptor_change"]=change
    return cfg,before,after,plan,completion


class FiniteOperationTests(unittest.TestCase):
    def test_source_component_lineage_is_not_whole_assembly_count(self):
        _,_,request,_=lod_case();lineage=request["lineage"]
        self.assertEqual((lineage["base_triangles"],lineage["lod1_triangles"]),(2,1))
        self.assertFalse(lineage["native_mapping_observed"])

    def test_outside_component_material_and_nonreduction_are_rejected(self):
        _,_,_,raw=lod_case();base=raw["synthetic-base.glb"]
        for bad in (glb([(5,0,0),(6,0,0),(6,1,0)],[0,1,2]),base,
                    glb([(0,0,0),(1,0,0),(1,1,0)],[0,1,2],material={"name":"Changed"})):
            with self.assertRaises(p.ContractError):op.inspect_lod_exports(base,bad,"Floor")
        with self.assertRaises(p.ContractError):op.inspect_lod_exports(base,raw["synthetic-lod1.glb"],"Unknown")

    def test_float32_submicrometre_offset_does_not_become_exact_source_membership(self):
        _,_,_,raw=lod_case()
        displaced=glb([(1e-7,0,0),(1,0,0),(1,1,0)],[0,1,2])
        with self.assertRaises(p.ContractError):op.inspect_lod_exports(raw["synthetic-base.glb"],displaced,"Floor")

    def test_pcg_binding_reads_label_without_creating_and_preserves_actual_seed(self):
        cfg,_,_,ue,_,_,_,_=pcg_case();row=op.bind_pcg_target(cfg,unreal_module=ue)
        self.assertEqual(row["layout_seed"],7);self.assertEqual(row["actual_component_seed"],42)

    def test_pcg_binding_rejects_ambiguity_foreign_world_and_unbounded_lookup(self):
        cfg,_,_,ue,actor,_,_,_=pcg_case()
        for actors in ([actor,actor],[actor]*32769,[]):
            ue.GameplayStatics.get_all_actors_of_class=lambda *_,rows=actors:rows
            with self.assertRaises(p.ContractError):op.bind_pcg_target(cfg,unreal_module=ue)
        ue.GameplayStatics.get_all_actors_of_class=lambda *_:[actor]
        actor.outer=Obj("/Game/Other.Other","/Script/Engine.World")
        with self.assertRaises(p.ContractError):op.bind_pcg_target(cfg,unreal_module=ue)

    def test_lod_dispatch_has_one_call_and_cannot_claim_async_completion(self):
        cfg,before,request,raw=lod_case();plan=op.prepare_operation(cfg,before,"synthetic-op",op.KINDS[0],request)
        ue,_=fake_world(cfg);row=before["meshes"][0];obj=Obj(row["object_path"],row["class_path"])
        obj.get_num_triangles=lambda _:2;obj.get_num_vertices=lambda _:4
        ue.find_object=lambda *_:obj;calls=[]
        subsystem=types.SimpleNamespace(get_lod_count=lambda _:1,get_lod_screen_sizes=lambda _:[2.0],
            get_lod_build_settings=lambda *_:types.SimpleNamespace(get_editor_property=lambda _:False),
            import_lod=lambda *args:calls.append(args) or 1)
        original=ue.get_editor_subsystem;ue.get_editor_subsystem=lambda kind:subsystem if kind=="mesh" else original(kind)
        with patch.object(op,"_asset_pin"):
            result=op.dispatch_operation(cfg,before,plan,p.fingerprint(plan),unreal_module=ue,source_reader=raw.__getitem__)
        self.assertEqual(len(calls),1);self.assertFalse(result["completed"]);self.assertFalse(result["adopted"])
        self.assertEqual(op.qualify_referenced_operation(cfg,before,before,plan,result)["state"],"HELD")

    def test_changed_source_or_native_pin_stops_before_mutation(self):
        cfg,before,request,raw=lod_case();plan=op.prepare_operation(cfg,before,"synthetic-op",op.KINDS[0],request)
        class NoCalls:
            def __getattr__(self,_):raise AssertionError("No native access for changed admission")
        with self.assertRaises(p.ContractError):op.dispatch_operation(cfg,before,plan,"0"*64,unreal_module=NoCalls())
        ue,_=fake_world(cfg)
        with patch.object(op,"_asset_pin",side_effect=p.ContractError("Changed package")):
            with self.assertRaises(p.ContractError):op.dispatch_operation(cfg,before,plan,p.fingerprint(plan),unreal_module=ue,source_reader=raw.__getitem__)

    def test_pcg_descriptor_delta_uses_local_generation_and_preserves_weight_seed(self):
        cfg,before,request,ue,_,component,selector,entry=pcg_case()
        plan=op.prepare_operation(cfg,before,"synthetic-pcg",op.KINDS[1],request)
        with patch.object(op,"_asset_pin"):
            result=op.dispatch_operation(cfg,before,plan,p.fingerprint(plan),unreal_module=ue)
        self.assertEqual(component.local_calls,[True]);self.assertEqual(component.props["seed"],42)
        self.assertEqual(entry.props["weight"],7)
        self.assertEqual(selector.props["mesh_entries"][0].props["descriptor"].props["static_mesh"].path,request["after_mesh_path"])
        self.assertEqual(result["observed_return"]["soft_descriptor_read_effect"]["entry_index"],0)
        self.assertFalse(result["completed"])

    def test_soft_property_loading_effect_must_be_explicitly_admitted_before_native_access(self):
        for bad in (None,{"selector_path":"/Game/Other.Other","entry_index":0,
                          "may_load_current_target_and_dependencies":True}):
            cfg,before,request,*_=pcg_case();request["soft_read_admission"]=bad
            with self.assertRaises(p.ContractError):op.prepare_operation(cfg,before,"synthetic-pcg",op.KINDS[1],request)

    def test_bind_and_generate_cannot_qualify_an_unchanged_saved_graph(self):
        cfg,before,after,plan,completion=pcg_completion_case(changed=False)
        self.assertEqual(p.qualify(cfg,before,after,completion)["state"],"QUALIFIED_REFERENCED_EVIDENCE")
        self.assertEqual(op.qualify_referenced_operation(cfg,before,after,plan,completion)["state"],"HELD")

    def test_descriptor_change_receipt_must_bind_exact_operation_entry_and_saved_reopen(self):
        cfg,before,after,plan,completion=pcg_completion_case()
        result=op.qualify_referenced_operation(cfg,before,after,plan,completion)
        self.assertEqual(result["state"],"QUALIFIED_REFERENCED_EVIDENCE");self.assertFalse(result["adopted"])
        for field,value in (("operation_id","other-operation"),("node_path","/Game/Other.Other"),
                            ("entry_index",1),("entry_index",False),("before_mesh_path","/Engine/BasicShapes/Sphere.Sphere"),
                            ("after_mesh_path","/Game/Other.Other"),("saved_graph_sha256","0"*64),
                            ("reopened_graph_sha256","0"*64),("receipt_sha256",None)):
            bad=copy.deepcopy(completion);bad["descriptor_change"][field]=value
            self.assertEqual(op.qualify_referenced_operation(cfg,before,after,plan,bad)["state"],"HELD")
        bad=copy.deepcopy(completion);del bad["descriptor_change"]
        self.assertEqual(op.qualify_referenced_operation(cfg,before,after,plan,bad)["state"],"HELD")

    def test_pcg_unbound_expected_output_or_noop_descriptor_cannot_dispatch(self):
        cfg,before,request,*_=pcg_case()
        request["after_mesh_path"]=request["before_mesh_path"]
        with self.assertRaises(p.ContractError):op.prepare_operation(cfg,before,"synthetic-op",op.KINDS[1],request)
        cfg,before,request,*_=pcg_case();cfg["pcg"]["expected_output_sha256"]=None
        before["contract_sha256"]=p.fingerprint(cfg)
        with self.assertRaises(p.ContractError):op.prepare_operation(cfg,before,"synthetic-op",op.KINDS[1],request)

    def test_legacy_hlod_has_no_layer_requirement_but_unresolved_settings_hold(self):
        file=Path(__file__).parent/"fixtures/daedalus_finishline_targets_r3_20261021.json"
        cfg=p.parse_json(file.read_bytes());before=facts(cfg)
        self.assertIsNone(cfg["hlod"]["layer_path"]);self.assertIsNone(cfg["hlod"]["layer_class"])
        self.assertEqual(p.inspect(cfg,before)["units"][p.UNITS[2]]["state"],"PENDING")
        with self.assertRaises(p.ContractError):op.prepare_operation(cfg,before,"synthetic-hlod",op.KINDS[2],{})

    def test_lod_source_and_deliberate_policy_must_match_config_before_dispatch(self):
        for mismatch in ("source","policy"):
            cfg,before,request,_=lod_case()
            if mismatch=="source":request["source"]["lod1_file"]="unadmitted.glb"
            else:cfg["units"][p.UNITS[0]]["desired_policy"]=None;before["contract_sha256"]=p.fingerprint(cfg)
            with self.assertRaises(p.ContractError):op.prepare_operation(cfg,before,"synthetic-op",op.KINDS[0],request)

    def test_pcg_selector_must_be_owned_by_the_actual_admitted_graph_node(self):
        cfg,before,request,ue,_,component,_,_=pcg_case();plan=op.prepare_operation(cfg,before,"synthetic-pcg",op.KINDS[1],request)
        component.get_graph().props["nodes"]=[]
        with patch.object(op,"_asset_pin"):
            with self.assertRaises(p.ContractError):op.dispatch_operation(cfg,before,plan,p.fingerprint(plan),unreal_module=ue)
        self.assertEqual(component.local_calls,[])

    def test_imported_lod_finalizer_never_reimports_or_saves_and_requires_real_geometry(self):
        cfg,before,request,_=lod_case();plan=op.prepare_operation(cfg,before,"synthetic-op",op.KINDS[0],request)
        ue,_=fake_world(cfg);row=before["meshes"][0];obj=Obj(row["object_path"],row["class_path"])
        obj.get_num_triangles=lambda i:2 if i==0 else 1;obj.get_num_vertices=lambda i:4 if i==0 else 3
        ue.find_object=lambda *_:obj;state={"count":1,"screens":[2.0,0.5]}
        flags=[Obj("flags0","struct"),Obj("flags1","struct")]
        for item in flags:item.props={k:False for k in p.BUILD_FIELDS}
        sub=types.SimpleNamespace(get_lod_count=lambda _:state["count"],get_lod_build_settings=lambda _,i:flags[i],
            get_lod_screen_sizes=lambda _:state["screens"],set_lod_build_settings=lambda _,i,v:flags.__setitem__(i,v),
            set_lod_screen_sizes=lambda _,v:state.update(screens=v) or True)
        old=ue.get_editor_subsystem;ue.get_editor_subsystem=lambda k:sub if k=="mesh" else old(k)
        with patch.object(op,"_asset_pin"):
            with self.assertRaises(p.ContractError):op.apply_imported_lod_policy(cfg,before,plan,p.fingerprint(plan),unreal_module=ue)
            state["count"]=2
            result=op.apply_imported_lod_policy(cfg,before,plan,p.fingerprint(plan),unreal_module=ue)
        self.assertEqual(result["state"],"POLICY_APPLIED_UNSAVED");self.assertFalse(result["completed"])
        self.assertEqual(state["screens"],[2.0,0.4])


if __name__=="__main__":unittest.main()
