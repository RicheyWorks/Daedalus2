"""Read the authorized normal activation; no native mutations or game execution.

Only the sole operator executes this script after normal startup is responsive.
It writes one new host receipt, never replaces an earlier receipt, and never
starts PIE, loads an asset, spawns an actor, submits input, advances or saves.
"""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys

TASK = Path(__file__).resolve().parent
ROOT = TASK / "contest-island-production"
BASE = ROOT / "engines/unreal/DaedalusLink/Content/IslandSource/CodexContest"
JOURNAL = BASE / "codex-arcade-normal-activation.json"
OUT = BASE / "codex-arcade-loaded-readback.json"
LIVE = Path("C:/Unreal/DaedalusRealm/Plugins/DaedalusLink")
MAP_FILE = Path("C:/Unreal/DaedalusRealm/Content/Daedalus/DaedalusWorld.umap")
WORLD = "/Game/Daedalus/DaedalusWorld.DaedalusWorld"
EXPECTED_MAP = {"bytes": 209329457, "sha256": "5690b48f9cdc9f50251c08127b161ab4f3afae49754b75316d561da2a3a80933"}
MARKER = "# Codex activated arcade read-only snapshot v1"
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "connectors/claude-asset-pipeline"))
from unreal_mcp.client import Mcp
from asset_pipeline import wire


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def fp(path):
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return {"bytes": size, "sha256": digest.hexdigest()}


def native_code():
    return r'''# Codex activated arcade read-only snapshot v1
import unreal,sys,hashlib
from datetime import datetime,timezone
from pathlib import Path
MARKER='# Codex activated arcade read-only snapshot v1'
def queue_read():
    b=sys.modules.get('claude_unreal_bridge')
    fields=('_jobs','_running','_job_boxes','_remote_lock')
    if b is None or not all(hasattr(b,k) for k in fields):
        return {'supported':False,'reason':'existing bridge queue fields unavailable'}
    with b._jobs.mutex:
        queued=[{'type':req.get('type'),'label':(req.get('params') or {}).get('label')} for req,box in b._jobs.queue]
    running=[]
    for gen,req,box in list(b._running):
        code=str((req.get('params') or {}).get('code',''))
        running.append({'type':req.get('type'),'label':(req.get('params') or {}).get('label'),
            'code_sha256':hashlib.sha256(code.encode()).hexdigest(),
            'this_read_marker':req.get('type')=='execute_python' and code.startswith(MARKER)})
    own=[r for r in running if r['this_read_marker']]
    other=[r for r in running if not r['this_read_marker']]
    unfinished=sum(not box['done'].is_set() for box,stamp in b._job_boxes.values())
    locked=b._remote_lock.locked()
    return {'supported':True,'bridge_file':b.__file__,
        'bridge_sha256':hashlib.sha256(Path(b.__file__).read_bytes()).hexdigest(),
        'queued_jobs':queued,'running_generators':running,'unfinished_async_job_boxes':unfinished,
        'remote_execution_lock_locked':locked,
        'idle_except_this_read_marker':len(own)==1 and not other and not queued and unfinished==0 and not locked}
def editor_read():
    return {'world':unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name(),
        'pie':bool(unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor()),
        'dirty_maps':[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
        'dirty_content':[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]}
def snap(a):
    p=a.get_actor_location();r=a.get_actor_rotation();s=a.get_actor_scale3d()
    comps=a.get_components_by_class(unreal.StaticMeshComponent)
    return {'path':a.get_path_name(),'label':a.get_actor_label(),'folder':str(a.get_folder_path()),
        'location':[p.x,p.y,p.z],'rotation':[r.pitch,r.yaw,r.roll],'scale':[s.x,s.y,s.z],
        'components':[{'path':c.get_path_name(),'mesh':c.static_mesh.get_path_name() if c.static_mesh else None,
            'materials':[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]} for c in comps]}
def prop(obj,name):
    try:return obj.get_editor_property(name)
    except Exception as exc:return {'unsupported':str(exc)}
def capture():
    out={'observed_utc':datetime.now(timezone.utc).isoformat(),'native_mutation':False,
        'unsupported':[],'gate_before':editor_read(),'queue_before':queue_read()}
    g=out['gate_before'];q=out['queue_before']
    if g['pie'] or g['dirty_maps'] or g['dirty_content'] or g['world']!='/Game/Daedalus/DaedalusWorld.DaedalusWorld':
        out['hold_reason']='PIE, dirty packages or different world; no actor/getter reads attempted'
        return out
    if not q.get('supported') or not q.get('idle_except_this_read_marker'):
        out['hold_reason']='queue verification unsupported or conflicting operation; no actor/getter reads attempted'
        return out
    cls=getattr(unreal,'DaedalusDesktopArcade',None)
    out['reflection']={'python_class_present':cls is not None,'class_path':None,'methods':{}}
    reflected=unreal.find_object(None,'/Script/DaedalusLink.DaedalusDesktopArcade')
    if reflected:out['reflection']['class_path']=reflected.get_path_name()
    for name in ('submit_arcade_source_key','submit_arcade_source_controller_button'):
        method=getattr(cls,name,None) if cls else None
        out['reflection']['methods'][name]={'present':callable(method),'doc':getattr(method,'__doc__',None)}
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    out['actors']=[snap(a) for a in actors if a.get_actor_label().startswith('Codex')]
    out['arcade_actors']=[]
    for a in actors:
        if not cls or not isinstance(a,cls):continue
        row={'path':a.get_path_name(),'label':a.get_actor_label(),'class':a.get_class().get_path_name(),
            'config':{name:prop(a,name) for name in ('initial_game_id','initial_seed','cabinet_id','auto_advance')},'getters':{}}
        for name in ('get_cabinet_id','get_selected_game_id','get_game_option'):
            method=getattr(a,name,None)
            try:row['getters'][name]=method() if callable(method) else {'unsupported':'method not reflected'}
            except Exception as exc:row['getters'][name]={'unsupported':str(exc)}
        method=getattr(a,'get_available_games',None)
        try:
            row['catalog']=[{name:prop(e,name) for name in ('id','title','controls')} for e in method()] if callable(method) else {'unsupported':'get_available_games not reflected'}
        except Exception as exc:row['catalog']={'unsupported':str(exc)}
        method=getattr(a,'get_state',None)
        try:
            if callable(method):
                state=method()
                row['state']={name:prop(state,name) for name in ('initialized','open','paused','over','won','save_pending','has_saved_run','id','title','note','persistence_message','score','lives','seed','steps','option')}
            else:row['state']={'unsupported':'get_state not reflected'}
        except Exception as exc:row['state']={'unsupported':str(exc)}
        out['arcade_actors'].append(row)
    out['gate_after']=editor_read();out['queue_after']=queue_read()
    out['background_compilation']='not queried';out['other_epic_mcp_sessions']='not queried'
    return out
result=capture()
'''


def compare_actors(before, after):
    issues, tolerated = [], []
    old = {r["path"]: r for r in before}
    new = {r["path"]: r for r in after}
    if len(old) != len(before) or len(new) != len(after):
        issues.append("duplicate actor paths")
    if set(old) != set(new):
        issues.append({"missing_actor_paths": sorted(set(old)-set(new)), "new_actor_paths": sorted(set(new)-set(old))})
    for path in sorted(set(old) & set(new)):
        left, right = old[path], new[path]
        for key in ("label", "folder"):
            if left[key] != right[key]:issues.append({"actor": path, "field": key, "before": left[key], "after": right[key]})
        for key in ("location", "rotation", "scale"):
            a, b = left[key], right[key]
            if a == b:continue
            difference = {"actor": path, "field": key, "before": a, "after": b}
            if len(a)==len(b)==3 and all(isinstance(v,(int,float)) and math.isfinite(v) for v in a+b) and all(abs(x-y)<=1e-5 for x,y in zip(a,b)):
                tolerated.append(dict(difference, reason="numeric round-trip difference within absolute 1e-5; exact values retained"))
            else:issues.append(difference)
        a = sorted(left["components"], key=lambda c: c["path"])
        b = sorted(right["components"], key=lambda c: c["path"])
        if a != b:issues.append({"actor": path, "field": "static_mesh_components", "before": a, "after": b})
        elif left["components"] != right["components"]:
            tolerated.append({"actor": path, "reason": "component enumeration order only"})
    if [r["path"] for r in before] != [r["path"] for r in after] and set(old)==set(new):
        tolerated.append({"reason": "actor enumeration order only"})
    return {"before_count": len(before), "after_count": len(after), "issues": issues,
            "equivalent": not issues, "transient_or_numeric_differences": tolerated}


def main():
    if OUT.exists():raise RuntimeError("existing loaded readback retained; inspect it before further execution")
    code = native_code()
    own_hash = hashlib.sha256(code.encode()).hexdigest()
    record = {"schema": "daedalus.codex-arcade-normal-activation-readback.v1", "stage": "readback_in_progress",
              "utc": datetime.now(timezone.utc).isoformat(), "host_source": {"path": str(Path(__file__)), **fp(__file__)},
              "native_code_sha256": own_hash, "native_mutation": False, "issues": [], "limits": [
                  "Read-only reflection/configuration and preservation, no game inputs/PIE/tests/native gameplay acceptance.",
                  "Loaded DLL process identity is not queried; normal activation journal plus installed bytes and reflection are separate evidence.",
                  "No full import/asset scan; source and eleven runtime catalog witnesses are checked on host only."]}
    try:
        journal = load(JOURNAL)
        record["activation_journal"] = {"path": str(JOURNAL), "fingerprint": fp(JOURNAL), "stage": journal.get("stage"),
            "new_editor_pid": journal.get("new_editor_pid"), "old_editor_pid": journal.get("old_editor_pid")}
        if journal.get("forced_close") is not False or not journal.get("reopen_dispatched") or not journal.get("old_editor_exit_verified_utc"):
            raise RuntimeError("require completed authorized normal exit/install/reopen journal")
        events = journal.get("installations", [])
        if len(events)!=13 or any(x.get("state")!="installed_and_verified" for x in events):
            raise RuntimeError("require exactly thirteen verified installation leaves")
        record["installed_leaves"] = [{"path": e["target"], "expected": e["expected"], "actual": fp(e["target"])} for e in events]
        if any(x["actual"]!=x["expected"] for x in record["installed_leaves"]):raise RuntimeError("installed leaf bytes changed")
        record["module_receipt"] = fp(LIVE/"Binaries/Win64/UnrealEditor.modules")
        expected_receipt = journal["unchanged_module_receipt"]["fingerprint"]
        if record["module_receipt"]!={k:expected_receipt[k] for k in ("bytes","sha256")}:
            raise RuntimeError("retained module receipt changed")
        if journal["map_before"]!=EXPECTED_MAP:raise RuntimeError("saved activation map identity changed")
        record["map_before_read"] = fp(MAP_FILE)
        if record["map_before_read"]!=EXPECTED_MAP:raise RuntimeError("map bytes changed; preserve and reconcile")
        prepared_path = TASK/"native157/prepared.json"
        prepared = load(prepared_path)
        changed = {str(Path(e["target"]).relative_to(LIVE)).replace("\\","/") for e in events}
        source_rows = [{"relative": rel,"expected": expected,"actual": fp(LIVE/rel)} for rel,expected in prepared["live_source_baseline"].items() if rel not in changed]
        catalog_rows = [{"relative": rel,"expected": expected,"actual": fp(LIVE/rel)} for rel,expected in prepared["runtime_catalogs"].items()]
        record["bounded_source_preservation"] = {"prepared": fp(prepared_path), "unrelated_source_count": len(source_rows),
            "unrelated_source_drift": [x for x in source_rows if x["actual"]!=x["expected"]],
            "runtime_catalog_count": len(catalog_rows), "runtime_catalog_drift": [x for x in catalog_rows if x["actual"]!=x["expected"]],
            "prepared_miri_saved_asset_count": prepared.get("protected_miri_saved_assets"),
            "prepared_static_mesh_count": prepared.get("protected_static_mesh_count"),
            "asset_count_scope": "prepared references only, not recounted or imported"}
        if record["bounded_source_preservation"]["unrelated_source_drift"] or record["bounded_source_preservation"]["runtime_catalog_drift"]:
            raise RuntimeError("unrelated installed source/catalog changed; preserve and reconcile")
        # MCP did not automatically resume after the authorized restart. Its
        # absence is reported, while the established wire/native getters supply
        # the actual PIE/world/dirty/queue gate. No service is started here.
        try:
            mcp = Mcp(timeout=5)
            pie = mcp.call("EditorToolset.EditorAppToolset", "IsPIERunning")
            level = mcp.call("editor_toolset.toolsets.scene.SceneTools", "get_current_level")
            record["mcp_preflight"] = {"supported":True,"server":mcp.server,"pie":pie,"current_level":level}
            if pie is not False:raise RuntimeError("MCP reports PIE running or unsupported stopped value")
        except Exception as exc:
            record["mcp_preflight"] = {"supported":False,"error":str(exc),
                "fallback":"existing wire and native read-only PIE/world/dirty/queue APIs",
                "service_or_settings_action":False}
        reply = wire.call(wire.UNREAL,"execute_python",code=code,unattended=False,timeout=60,side="Unreal")
        record["native_reply"] = reply
        native = wire.obj(reply,side="Unreal",what="activated arcade read-only preservation")
        record["native"] = native
        if native.get("hold_reason"):record["issues"].append(native["hold_reason"])
        for name in ("queue_before","queue_after"):
            q = native.get(name,{})
            own = [x for x in q.get("running_generators",[]) if x.get("type")=="execute_python" and x.get("code_sha256")==own_hash]
            other = [x for x in q.get("running_generators",[]) if x not in own]
            q["matching_read_generators"] = len(own)
            q["other_running_generators"] = other
            q["self_sha_verified_idle"] = bool(q.get("supported") and len(own)==1 and not other and not q.get("queued_jobs") and q.get("unfinished_async_job_boxes")==0 and q.get("remote_execution_lock_locked") is False)
            if not q["self_sha_verified_idle"]:record["issues"].append(name+": queue/self SHA verification unavailable or conflicting")
        for name in ("gate_before","gate_after"):
            g=native.get(name,{})
            if g.get("world")!=WORLD or g.get("pie") is not False or g.get("dirty_maps")!=[] or g.get("dirty_content")!=[]:
                record["issues"].append(name+": current map/PIE/dirty gate differs or unsupported")
        if "actors" in native:
            record["actor_comparison"] = compare_actors(journal["native_before"]["actors"],native["actors"])
            record["issues"].extend(record["actor_comparison"]["issues"])
            if len(native["actors"])!=101:record["issues"].append("expected101 preserved Codex actors including existing Pong")
        methods = native.get("reflection",{}).get("methods",{})
        if any(not methods.get(k,{}).get("present") for k in ("submit_arcade_source_key","submit_arcade_source_controller_button")):
            record["issues"].append("one or both new reflected source-dispatch methods absent")
        pong = [x for x in native.get("arcade_actors",[]) if x.get("label")=="CodexAcceptance_Pong"]
        record["existing_pong_count"] = len(pong)
        if len(pong)!=1:record["issues"].append("existing Pong actor identity not unique/present")
        registry=LIVE/"Source/DaedalusLink/Public/DesktopGames/DaedalusDesktopGameRegistry.h"
        expected_catalog=[dict(zip(("id","title","controls"),values)) for values in
            re.findall(r'\{"([^"\n]+)","([^"\n]+)","([^"\n]+)"\}',registry.read_text(encoding="utf-8-sig"))]
        record["expected_catalog_from_installed_source"]={"file":str(registry),"fingerprint":fp(registry),"entries":expected_catalog}
        if len(expected_catalog)!=12:record["issues"].append("installed source catalog extraction did not yield twelve entries")
        if len(pong)==1:
            actual_catalog=pong[0].get("catalog")
            if actual_catalog!=expected_catalog:record["issues"].append({"field":"existing Pong catalog","expected":expected_catalog,"actual":actual_catalog})
            record["saved_staging_actor_count"]=len(native.get("actors",[]))-1
        def unsupported(value,path="native.arcade_actors"):
            found=[]
            if isinstance(value,dict):
                if "unsupported" in value:found.append({"field":path,"reason":value["unsupported"]})
                for key,item in value.items():found.extend(unsupported(item,path+"."+str(key)))
            elif isinstance(value,list):
                for index,item in enumerate(value):found.extend(unsupported(item,path+"["+str(index)+"]"))
            return found
        record["unsupported_getter_fields"]=unsupported(native.get("arcade_actors",[]))
        record["issues"].extend(record["unsupported_getter_fields"])
        record["map_after_read"] = fp(MAP_FILE)
        if record["map_after_read"]!=EXPECTED_MAP:record["issues"].append("map file changed during read")
        record["activation_journal_after"] = fp(JOURNAL)
        if record["activation_journal_after"]!=record["activation_journal"]["fingerprint"]:
            record["issues"].append("activation journal changed during read; reconcile concurrent journal updates")
        record["stage"] = "activated_reflection_and_preservation_readback_complete" if not record["issues"] else "activated_readback_requires_reconciliation"
    except Exception as exc:
        record["stage"]="readback_blocked_or_unsupported"
        record["issues"].append({"exception":type(exc).__name__,"message":str(exc)})
    with OUT.open("x",encoding="utf-8") as output:
        json.dump(record,output,indent=2,allow_nan=False)
        output.write("\n")
    print(json.dumps({"stage":record["stage"],"receipt":str(OUT),"issues":record["issues"]},indent=2))
    return 0 if not record["issues"] else 2


if __name__=="__main__":
    raise SystemExit(main())
