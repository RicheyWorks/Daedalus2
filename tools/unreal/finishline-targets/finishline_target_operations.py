"""Finite sole-operator operations, never executed at import or by source tests.

This is neither transport nor admission authority. The existing sole operator
admits exact source/plan pins and owns resource/save custody before calling it.
Dispatch is not completion, save, reopen, consumer acceptance or adoption.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import struct

import finishline_target_policy as p
from ue_finishline_target_facts import _id, _file_pin

KINDS = ("lod.import_authored", "pcg.bind_and_generate_local", "hlod.legacy_existing")
PLAN_SCHEMA = "daedalus.finishline-operation-plan/v1"
MAX_SOURCE_BYTES = 16777216


def _bytes(path):
    file = Path(path); before = file.stat()
    p.require(before.st_size <= MAX_SOURCE_BYTES, "Source export exceeds bound")
    raw = file.read_bytes(); after = file.stat()
    p.require(before.st_size == after.st_size == len(raw) and
              before.st_mtime_ns == after.st_mtime_ns, "Source changed during read")
    return raw


def _glb(raw):
    p.require(type(raw) is bytes and 20 <= len(raw) <= MAX_SOURCE_BYTES, "Invalid GLB size")
    magic, version, total = struct.unpack_from("<III", raw)
    p.require(magic == 0x46546C67 and version == 2 and total == len(raw), "Invalid GLB envelope")
    length, kind = struct.unpack_from("<II", raw, 12)
    p.require(kind == 0x4E4F534A and 20 + length + 8 <= len(raw), "Missing bounded GLB JSON/BIN")
    doc = p.parse_json(raw[20:20+length]); offset = 20+length
    size, kind = struct.unpack_from("<II", raw, offset)
    p.require(kind == 0x004E4942 and offset+8+size == len(raw), "Unexpected GLB chunks")
    return doc, raw[offset+8:]


def _positions(doc, binary, accessor):
    a = doc["accessors"][accessor]
    p.require(a.get("componentType") == 5126 and a.get("type") == "VEC3" and
              "sparse" not in a and p.integer(a.get("count"), 1, 1000000), "Unsupported POSITION accessor")
    view = doc["bufferViews"][a["bufferView"]]
    p.require(view.get("buffer", 0) == 0, "External GLB buffer unsupported")
    stride = view.get("byteStride", 12); start = view.get("byteOffset", 0)+a.get("byteOffset", 0)
    p.require(p.integer(stride, 12, 256) and start >= 0 and
              a.get("byteOffset", 0)+(a["count"]-1)*stride+12 <= view["byteLength"] and
              start+(a["count"]-1)*stride+12 <= len(binary), "POSITION outside buffer bounds")
    result = set()
    for i in range(a["count"]):
        pos = struct.unpack_from("<fff", binary, start+i*stride)
        p.require(all(math.isfinite(x) for x in pos), "Nonfinite source position")
        result.add(tuple(pos))  # Exact decoded float32 values, with no positional quantization.
    return result


def inspect_lod_exports(base_bytes, lod_bytes, base_node):
    """Bind the real component, not a whole-assembly catalog triangle count.

    Supports the retained identity-transform triangle GLBs only. Every LOD1
    position must belong to the chosen LOD0 component; no exporter is invoked.
    """
    base, binary = _glb(base_bytes); lod, lod_binary = _glb(lod_bytes)
    p.require(len(base.get("nodes", [])) <= 128 and len(lod.get("nodes", [])) <= 128,
              "Source node count exceeds bound")
    selected = [n for n in base["nodes"] if n.get("name") == base_node]
    p.require(len(selected) == 1 and "mesh" in selected[0], "Ambiguous source component")
    def geometry(doc, data, nodes):
        points=set(); triangles=0; vertices=0; materials=set()
        for n in nodes:
            p.require(not any(k in n for k in ("matrix", "translation", "rotation", "scale", "children")),
                      "Source transforms/hierarchy require an explicit authored mapping")
            p.require("mesh" in n, "Nonmesh source node")
            for primitive in doc["meshes"][n["mesh"]]["primitives"]:
                p.require(primitive.get("mode",4) == 4 and "indices" in primitive, "Triangle source required")
                count=doc["accessors"][primitive["indices"]]["count"]
                p.require(p.integer(count,3,3000000) and count % 3 == 0, "Invalid triangle index count")
                pos=primitive["attributes"]["POSITION"]
                index=doc["accessors"][primitive["indices"]]; view=doc["bufferViews"][index["bufferView"]]
                p.require(index.get("type")=="SCALAR" and index.get("componentType") in (5121,5123,5125) and
                          "sparse" not in index and view.get("buffer",0)==0 and "byteStride" not in view,
                          "Unsupported triangle indices")
                fmt,width={5121:("B",1),5123:("H",2),5125:("I",4)}[index["componentType"]]
                offset=view.get("byteOffset",0)+index.get("byteOffset",0)
                p.require(offset>=0 and index.get("byteOffset",0)+count*width<=view["byteLength"] and
                          offset+count*width<=len(data),"Index accessor outside buffer bounds")
                p.require(all(struct.unpack_from("<"+fmt,data,offset+i*width)[0]<doc["accessors"][pos]["count"]
                              for i in range(count)),"Triangle index outside vertex array")
                points.update(_positions(doc,data,pos)); triangles += count//3
                vertices += doc["accessors"][pos]["count"]
                material=doc["materials"][primitive["material"]]
                materials.add(p.fingerprint(material))
        return points,triangles,vertices,materials
    a,at,av,am=geometry(base,binary,selected); b,bt,bv,bm=geometry(lod,lod_binary,lod["nodes"])
    p.require(b and b.issubset(a), "LOD1 includes geometry outside the selected LOD0 component")
    p.require(0 < bt < at and bm.issubset(am), "No reduction or material identity changed")
    return {"base_sha256":hashlib.sha256(base_bytes).hexdigest(),
            "lod1_sha256":hashlib.sha256(lod_bytes).hexdigest(),"base_node":base_node,
            "base_triangles":at,"base_vertices":av,"lod1_triangles":bt,"lod1_vertices":bv,
            "source_mapping":"LOD1 identity-transform positions/materials are a subset of selected LOD0 component",
            "native_mapping_observed":False}


def _world(config, ue):
    world=ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
    p.require(_id(world) == {k:config["world"][k] for k in ("object_path","class_path")},
              "Different current world")
    return world


def _in_world(obj, config):
    seen=set()
    for _ in range(16):
        ident=_id(obj); p.require(ident["object_path"] not in seen,"Object outer cycle")
        seen.add(ident["object_path"])
        if ident["class_path"]==config["world"]["class_path"]:
            p.require(ident["object_path"]==config["world"]["object_path"],"Object belongs to different world")
            return
        obj=obj.get_outer()
    raise p.ContractError("Object world outer exceeds bound")


def _asset_pin(config,path,expected):
    p.require(path.startswith("/Game/") and ":" not in path,"Only exact project asset pins supported")
    file=Path(config["release"]["project_file"]).parent/"Content"/(path.split(".",1)[0][6:]+".uasset")
    p.require(_file_pin(file,33554432)==expected,"Native asset file changed since preflight")


def bind_pcg_target(config, *, unreal_module=None):
    """One class-scoped lookup; no default label creation, generation or writes."""
    p.validate_contract(config)
    if unreal_module is None:
        import unreal as unreal_module
    ue=unreal_module; world=_world(config,ue)
    actors=ue.GameplayStatics.get_all_actors_of_class(world,ue.PCGVolume)
    p.require(len(actors) <= 32768,"PCG actor lookup exceeds admitted bound")
    matches=[]
    for actor in actors:
        if actor.get_actor_label(False) != "PYTH_PCG_Ecology": continue
        _in_world(actor,config)
        p.require(actor.actor_has_tag("PYTH_Eco"),"Exact PCG label has unexpected tag")
        component=actor.get_component_by_class(ue.PCGComponent)
        p.require(_id(component)["class_path"] == config["pcg"]["component_class"],"Wrong PCG component class")
        p.require(component.get_owner() == actor and component.get_graph().get_path_name() ==
                  config["pcg"]["graph_path"],"Wrong PCG owner/graph binding")
        seed=component.get_editor_property("seed")
        p.require(p.integer(seed,-2147483648,2147483647),"Unobserved PCG component seed")
        matches.append({"actor_path":actor.get_path_name(),"component_path":component.get_path_name(),
                        "component_class":_id(component)["class_path"],"graph_path":config["pcg"]["graph_path"],
                        "actual_component_seed":seed,"layout_seed":config["pcg"].get("layout_seed",config["pcg"].get("seed")),
                        "world_path":world.get_path_name()})
    p.require(len(matches)==1,"PCG label binding is absent or ambiguous")
    return matches[0]


def prepare_operation(config, before, operation_id, kind, request):
    """Pure finite plan validation. Caller authority is outside this module."""
    config=p.parse_json(p.canonical(config)); request=p.parse_json(p.canonical(request))
    p.require(p.inspect(config,before)["state"]=="VALID_TARGET_FACTS","Invalid pre-operation facts")
    p.require(kind in KINDS and p.text(operation_id),"Unknown operation identity")
    if kind==KINDS[0]:
        mesh=[x for x in before["meshes"] if x.get("id")==request.get("mesh_id")]
        p.require(len(mesh)==1 and mesh[0].get("state")=="OBSERVED" and len(mesh[0]["lods"])==1,
                  "LOD operation requires one observed LOD0; unchanged reimport is not selected")
        source=request.get("source",{}); lineage=request.get("lineage",{})
        admitted=config.get("source_exports",{})
        p.require(all(source.get(k)==admitted.get(k) and source.get(k) is not None for k in
                      ("base_file","lod1_file","base_sha256","lod1_sha256")),"Source export is outside admitted config")
        p.require(all(p.text(source.get(k),512) for k in ("base_file","lod1_file")) and
                  all(p.sha(source.get(k)) for k in ("base_sha256","lod1_sha256")),"Missing actual source export pins")
        p.require(lineage.get("base_sha256")==source["base_sha256"] and
                  lineage.get("lod1_sha256")==source["lod1_sha256"] and
                  lineage.get("base_triangles")==mesh[0]["lods"][0]["triangles"] and
                  p.integer(lineage.get("lod1_triangles"),1,mesh[0]["lods"][0]["triangles"]-1),
                  "Authored component/native geometry mapping is unbound")
        desired=config["units"][p.UNITS[0]].get("desired_policy",{})
        p.require(isinstance(desired,dict) and desired.get("kind")=="authored_lod_pair" and
                  desired.get("mesh_id")==request["mesh_id"] and
                  desired.get("lod1_source_sha256")==source["lod1_sha256"] and
                  desired.get("lod1_triangles")==lineage["lod1_triangles"] and
                  desired.get("lod1_vertices")==lineage["lod1_vertices"],"Explicit authored LOD policy is unbound")
        screens=desired.get("screen_sizes",[]); flags=desired.get("lod1_build_settings",{})
        p.require(isinstance(screens,list) and len(screens)==2 and all(p.render_screen_size(x) for x in screens) and
                  screens[0]==mesh[0]["lods"][0]["screen_size"] and screens[0]>screens[1] and
                  set(flags)==set(p.BUILD_FIELDS) and all(type(x) is bool for x in flags.values()),
                  "LOD thresholds/build policy is unbound or changes original LOD0 threshold")
    elif kind==KINDS[1]:
        pcg=before["pcg"]; c=pcg["component"]
        p.require(c.get("state")=="OBSERVED" and pcg["graph"].get("state")=="OBSERVED" and
                  c.get("object_path")==config["pcg"]["component_path"],"Unbound PCG consumer")
        p.require(p.sha(config["pcg"].get("expected_output_sha256")),"Expected deterministic output not admitted")
        old_path=request.get("before_mesh_path","")
        valid_old=p.path(old_path) or (isinstance(old_path,str) and old_path.startswith("/Engine/BasicShapes/") and
                                      p.path(old_path.replace("/Engine/", "/Game/",1)))
        p.require(p.path(request.get("node_path")) and p.path(request.get("settings_path")) and
                  p.path(request.get("selector_path")) and p.path(request.get("selector_class")) and
                  p.integer(request.get("entry_index"),0,127) and valid_old and
                  request.get("after_mesh_path") in config["pcg"]["descriptor_mesh_paths"] and
                  request["before_mesh_path"] != request["after_mesh_path"],"No useful exact descriptor delta")
        p.require(request.get("selector_class")=="/Script/PCG.PCGMeshSelectorWeighted",
                  "Only source-grounded weighted selector supported")
        admission=request.get("soft_read_admission",{})
        p.require(isinstance(admission,dict) and admission.get("may_load_current_target_and_dependencies") is True and
                  p.integer(admission.get("entry_index"),0,127) and admission=={
            "selector_path":request["selector_path"],"entry_index":request["entry_index"],
            "may_load_current_target_and_dependencies":True},
            "Selected soft descriptor read/loading effect is not admitted")
    else:
        h=before["hlod"]
        p.require(config["hlod"].get("route")=="legacy_nonpartitioned" and
                  before["world"].get("partitioned") is False and h.get("state")=="OBSERVED",
                  "Existing nonpartitioned legacy cluster not bound")
        p.require(request.get("lod_actor_path")==h.get("lod_actor_path") and
                  request.get("source_actor_paths")==h.get("source_actor_paths") and
                  len(h.get("source_actor_paths",[]))>=2,"Wrong or empty legacy source set")
    result={"schema":PLAN_SCHEMA,"kind":kind,"operation_id":operation_id,
            "contract_sha256":p.fingerprint(config),"before_sha256":p.fingerprint(before),
            "adapter_sha256":_file_pin(__file__,p.MAX_BYTES),
            "policy_sha256":_file_pin(p.__file__,p.MAX_BYTES),"request":request,
            "state":"SOURCE_PLAN_READY","authority":"Existing sole operator admission only; hash is identity, not permission"}
    p.canonical(result); return result


def dispatch_operation(config,before,plan,admitted_plan_sha256,*,unreal_module=None,source_reader=None):
    """One admitted operation; no save/reopen, global build, fallback or retry.

    Calls can mutate in-memory native state when the sole operator invokes them.
    The admitted selected soft descriptor getter may synchronously load its
    current target and dependencies, even when comparison later rejects it.
    This is not a loaded-only operation or a zero-implicit-load guarantee.
    Any exception after dispatch must be reconciled by that operator, not retried.
    """
    p.require(p.fingerprint(plan)==admitted_plan_sha256,"Operation plan changed")
    expected=prepare_operation(config,before,plan["operation_id"],plan["kind"],plan["request"])
    p.require(expected==plan,"Operation source/prestate changed")
    if plan["kind"]==KINDS[2]:
        return {"operation_id":plan["operation_id"],"plan_sha256":admitted_plan_sha256,
                "state":"BLOCKED_NATIVE_SINGLE_CLUSTER_BRIDGE_UNBOUND","dispatched":False,
                "reason":"Legacy BuildMeshForLODActor is plain C++; shared proxy/package closure and asynchronous result binding require existing native-owner integration. No HLODLayer or global builder substituted.",
                "completed":False,"adopted":False}
    if unreal_module is None:
        import unreal as unreal_module
    ue=unreal_module; _world(config,ue); request=plan["request"]
    if plan["kind"]==KINDS[0]:
        raw=source_reader or _bytes; source=request["source"]
        lineage=inspect_lod_exports(raw(source["base_file"]),raw(source["lod1_file"]),request["lineage"]["base_node"])
        p.require(lineage==request["lineage"],"Source lineage changed")
        row=next(x for x in before["meshes"] if x.get("id")==request["mesh_id"])
        _asset_pin(config,row["object_path"],row["asset_file_sha256"])
        obj=ue.find_object(None,row["object_path"])
        p.require(_id(obj)=={k:row[k] for k in ("object_path","class_path")},"LOD target identity changed")
        subsystem=ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem)
        old=row["lods"][0]
        p.require(subsystem.get_lod_count(obj)==1 and obj.get_num_triangles(0)==lineage["base_triangles"] and
                  obj.get_num_vertices(0)==old["vertices"] and
                  list(subsystem.get_lod_screen_sizes(obj))==[old["screen_size"]] and
                  all(subsystem.get_lod_build_settings(obj,0).get_editor_property(k)==v
                      for k,v in old["build_settings"].items()),
                  "LOD native prestate changed")
        returned=subsystem.import_lod(obj,1,source["lod1_file"])
        result={"returned_lod_index":returned,"expected_lod1_triangles":lineage["lod1_triangles"]}
    else:
        c=before["pcg"]["component"]; component=ue.find_object(None,c["object_path"])
        _asset_pin(config,config["pcg"]["graph_path"],before["pcg"]["graph"]["asset_file_sha256"])
        selector=ue.find_object(None,request["selector_path"])
        p.require(_id(component)=={"object_path":c["object_path"],"class_path":config["pcg"]["component_class"]} and
                  component.get_graph().get_path_name()==config["pcg"]["graph_path"] and
                  component.get_editor_property("seed")==c["seed"],"PCG component changed")
        _in_world(component.get_owner(),config)
        p.require(_id(selector)=={"object_path":request["selector_path"],"class_path":request["selector_class"]} and
                  selector.get_outer().get_path_name().startswith(config["pcg"]["graph_path"]+":"),
                  "Selector is outside exact graph")
        nodes=list(component.get_graph().get_editor_property("nodes"))
        p.require(len(nodes)<=128,"Graph node count exceeds bound")
        selected=[x for x in nodes if x.get_path_name()==request["node_path"]]
        p.require(len(selected)==1,"Exact descriptor node is absent/ambiguous")
        settings=selected[0].get_settings()
        p.require(_id(settings)=={"object_path":request["settings_path"],"class_path":"/Script/PCG.PCGStaticMeshSpawnerSettings"} and
                  settings.get_editor_property("mesh_selector_parameters")==selector and selector.get_outer()==settings,
                  "Selector is not the exact graph node's spawner settings")
        entries=list(selector.get_editor_property("mesh_entries")); index=request["entry_index"]
        p.require(1<=len(entries)<=128 and index<len(entries),"Descriptor entries changed")
        entry=entries[index]; descriptor=entry.get_editor_property("descriptor")
        p.require(descriptor.get_editor_property("static_mesh").get_path_name()==request["before_mesh_path"],
                  "Descriptor old mesh changed")
        mesh=ue.find_object(None,request["after_mesh_path"])
        target=next(x for x in config["meshes"] if x["object_path"]==request["after_mesh_path"])
        _asset_pin(config,target["object_path"],target["asset_file_sha256"])
        p.require(_id(mesh)=={"object_path":request["after_mesh_path"],"class_path":"/Script/Engine.StaticMesh"},
                  "Blender descriptor mesh not loaded/bound")
        descriptor.set_editor_property("static_mesh",mesh); entry.set_editor_property("descriptor",descriptor)
        entries[index]=entry; selector.set_editor_property("mesh_entries",entries)
        component.generate_local(True)  # reflected local-only delayed call; never network Generate.
        result={"descriptor_before":request["before_mesh_path"],"descriptor_after":request["after_mesh_path"],
                "actual_component_seed":c["seed"],"local_only":True,
                "soft_descriptor_read_effect":{"selector_path":request["selector_path"],
                    "entry_index":request["entry_index"],
                    "loading":"May synchronously load current selected target and dependencies; load count not measured"}}
    return {"operation_id":plan["operation_id"],"plan_sha256":admitted_plan_sha256,
            "state":"DISPATCHED_PENDING_COMPLETION","dispatched":True,"completed":False,
            "adopted":False,"observed_return":result,
            "next":"Retain actual callback/output readback, source/native pins, save/reopen and consumer receipts. Return values alone are not completion."}


def qualify_referenced_operation(config,before,after,plan,completion):
    """Reuse the existing strict stage qualifier; a dispatch receipt cannot pass."""
    try:
        p.require(plan==prepare_operation(config,before,plan["operation_id"],plan["kind"],plan["request"]),
                  "Operation plan no longer matches source/prestate")
        p.require(completion.get("plan_sha256")==p.fingerprint(plan) and
                  completion.get("operation_id")==plan["operation_id"],"Wrong operation completion binding")
        if plan["kind"]==KINDS[1]:
            old=before["pcg"]["graph"].get("asset_file_sha256")
            new=after["pcg"]["graph"].get("asset_file_sha256")
            observation=after.get("observation",{})
            p.require(p.sha(new) and new!=old and observation.get("phase")=="reopen" and
                      observation.get("unit_id")==p.UNITS[1] and
                      observation.get("operation_id")==plan["operation_id"] and
                      observation.get("package_overrides",{}).get("pcg_graph")==new,
                      "Descriptor edit requires changed saved graph and exact reopened package witness")
            change=completion.get("descriptor_change",{}); request=plan["request"]
            p.require(change.get("completed") is True and change.get("operation_id")==plan["operation_id"] and
                      change.get("plan_sha256")==p.fingerprint(plan) and
                      p.sha(change.get("receipt_sha256")) and p.text(change.get("record_path"),512),
                      "Missing operation-correlated descriptor change receipt")
            p.require(p.integer(change.get("entry_index"),0,127) and
                      all(change.get(k)==request[k] for k in ("node_path","settings_path","selector_path",
                      "entry_index","before_mesh_path","after_mesh_path")) and
                      change.get("saved_graph_sha256")==new and change.get("reopened_graph_sha256")==new,
                      "Descriptor/save/reopen receipt differs from the exact operation plan")
        return p.qualify(config,before,after,completion)
    except (p.ContractError,KeyError,TypeError,ValueError) as exc:
        return {"state":"HELD","adopted":False,"errors":[str(exc)[:256]]}


def apply_imported_lod_policy(config,before,plan,admitted_plan_sha256,*,unreal_module=None):
    """After actual import completion only; never repeats the import or saves.

    The operator reconciles an uncertain dispatch first. No polling or auto retry.
    """
    p.require(plan["kind"]==KINDS[0] and p.fingerprint(plan)==admitted_plan_sha256 and
              plan==prepare_operation(config,before,plan["operation_id"],plan["kind"],plan["request"]),
              "Imported LOD policy admission changed")
    if unreal_module is None:
        import unreal as unreal_module
    ue=unreal_module;_world(config,ue)
    row=next(x for x in before["meshes"] if x["id"]==plan["request"]["mesh_id"])
    _asset_pin(config,row["object_path"],row["asset_file_sha256"])
    obj=ue.find_object(None,row["object_path"]);p.require(_id(obj)=={k:row[k] for k in ("object_path","class_path")},"Wrong imported LOD target")
    sub=ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem);desired=config["units"][p.UNITS[0]]["desired_policy"]
    old=row["lods"][0]
    p.require(sub.get_lod_count(obj)==2 and obj.get_num_triangles(0)==old["triangles"] and
              obj.get_num_vertices(0)==old["vertices"] and obj.get_num_triangles(1)==desired["lod1_triangles"] and
              obj.get_num_vertices(1)==desired["lod1_vertices"] and
              all(sub.get_lod_build_settings(obj,0).get_editor_property(k)==v for k,v in old["build_settings"].items()),
              "Import is incomplete, changed LOD0 or differs from authored LOD1 geometry")
    settings=sub.get_lod_build_settings(obj,1)
    for key,value in desired["lod1_build_settings"].items():settings.set_editor_property(key,value)
    sub.set_lod_build_settings(obj,1,settings)
    p.require(sub.set_lod_screen_sizes(obj,desired["screen_sizes"]) is True,"LOD threshold operation failed")
    p.require(list(sub.get_lod_screen_sizes(obj))==desired["screen_sizes"] and
              all(sub.get_lod_build_settings(obj,1).get_editor_property(k)==v
                  for k,v in desired["lod1_build_settings"].items()),"LOD policy readback differs")
    return {"operation_id":plan["operation_id"],"plan_sha256":admitted_plan_sha256,
            "state":"POLICY_APPLIED_UNSAVED","completed":False,"adopted":False,
            "next":"Existing sole operator exact mesh save, fresh reopen/readback, material/collision/consumer review and referenced stage qualification."}
