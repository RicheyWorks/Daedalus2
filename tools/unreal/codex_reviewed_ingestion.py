# SPDX-License-Identifier: MIT
"""Run the proven PR146 adapter for one retained reviewed candidate.

Actual production import/save then identical-input reuse, not a test suite.
Requires the root operator's acknowledged single-writer turn and an admission
deadline inside its current lease. Never edits the adapter or frozen importer.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "connectors/claude-asset-pipeline"))
from asset_pipeline import wire
from codex_contest_island_delivery import Mcp, SCENE, package

HEAD = "05fc3c2521c62e06de88bf85106eee0dd55086ab"
HASHES = {
    "daedalus_ingestion_receipts": "04d21db0cd1352d9ca16abbaeeade702e924bd689cee5ea499c0b0a408f219a3",
    "daedalus_codex_ingestion": "986d49d34cbbf1d79cbdd2e822c33eff6c6033a6e2ccb1712bfd0e2874748711",
}
IMPORTER_SHA = "dfac57ce929686dc1bca400da4a258405f0a1bd1cb783fa673793ba8f28de982"
BASE = ROOT / "engines/unreal/DaedalusLink/Content/IslandSource/CodexContest"
CANDIDATES = {
    "hero-r4": ("CodexIsland_summit_rim_84011_HeroR4", BASE / "HeroR4/codex-hero-r4.delivery.json"),
    "garden-gate-r1": ("CodexIsland_cliff_garden_84022_GardenGateR1", BASE / "GardenGateR1/codex-garden-gate-r1.delivery.json"),
}
NATIVE = '''import sys,hashlib,json,time
from pathlib import Path
import unreal
import importlib.util
cfg=CONFIG
loaded=[]
for name,expected in cfg['module_hashes'].items():
    path=Path(cfg['review'])/(name+'.py')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected:
        raise RuntimeError('reviewed PR146 source changed; no item admitted: '+name)
    spec=importlib.util.spec_from_file_location(name,str(path))
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    exec(compile(raw,str(path),'exec'),module.__dict__)
    loaded.append({'name':name,'path':str(path),'sha256':expected})
ingestion=sys.modules['daedalus_codex_ingestion']
def steps():
    b=sys.modules.get('claude_unreal_bridge')
    others=[{'type':req.get('type'),'label':(req.get('params') or {}).get('label')}
            for gen,req,box in list(b._running)
            if req.get('type')!='daedalus.steps' or (req.get('params') or {}).get('label')!=cfg['label']]
    if others or b._jobs.qsize() or b._remote_lock.locked():
        raise RuntimeError('conflicting bridge job observed; no item admitted: '+str(others))
    dirty=[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    dirty += [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    if dirty:
        raise RuntimeError('dirty packages observed before ingestion; preserve work: '+str(dirty))
    outcome={'stage':'production_started','reviewed_head':cfg['reviewed_head'],'runtime_head':cfg['reviewed_head'],
             'loaded':loaded,'candidate':cfg['name'],'prepared_manifest_sha256':cfg['manifest_sha256'],
             'deadline_epoch':cfg['deadline'],'editor_preflight':cfg['editor_preflight'],'passes':[]}
    for phase in ('production_import','identical_input_reuse'):
        started=time.perf_counter()
        results=[]
        iterator=ingestion.import_steps(cfg['manifest'],[cfg['name']],cfg['importer'],cfg['importer_sha256'],deadline_epoch=cfg['deadline'])
        for value in iterator:
            results.append(value)
            yield value
        outcome['passes'].append({'phase':phase,'elapsed_s':round(time.perf_counter()-started,6),'results':results})
        outcome['stage']='production_saved' if phase=='production_import' else 'production_saved_and_unchanged_reused'
        Path(cfg['report']).write_text(json.dumps(outcome,indent=2)+'\\n',encoding='utf-8')
        yield phase
    return outcome
'''


def run(candidate, review, deadline_epoch, expected_manifest_sha256):
    name, manifest = CANDIDATES[candidate]
    report = BASE / ("codex-" + candidate + ".adoption.json")
    reply_path = BASE / ("codex-" + candidate + ".adoption.reply.json")
    if report.exists() or reply_path.exists():
        raise RuntimeError("inspect retained attempt before another run: " + str(report))
    actual = hashlib.sha256(manifest.read_bytes()).hexdigest()
    if actual != expected_manifest_sha256:
        raise RuntimeError("reviewed prepared manifest bytes differ")
    mcp = Mcp(timeout=30)
    pie = mcp.call("EditorToolset.EditorAppToolset", "IsPIERunning")
    current_map = mcp.call(SCENE, "get_current_level")
    if pie is not False or package(current_map) != "/Game/Daedalus/DaedalusWorld":
        raise RuntimeError("actual agreed map with PIE stopped is required before admission")
    label = "Codex reviewed " + candidate + " production import-save and unchanged reuse"
    cfg = dict(name=name, manifest=str(manifest), manifest_sha256=actual,
               review=str(Path(review).resolve()), reviewed_head=HEAD, module_hashes=HASHES,
               importer=str(ROOT / "engines/unreal/DaedalusLink/Content/Python/daedalus_codex_prepared_assets.py"),
               importer_sha256=IMPORTER_SHA, report=str(report), deadline=deadline_epoch, label=label,
               editor_preflight={"server":mcp.server,"pie_running":pie,"current_map":current_map})
    code = NATIVE.replace("CONFIG", repr(cfg), 1)
    reply = wire.call(wire.UNREAL, "daedalus.steps", code=code, label=label, budget_ms=1, timeout=180, side="Unreal")
    with reply_path.open("x", encoding="utf-8") as output:
        json.dump(reply, output, indent=2)
        output.write("\n")
    print(json.dumps({"candidate": name, "error": reply.get("error"), "steps": reply.get("steps"),
                      "seconds": reply.get("seconds"), "report":str(report),"reply":str(reply_path)}, indent=2))
    if reply.get("error"):
        raise RuntimeError("inspect actual retained reply and native outcome before retry")
    return reply


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", choices=CANDIDATES)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--deadline-epoch", type=float, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    args = parser.parse_args()
    run(args.candidate, args.review, args.deadline_epoch, args.expected_manifest_sha256)
