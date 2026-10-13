# SPDX-License-Identifier: MIT
"""Fast (<10 s) editor-turn fix: retune the existing OddsReaper storm Mood Volume without re-placing the island.
Needs the rebuilt DaedalusLink (MoodVolume trigger_on_view / force_on_begin_play). Saves only OddsReaperIsland."""
import unreal
SUB = "/Game/OddsReaper/Maps/OddsReaperIsland"


def run():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    les.set_current_level_by_name("OddsReaperIsland")
    vols = [a for a in actors.get_all_level_actors() if isinstance(a, unreal.DaedalusMoodVolume) and a.get_actor_label() == "OddsReaper Storm Mood"]
    out = []
    for v in vols:
        v.set_actor_scale3d(unreal.Vector(4.0, 4.0, 3.0))
        v.set_editor_property("mood", "oddsreaper_storm")
        for name, val in (("set_weather", True), ("trigger_on_view", True), ("force_on_begin_play", True), ("hold_while_inside", True), ("set_hour", 18.75)):
            for prop in (name, "b_" + name):
                try: v.set_editor_property(prop, val); break
                except Exception: pass
        v.set_editor_property("weather", unreal.DaedalusWeather.STORM)
        out.append(str(v.get_path_name()))
    les.save_current_level()
    return {"ok": bool(vols), "volumes": out}


if __name__ == "__main__":
    print(run())
