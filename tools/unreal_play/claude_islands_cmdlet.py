# SPDX-License-Identifier: MIT
"""Contest placement without the editor UI (research doc 2026-10-14, action 3): one headless editor process places a
range of islands and exits. Runs only while the interactive editor is CLOSED (same packages).

    set CLAUDE_ISLANDS=369 700
    "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe" C:\\Unreal\\DaedalusRealm\\DaedalusRealm.uproject
        -run=pythonscript -script=C:\\Users\\730ri\\projects\\D2-build\\tools\\unreal_play\\claude_islands_cmdlet.py
        -nullrhi -unattended -NoShaderCompile -NoSplash -stdout -FullStdOutLogOutput

Prints CMDLET lines; the last one is the tally. The level is saved once at the end (save_world proves the mtime).
"""
import os
import time

import unreal

MAP = "/Game/Daedalus/DaedalusWorld"


def log(msg):
    unreal.log("CMDLET " + msg)
    print("CMDLET " + msg, flush=True)


def main():
    start, stop = [int(v) for v in os.environ.get("CLAUDE_ISLANDS", "0 0").split()]
    chunk = int(os.environ.get("CLAUDE_ISLANDS_CHUNK", "6"))
    t0 = time.time()
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not les.load_level(MAP):
        log("FAILED to load %s" % MAP)
        return
    log("level loaded in %.0f s" % (time.time() - t0))
    import daedalus_claude_islands as C
    import daedalus_plots
    placed = 0
    for s in range(start, stop, chunk):
        seeds = list(range(s, min(s + chunk, stop)))
        t = time.time()
        r = C.place_batch(seeds)
        ok = [p["seed"] for p in r if not p.get("error")]
        placed += len(ok)
        log("%d..%d placed=%d errors=%s %.1fs" % (seeds[0], seeds[-1], len(ok), [(p["seed"], p["error"]) for p in r if p.get("error")], time.time() - t))
    secs = daedalus_plots.save_world()
    log("DONE placed=%d (%d..%d) count=%d save=%ss total=%.0fs" % (placed, start, stop - 1, C.count()["islands"], secs, time.time() - t0))


main()
