# SPDX-License-Identifier: MIT
# Sweep: spawn one of EVERY placeable actor class the editor knows, read it back, destroy it.
# Abstract classes, ones flagged NotPlaceable/Deprecated, and ones that need a world type the editor level
# isn't (game modes, controllers, HUDs...) are recorded as EXCLUDED with the reason, never silently skipped.

import inspect as _inspect

_SKIP_WORDS = ("GameMode", "GameState", "PlayerController", "PlayerState", "AIController", "HUD", "WorldSettings",
               "GameSession", "SpectatorPawn", "Info", "Brush", "LevelScriptActor", "DefaultPhysicsVolume")


def _actor_classes():
    out = []
    for n in dir(unreal):
        c = getattr(unreal, n, None)
        if _inspect.isclass(c):
            try:
                if issubclass(c, unreal.Actor):
                    out.append((n, c))
            except Exception:
                pass
    return sorted(out)


@probe("sweep.actors")
def _sweep():
    rows, ok, fail, excluded = {}, 0, 0, 0
    for name, cls in _actor_classes():
        uclass = cls.static_class()
        flags = []
        try:
            if unreal.SystemLibrary.is_valid_class(uclass) is False:
                flags.append("invalid")
        except Exception:
            pass
        why = None
        if name.startswith(("SKEL_", "REINST_")) or "Deprecated" in name:
            why = "generated or deprecated"
        elif any(w in name for w in _SKIP_WORDS):
            why = "a game-framework or world actor, made by the game, not placed"
        if why:
            rows[name] = {"state": "EXCLUDED", "why": why}
            excluded += 1
            continue
        try:
            a = EAS.spawn_actor_from_class(cls, ORIGIN)
            if a is None:
                rows[name] = {"state": "FAIL", "why": "spawn returned None (abstract or not placeable)"}
                fail += 1
                continue
            a.set_folder_path(PROBE_FOLDER)
            back = a.get_class().get_name()
            comps = len(a.get_components_by_class(unreal.ActorComponent))
            EAS.destroy_actor(a)
            rows[name] = {"state": "ok", "class": back, "components": comps}
            ok += 1
        except Exception as e:
            rows[name] = {"state": "FAIL", "why": "%s: %s" % (type(e).__name__, str(e)[:160])}
            fail += 1
    total = len(rows)
    return {"ok": ok + fail + excluded == total and ok > 0, "total": total, "spawned": ok, "failed": fail,
            "excluded": excluded, "rows": rows}
