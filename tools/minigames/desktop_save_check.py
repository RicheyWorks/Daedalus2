"""In-editor save/restore check for the 12 desktop-arcade games (ADaedalusDesktopArcade).

Default is --dry-run: prints the plan and touches nothing. --run drives the editor through the
authorized bridge (127.0.0.1:9877, execute_python) and needs:
  * the team-link `unreal` lease held by --owner (checked via GET <hub>/locks),
  * no producer running (campaign active-status.json stage must be a saved/paused boundary),
  * editor on an allowed map, 0 dirty packages, not in Play.
It starts ONE Play-in-Editor session, spawns a transient arcade in the PIE world only (never the
editor level), and per game: StartGame -> advance -> SaveGame -> record .dgs -> RestartGame ->
ResumeGame -> compare the fields the C++ restores (Id, Score, Option). star_shooter uses its own
source-menu save, so manual SaveGame must be refused (SKIP-by-design). No level is saved.
Pre-existing .dgs files are backed up first and copied back afterwards.
Entry points read from DaedalusDesktopArcade.h/.cpp and DaedalusDesktopSaveSlots.h.
"""
import argparse, datetime, json, os, shutil, socket, sys, time, urllib.request

GAMES = ["beacon_sweep", "twinwake", "dungeon", "driftstone", "football", "glowtrail",
         "riftwing", "emberstep", "star_shooter", "dodge_ball", "ironwake", "lanternwild"]
SOURCE_MENU = {"star_shooter"}          # SaveStyle::SourceMenu in DaedalusDesktopSaveSlots.h
COMPARE_FIELDS = ("id", "score", "option")  # ResumeGame: "score and mode restored, positions start fresh"
ALLOWED_MAPS = ("/Game/Daedalus/Sandbox/NativeDiscovery/20261024/R18_C0030/L_GrandCollection_C0030",
                "/Game/Daedalus/Sandbox/NativeDiscovery/20261024/R18_C0198/L_GrandCollection_C0198")
SAVED_DIR = r"C:\Unreal\DaedalusRealm\Saved\DaedalusDesktopGames"
SAFE_STAGES = ("paused_saved_boundary", "stopped_saved_boundary", "complete", "completed")
SEED, WARMUP_S, PLAY_S, STEP = 730, 0.25, 6.0, 1.0 / 60.0


def save_file(game):
    return game + ".dgs"


def build_plan(games=GAMES):
    plan = []
    for g in games:
        if g not in GAMES:
            raise ValueError("unknown game id: " + g)
        steps = ["StartGame(%r,%d)" % (g, SEED), "AdvanceGame warmup+play %.1fs" % (WARMUP_S + PLAY_S)]
        if g in SOURCE_MENU:
            steps += ["SaveGame() must return False (source-menu save)", "no restore compare"]
            expect = "skip_source_menu"
        else:
            steps += ["SaveGame() -> True", "record " + save_file(g), "RestartGame()", "ResumeGame() -> True",
                      "compare " + ",".join(COMPARE_FIELDS)]
            expect = "manual_save"
        plan.append({"game": g, "file": save_file(g), "expect": expect, "steps": steps})
    return plan


def compare_states(before, after, fields=COMPARE_FIELDS):
    diffs = {f: [before.get(f), after.get(f)] for f in fields if before.get(f) != after.get(f)}
    return not diffs, diffs


def judge(game, result):
    """result: dict from the in-editor payload for one game. Returns (verdict, reason)."""
    if result.get("error"):
        return "FAIL", result["error"]
    if game in SOURCE_MENU:
        return ("SKIP", "source-menu save; manual SaveGame refused as designed") if result.get("saved") is False \
            else ("FAIL", "manual SaveGame unexpectedly accepted for source-menu game")
    if not result.get("saved"):
        return "FAIL", "SaveGame returned False: %s" % result.get("message", "")
    size = result.get("file_bytes") or 0
    if not 0 < size <= 4096:
        return "FAIL", "save file missing or out of bounds (%s bytes)" % size
    if not result.get("resumed"):
        return "FAIL", "ResumeGame returned False: %s" % result.get("message", "")
    ok, diffs = compare_states(result.get("before", {}), result.get("after", {}))
    if not ok:
        return "FAIL", "restored state differs: %s" % json.dumps(diffs)
    if (result.get("before") or {}).get("score", 0) == 0:
        return "PASS", "restored (weak: score 0 at save)"
    return "PASS", "restored"


def safe_stage(status):
    stage = (status or {}).get("stage", "")
    return stage in SAFE_STAGES


# ---------------- editor side (only used with --run) ----------------
PAYLOAD = r'''
import unreal, json, os
GAMES_V = __GAMES__
SRC_V = __SRC__
SEED_V, WARM_V, PLAY_V, STEP_V = __NUMS__
DIR_V = __DIR__
def st(arc):
    s = arc.get_state()
    return {"id": s.id, "score": int(s.score), "option": int(s.option), "lives": int(s.lives),
            "steps": int(s.steps), "over": bool(s.b_over), "has_saved": bool(s.b_has_saved_run), "note": s.note}
def adv(arc, seconds, inp):
    n = int(seconds / STEP_V)
    for i in range(n):
        arc.set_arcade_input(inp(i)); arc.advance_game(STEP_V)
    arc.set_arcade_input(unreal.DaedalusDesktopArcadeInput())
gw = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if gw is None: raise RuntimeError("PIE world not available")
xf = unreal.Transform(location=[0.0, 0.0, -100000.0])
arc = unreal.GameplayStatics.begin_deferred_actor_spawn_from_class(gw, unreal.DaedalusDesktopArcade, xf)
arc.set_editor_property("auto_advance", False)
unreal.GameplayStatics.finish_spawning_actor(arc, xf)
out = {}
def press(i):
    p = unreal.DaedalusDesktopArcadeInput()
    p.action_pressed = p.fire_pressed = p.jump_pressed = (i == 0)
    return p
def play(i):
    p = unreal.DaedalusDesktopArcadeInput()
    p.fire = True; p.fire_pressed = (i % 20 == 0); p.action_pressed = (i % 30 == 0)
    p.right = (i // 90) % 2 == 0; p.left = not p.right; p.up = (i // 45) % 2 == 0
    return p
for g in GAMES_V:
    r = {}
    try:
        if not arc.start_game(g, SEED_V): raise RuntimeError("StartGame refused")
        adv(arc, WARM_V, press); adv(arc, PLAY_V, play)
        r["before"] = st(arc)
        if r["before"]["over"]:
            arc.restart_game(); adv(arc, WARM_V, press); adv(arc, 1.0, play); r["before"] = st(arc)
        r["saved"] = bool(arc.save_game())
        r["message"] = arc.get_state().persistence_message
        f = os.path.join(DIR_V, g + ".dgs")
        r["file_bytes"] = os.path.getsize(f) if os.path.exists(f) else 0
        if r["saved"] and g not in SRC_V:
            arc.restart_game(); r["reset"] = st(arc)
            r["resumed"] = bool(arc.resume_game())
            r["message"] = arc.get_state().persistence_message
            r["after"] = st(arc)
    except Exception as e:
        r["error"] = repr(e)
    out[g] = r
arc.close_arcade(); arc.destroy_actor()
print("DSC_RESULT " + json.dumps(out))
'''


def payload(games):
    return (PAYLOAD.replace("__GAMES__", repr(list(games))).replace("__SRC__", repr(sorted(SOURCE_MENU)))
            .replace("__NUMS__", repr((SEED, WARMUP_S, PLAY_S, STEP))).replace("__DIR__", repr(SAVED_DIR)))


def bridge(code, port, timeout=300):
    s = socket.create_connection(("127.0.0.1", port), timeout=timeout)
    msg = {"id": "desktop-save-check-%d" % int(time.time() * 1000), "type": "execute_python",
           "params": {"code": code, "unattended": False}}
    s.sendall((json.dumps(msg) + "\n").encode())
    buf = b""
    while not buf.endswith(b"\n"):
        c = s.recv(65536)
        if not c:
            break
        buf += c
    s.close()
    reply = json.loads(buf.decode())
    if reply.get("status") != "ok":
        raise RuntimeError("bridge error: %s" % json.dumps(reply)[:2000])
    return (reply.get("result") or {}).get("stdout", "")


STATE_CODE = r'''
import unreal, json
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
d = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()] + \
    [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
print("DSC_STATE " + json.dumps({"world": w.get_path_name().split(".")[0], "dirty": d,
      "play": unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor()}))
'''


def tagged(text, tag):
    for line in text.splitlines():
        if line.startswith(tag + " "):
            return json.loads(line[len(tag) + 1:])
    raise RuntimeError("no %s in bridge output: %s" % (tag, text[:1000]))


def editor_state(port):
    return tagged(bridge(STATE_CODE, port), "DSC_STATE")


def wait_play(port, want, timeout=120):
    end = time.time() + timeout
    while time.time() < end:
        if editor_state(port)["play"] == want:
            return
        time.sleep(1.0)
    raise RuntimeError("Play state did not become %s" % want)


def preflight(args):
    locks = json.load(urllib.request.urlopen(args.hub + "/locks", timeout=10))
    holder = (locks.get("unreal") or {}).get("holder")
    if holder != args.owner:
        raise SystemExit("BLOCKED: unreal lease holder is %r, need %r" % (holder, args.owner))
    if args.campaign_status and os.path.exists(args.campaign_status):
        status = json.load(open(args.campaign_status, encoding="utf-8"))
        if not safe_stage(status):
            raise SystemExit("BLOCKED: producer stage %r is not a saved boundary" % status.get("stage"))
    s = editor_state(args.port)
    if s["play"] or s["dirty"] or s["world"] not in ALLOWED_MAPS:
        raise SystemExit("BLOCKED: editor not clean/allowed: %s" % json.dumps(s))
    return s


def run(args, games):
    start = preflight(args)
    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    backup = os.path.join(args.out, "dgs-backup-" + stamp)
    os.makedirs(backup, exist_ok=True)
    existing = [f for f in os.listdir(SAVED_DIR)] if os.path.isdir(SAVED_DIR) else []
    for f in existing:
        if os.path.isfile(os.path.join(SAVED_DIR, f)):
            shutil.copy2(os.path.join(SAVED_DIR, f), os.path.join(backup, f))
    results, error = {}, None
    bridge("import unreal\nunreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()", args.port)
    try:
        wait_play(args.port, True)
        time.sleep(3.0)
        results = tagged(bridge(payload(games), args.port), "DSC_RESULT")
    except Exception as e:  # always end Play
        error = repr(e)
    finally:
        bridge("import unreal\nunreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()", args.port)
        wait_play(args.port, False)
    for f in existing:  # put the player's own saves back
        src = os.path.join(backup, f)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(SAVED_DIR, f))
    end = editor_state(args.port)
    table = []
    for g in games:
        v, why = judge(g, results.get(g, {"error": error or "no result"}))
        table.append({"game": g, "verdict": v, "reason": why, "detail": results.get(g)})
    clean = (not end["play"]) and not end["dirty"] and end["world"] == start["world"]
    report = {"utc": datetime.datetime.utcnow().isoformat() + "Z", "start": start, "end": end, "end_clean": clean,
              "error": error, "backup": backup, "results": table}
    path = os.path.join(args.out, "desktop-save-check-%s.json" % stamp)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    for row in table:
        print("%-13s %-4s %s" % (row["game"], row["verdict"], row["reason"]))
    print("end_clean=%s report=%s" % (clean, path))
    return 0 if clean and all(r["verdict"] != "FAIL" for r in table) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=True, help="print the plan only (default)")
    mode.add_argument("--run", action="store_true", help="drive the editor (needs unreal lease, producer stopped)")
    ap.add_argument("--games", default=",".join(GAMES))
    ap.add_argument("--port", type=int, default=9877)
    ap.add_argument("--hub", default="http://127.0.0.1:9890")
    ap.add_argument("--owner", default="unreal-epic-boss")
    ap.add_argument("--campaign-status", default=r"C:\Users\730ri\Documents\Codex\2026-10-14\task-2"
                    r"\campaign-integration-20261024\GrandCollectionR18\active-status.json")
    ap.add_argument("--out", default=os.getcwd())
    args = ap.parse_args(argv)
    games = [g for g in args.games.split(",") if g]
    plan = build_plan(games)
    if not args.run:
        print(json.dumps({"mode": "dry-run", "allowed_maps": ALLOWED_MAPS, "saved_dir": SAVED_DIR, "plan": plan}, indent=1))
        return 0
    return run(args, games)


if __name__ == "__main__":
    sys.exit(main())