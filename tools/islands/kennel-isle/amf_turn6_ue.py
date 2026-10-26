# art-master-flex r6: tag the placed pets so the native trough (DaedalusTonic*, docs/KENNEL_ISLE_TONIC_TROUGH.md) knows who is who.
#   Cane Corso (AMF_Companion + label CaneCorso) -> Cane_Corso      camp pup (AMF_Camp_CorsoPup) -> Pack_Member
#   optional coat/stage per label substring from COAT / STAGE below (empty on purpose: coat patterns are a design choice, untagged = None / stage 1).
# Tags only, idempotent, DRY=True by default (report only). AMF levels only; never touches other levels. Needs an editor window granted by codex-play-guard.
import unreal, json
DRY = True            # set False for the real run
OUT = r"C:\Users\730ri\projects\bot-team\art\NOTES\amf\last_turn6.json"
COAT = {}             # e.g. {"CaneCorso": "Stripes"} -> tag Coat_Stripes (Spots | Stripes | Labyrinth)
STAGE = {}            # e.g. {"CaneCorso": 2} -> tag Stage_2 (2 or 3; stage 1 is the default)

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
o = {"dry": DRY, "err": [], "pets_seen": 0, "would_add": {}, "tags_added": 0, "saved": []}

def want(a, lbl):
    w = []
    if "CaneCorso" in lbl and "AMF_Companion" in [str(x) for x in a.tags]: w.append("Cane_Corso")
    if lbl.startswith("AMF_Camp_CorsoPup"): w.append("Pack_Member")
    for k, v in COAT.items():
        if k in lbl and v in ("Spots", "Stripes", "Labyrinth"): w.append("Coat_" + v)
    for k, v in STAGE.items():
        if k in lbl and v in (2, 3): w.append("Stage_%d" % v)
    return w

try:
    if les.is_in_play_in_editor(): les.editor_request_end_play()
except Exception as e: o["err"].append("pie:" + str(e))
try:
    les.set_current_level_by_name("WildBiomes_AMF_Pets")
    for a in eas.get_all_level_actors():
        if "WildBiomes_AMF_Pets" not in a.get_outer().get_path_name(): continue
        cur = [str(x) for x in a.tags]
        if "AMF_Pets" not in cur: continue
        o["pets_seen"] += 1
        lbl = a.get_actor_label(); new = [t for t in want(a, lbl) if t not in cur]
        if not new: continue
        o["would_add"][lbl] = new
        if not DRY:
            a.modify(); a.tags = list(a.tags) + [unreal.Name(t) for t in new]; o["tags_added"] += len(new)
except Exception as e: o["err"].append("tag:" + str(e))
if not DRY:
    for L in ["WildBiomes_AMF_Pets"]:
        try:
            for lv in unreal.EditorLevelUtils.get_levels(unreal.EditorLevelLibrary.get_editor_world()):
                if L in lv.get_path_name(): o["saved"].append([L, unreal.EditorLoadingAndSavingUtils.save_packages([lv.get_outermost()], True)])
        except Exception as e: o["err"].append("save:" + L + ":" + str(e))
json.dump(o, open(OUT, "w"), indent=1)