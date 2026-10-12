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
}
eas = unreal.EditorAssetLibrary
ell = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def actors():
    return ell.get_all_level_actors()

def biome_centres():
    found = {}
    for a in actors():
        n = a.get_actor_label()
        for b in BIOMES:
            if n == "WB_Label_" + b:
                found[b] = a.get_actor_location()
    if len(found) < len(BIOMES):
        ps = next((a for a in actors() if isinstance(a, unreal.PlayerStart)), None)
        o = ps.get_actor_location() if ps else unreal.Vector(0, 0, 0)
        for i, b in enumerate(BIOMES):
            if b not in found:
                r = 450000 + i * (1600000 - 450000) / max(1, len(BIOMES) - 1)
                t = 2 * math.pi * i / len(BIOMES)
                found[b] = unreal.Vector(o.x + r * math.cos(t), o.y + r * math.sin(t), o.z)
                unreal.log_warning("YTM: no WB_Label_%s, using fallback ring" % b)
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
    if not eas.does_directory_exist(ROOT):
        eas.make_directory(ROOT)
    centres = biome_centres()
    frames = FPS * SHOT_SECONDS
    master = make_sequence("WB_Flythrough_Master", frames * len(BIOMES))
    for i, b in enumerate(BIOMES):
        s = make_sequence("WB_Flythrough_" + b, frames)
        add_camera(s, centres[b], STYLE[b], 0, frames)
        add_camera(master, centres[b], STYLE[b], i * frames, frames)
        eas.save_loaded_asset(s)
    eas.save_loaded_asset(master)
    unreal.log("YTM: flythroughs written to %s (%d biomes, %ds each)" % (ROOT, len(BIOMES), SHOT_SECONDS))

run()
