# SPDX-License-Identifier: MIT
"""Reactive Battlefield Ecology (ADR-061) in-editor check, read-only apart from the events file it writes.
Needs the DaedalusLink plugin built from main (UDaedalusEcology) and a snapshot from BattlefieldCheck.java snap.
    python ../pcg-ecology/ue_send.py battlefield_check_ue.py 300
Loads Saved/Daedalus/ecology.dbe, asks cover/concealment/burning at the BattlefieldCheck.POINTS, queues one IGNITE on
the oak at 2000,1500 (r 150 cm) and writes Saved/Daedalus/ecology_events.dbe for BattlefieldCheck.java apply.
No actor is spawned, saved, imported or placed."""
import unreal

POINTS = [(900, 1500), (3900, 1500), (2000, 1500), (2500, 500), (100, 100)]
IGNITE_AT, IGNITE_R = (2000, 1500), 150.0


def run():
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    out = ["class_loaded=%s" % hasattr(unreal, "DaedalusEcology")]
    if not hasattr(unreal, "DaedalusEcology"):
        return out
    eco = unreal.DaedalusEcology.get_ecology(w)
    out.append("subsystem=%s" % (eco is not None))
    if not eco:
        return out
    out.append("load=%s err=%s" % (eco.load_snapshot(""), eco.last_error()))
    for x, y in POINTS:
        p = unreal.Vector(x, y, 0)
        out.append("UE %d,%d cover=%.3f conceal=%.3f burning=%s" % (x, y, eco.cover_at(p), eco.concealment_at(p), eco.burning_at(p)))
    out.append("queue=%s" % eco.queue_event(unreal.DaedalusEcologyEvent.IGNITE, unreal.Vector(IGNITE_AT[0], IGNITE_AT[1], 0), IGNITE_R))
    out.append("flush=%s err=%s stats=%s" % (eco.flush_events(""), eco.last_error(), eco.stats()))
    return out


print("BATTLEFIELD_CHECK " + " | ".join(run()))