"""youtube-master (Team Grok): Wild Biomes Sequencer flythroughs.
Run in the editor ONLY during a granted Grok editor turn, via:
  python ...\\pcg-ecology\\ue_send.py C:\\Users\\730ri\\projects\\bot-team\\art\\NOTES\\youtube-master\\ytm_flythrough_ue.py 600
Creates one LevelSequence per biome + a master cut under /Game/YTM/Seq, with a
spawnable CineCamera orbiting/dollying each biome centre (pythagoras WB_Label_<biome>
actors; fallback = ring 4.5-16 km around PlayerStart). Touches only /Game/YTM. Idempotent.
Does not start Play. Saves only its own assets.
"""
import math, unreal

BIOMES = ["YoungMeadow", "BrambleScrub", "PineStand", "OldGrowthOak", "WillowRiverbank"]
FPS = 30
SHOT_SECONDS = 12
ROOT = "/Game/YTM/Seq"
# shot style per biome: (radius cm, height cm, sweep deg, focal mm)
STYLE = {
    "YoungMeadow":     (6000, 900, 120, 24),
    "BrambleScrub":    (3500, 400, 90, 35),
    "PineStand":       (5000, 2500, 150, 28),
    "OldGrowthOak":    (4000, 1800, 100, 21),
    "WillowRiverbank": (4500, 600, 110, 35),
    "YTMIsland":       (14000, 4000, 160, 24),
    "YTM_Spring":      (900, 250, 70, 35),
    "YTM_Shrine":      (700, 220, 80, 35),
    "YTM_Garden":      (2200, 700, 100, 28),
    "YTM_Farm":        (2400, 800, 100, 28),
    "YTM_Dock":        (2500, 900, 90, 24),
}
# island detail shots, offsets (cm) from the YTM_Spawn marker (layout from ytm_island_ue.py / ytm_hero_ue.py)
YTM_DETAIL = {"YTM_Spring": (1500, 0, 100), "YTM_Shrine": (-800, 1200, 150), "YTM_Garden": (4900, 200, 100),
              "YTM_Farm": (-4900, 0, 100), "YTM_Dock": (0, -11000, 100)}
eas = unreal.EditorAssetLibrary
ell = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def actors():
    return ell.get_all_level_actors()

PYT_SUB = "Island_Pythagoras"
PYT_CENTRE = unreal.Vector(-60000, 60000, 2500)
def pyt_loaded():
    """READ-ONLY: report whether pythagoras's sublevel is streamed in. We never add, remove, modify or save it
    (adding a level would dirty DaedalusWorld); if it is not loaded we orbit PYT_CENTRE instead."""
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    for s_ in unreal.EditorLevelUtils.get_levels(w):
        if PYT_SUB in s_.get_path_name(): return True
    return False
def _key(n): return n.lower().replace("_","").replace(" ","")
def biome_centres():
    """Real centres first: pythagoras WB_Label_<name>, then centroid of Habitat_<name>/PYTH_WB_<name> actors
    (wild_biomes_ue.py), names matched loosely (YoungMeadow == young_meadow). Fallback ring only if none."""
    want = {_key(b): b for b in BIOMES}; found = {}; pts = {}
    for a in actors():
        lab = a.get_actor_label(); tags = [str(t) for t in a.tags]
        for pre in ("PYT_Label_", "WB_Label_"):
            if lab.startswith(pre) and _key(lab[len(pre):]) in want:
                found[want[_key(lab[len(pre):])]] = a.get_actor_location()
        for pre in ("PYT_Habitat_", "WB_Habitat_"):
            if lab.startswith(pre) and _key(lab[len(pre):]) in want:
                pts.setdefault(want[_key(lab[len(pre):])], []).append(a.get_actor_location())
        for t in tags:
            for pre in ("PYT_Habitat_", "Habitat_", "PYTH_WB_"):
                if t.startswith(pre) and _key(t[len(pre):]) in want:
                    pts.setdefault(want[_key(t[len(pre):])], []).append(a.get_actor_location())
    for b, ps_ in pts.items():
        if b not in found:
            found[b] = unreal.Vector(sum(p.x for p in ps_)/len(ps_), sum(p.y for p in ps_)/len(ps_), sum(p.z for p in ps_)/len(ps_))
    unreal.log("YTM: real biome centres for %s" % sorted(found))
    if len(found) < len(BIOMES):
        # Wild Biomes lives in Island_Pythagoras around PYT_CENTRE; without markers, orbit that centre (5 points, 40 m apart)
        o = PYT_CENTRE
        for i, b in enumerate(BIOMES):
            if b not in found:
                t = 2 * math.pi * i / len(BIOMES)
                found[b] = unreal.Vector(o.x + 4000 * math.cos(t), o.y + 4000 * math.sin(t), o.z)
                unreal.log_warning("YTM: no marker for %s, orbiting Island_Pythagoras centre" % b)
    # Youtube Master Island hero shot (spawn marker placed by ytm_island_ue.py)
    sp = next((a for a in actors() if a.actor_has_tag("YTM_Spawn")), None)
    if sp:
        o = sp.get_actor_location(); found["YTMIsland"] = o
        for k, (dx, dy, dz) in YTM_DETAIL.items():
            found[k] = unreal.Vector(o.x + dx, o.y + dy, o.z + dz)
    return found

def look_rot(src, dst):
    return unreal.MathLibrary.find_look_at_rotation(src, dst)

def make_sequence(name, frames):
    path = ROOT + "/" + name
    if eas.does_asset_exist(path):
        eas.delete_asset(path)
    seq = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, ROOT, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
    seq.set_display_rate(unreal.FrameRate(FPS, 1))
    seq.set_playback_start(0)
    seq.set_playback_end(frames)
    return seq

def add_camera(seq, centre, style, start, frames):
    radius, height, sweep, focal = style
    cam = seq.add_spawnable_from_class(unreal.CineCameraActor)
    cuts = seq.find_tracks_by_type(unreal.MovieSceneCameraCutTrack) or [seq.add_track(unreal.MovieSceneCameraCutTrack)]
    cs = cuts[0].add_section()
    cs.set_range(start, start + frames)
    cs.set_camera_binding_id(seq.get_binding_id(cam))
    tr = cam.add_track(unreal.MovieScene3DTransformTrack)
    sec = tr.add_section(); sec.set_range(start, start + frames)
    ch = sec.get_all_channels()  # x,y,z, roll,pitch,yaw, sx,sy,sz
    steps = 6
    for k in range(steps + 1):
        f = unreal.FrameNumber(start + int(frames * k / steps))
        a = math.radians(-sweep / 2 + sweep * k / steps)
        r = radius * (1.0 - 0.25 * k / steps)  # slow push-in
        p = unreal.Vector(centre.x + r * math.cos(a), centre.y + r * math.sin(a), centre.z + height)
        rot = look_rot(p, centre)
        for c, v in zip(ch[:6], [p.x, p.y, p.z, rot.roll, rot.pitch, rot.yaw]):
            c.add_key(f, v, interpolation=unreal.MovieSceneKeyInterpolation.AUTO)
    # focal length
    return cam

def run():
    unreal.log("YTM: Island_Pythagoras loaded=%s (read-only)" % pyt_loaded())
    pre_dirty = {p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()}
    if not eas.does_directory_exist(ROOT):
        eas.make_directory(ROOT)
    centres = biome_centres()
    frames = FPS * SHOT_SECONDS
    island = [k for k in ["YTMIsland"] + list(YTM_DETAIL) if k in centres]
    shots = island[:1] + island[1:3] + BIOMES + island[3:]  # matches recording-isle shots.real.txt order roughly
    master = make_sequence("WB_Flythrough_Master", frames * len(shots))
    for i, b in enumerate(shots):
        s = make_sequence(b if b.startswith("YTM_") else "WB_Flythrough_" + b, frames)
        add_camera(s, centres[b], STYLE[b], 0, frames)
        add_camera(master, centres[b], STYLE[b], i * frames, frames)
        eas.save_loaded_asset(s)
    eas.save_loaded_asset(master)
    now_dirty = {p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()}
    unreal.log("YTM: maps dirtied by this run (should be none): %s" % sorted(now_dirty - pre_dirty))
    unreal.log("YTM: flythroughs written to %s (%d shots, %ds each)" % (ROOT, len(shots), SHOT_SECONDS))

run()
