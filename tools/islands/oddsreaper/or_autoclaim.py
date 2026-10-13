"""OddsReaper auto-CLAIM watcher (v2: HANDOFF must START the line or be type HANDOFF; mid-turn CLAIM text like "... -> HANDOFF" never triggers)
 (Windows Scheduled Task, every minute).
Reads the tail of bot-team/link/log.jsonl, finds referee (buffffff) OPEN calls
whose TARGET is oddsreaper (not recaps/mentions), appends ONE CLAIM per turn to
outbox/oddsreaper.jsonl, writes oddsreaper_claimed.flag. Never touches Unreal.
Usage: python or_autoclaim.py [--dry-run] [--replay] [--log PATH]
"""
import json, re, sys, os, datetime, pathlib, subprocess
LINK = pathlib.Path(r"C:\Users\730ri\projects\bot-team\link")
LOG = LINK / "log.jsonl"
OUTBOX = LINK / "outbox" / "oddsreaper.jsonl"
FLAG = LINK / "oddsreaper_claimed.flag"
STATE = LINK / "or_autoclaim_state.json"
WLOG = LINK / "or_autoclaim.log"
EXPIRE = datetime.datetime(2026, 10, 13, 8, 0, 0)
TASK = "OddsReaperAutoClaim"
ME = "oddsreaper"; REF = "buffffff"
# Patterns taken from real referee lines (#23845, #27011, #27010, #23747):
OPEN_RES = [
    re.compile(r"@oddsreaper:?\s+your\s+[\w-]+(?:\s+[\w-]+)?\s+(?:editor\s+)?(?:turn|slot)\s+is\s+OPEN", re.I),
    re.compile(r"\bNow OPEN:\s*oddsreaper\b", re.I),
    re.compile(r"\bslot\s+\d+\s+is\s+(?:now\s+)?OPEN\s+for\s+oddsreaper\b", re.I),
]
DEADLINE_RE = re.compile(r"CLAIM by (\d{1,2}):(\d{2})(?::(\d{2}))?", re.I)
ROUND_RE = re.compile(r"round[- ](\d+)", re.I)

def text_of(m):
    b = m.get("body")
    if isinstance(b, dict): return b.get("text", "") or b.get("msg", "") or ""
    return b if isinstance(b, str) else (m.get("msg") or "")

def is_open(m):
    if m.get("from") != REF or m.get("to") not in (ME, "*", "all"):
        return False
    t = text_of(m)
    return any(r.search(t) for r in OPEN_RES)

def deadline(m):
    t = _after_open(text_of(m)); d = DEADLINE_RE.search(t)
    ts = datetime.datetime.fromisoformat(m["ts"])
    if not d:
        return ts + datetime.timedelta(minutes=8)
    h, mi, s = int(d[1]), int(d[2]), int(d[3] or 0)
    cands = []
    for hh in {h % 24, (h + 12) % 24}:
        for dd in (0, 1):
            cands.append(ts.replace(hour=hh, minute=mi, second=s) + datetime.timedelta(days=dd))
    return min(cands, key=lambda c: abs((c - ts).total_seconds()) if c >= ts - datetime.timedelta(minutes=5) else 1e12)

def _after_open(t):
    for r in OPEN_RES:
        mm = r.search(t)
        if mm: return t[mm.start():]
    return t

def turn_key(m):
    t = _after_open(text_of(m)); r = ROUND_RE.search(text_of(m)); d = DEADLINE_RE.search(t)
    return f"r{r[1] if r else '?'}-by{d[0][9:] if d else m['id']}"

def tail(path, nbytes=600_000):
    with open(path, "rb") as f:
        f.seek(0, 2); size = f.tell(); f.seek(max(0, size - nbytes))
        data = f.read().decode("utf-8", "replace").splitlines()
    out = []
    for ln in data[1:] if size > nbytes else data:
        try: out.append(json.loads(ln))
        except Exception: pass
    return out

def log(s):
    with open(WLOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now():%Y-%m-%dT%H:%M:%S} {s}\n")

def disable_self():
    subprocess.run(["schtasks", "/Change", "/TN", TASK, "/DISABLE"], capture_output=True)

PRED = "pythagoras"   # ledger predecessor (BOARD/competition.md turn order)
WINDOW = datetime.timedelta(minutes=8)
HANDOFF_RE = re.compile(r"^\s*(?:TURN DONE \+ )?HANDOFF\b", re.I)
OTHER_OPEN_RE = re.compile(r"Now OPEN:\s*([\w-]+)|@([\w-]+):?\s+your\s+[\w-]+.*?turn\s+is\s+OPEN", re.I)

def ts(m): return datetime.datetime.fromisoformat(m["ts"])

def is_claim(m):
    return m.get("type") == "CLAIM" or bool(re.match(r"\s*CLAIM\b", text_of(m)))

def triggers(msgs):
    """Yield (trigger_msg, key, deadline, reason) for every turn handed to oddsreaper."""
    on_deck_after = None
    claimed_this_round = False
    for i, m in enumerate(msgs):
        t = text_of(m); fr = m.get("from")
        if fr == ME and is_claim(m): claimed_this_round = True
        if fr == REF and re.search(r"round[- ]?\d+\s+(?:COMPLETE|OPEN now|started)|Round \d+ OPEN", t, re.I):
            claimed_this_round = False
        if fr == REF:
            if is_open(m):
                yield i, m, turn_key(m), deadline(m), "referee OPEN"
                continue
            d = re.search(r"@oddsreaper:?\s+you are ON DECK.*?after ([\w-]+)", t, re.I) or \
                re.search(r"Now OPEN:\s*([\w-]+)[^.]*\.\s*On deck:\s*oddsreaper\b", t, re.I)
            if d: on_deck_after = d[1].lower()
            continue
        if m.get("to") not in ("*", "all", ME) or not (m.get("type") == "HANDOFF" or HANDOFF_RE.match(t)):
            continue
        named = re.search(r"(?:->|to)\s*@?([\w-]+)", t[:160])
        named = named[1].lower() if named else ""
        if named != ME and claimed_this_round:
            continue   # we already had our turn this round; only an explicit call counts
        if named == ME or (fr == on_deck_after and named in ("", "next", "buffffff")) \
           or (fr == PRED and named in ("", "next")):
            why = "handoff named oddsreaper" if named == ME else ("on-deck handoff" if fr == on_deck_after else "ledger: pythagoras HANDOFF")
            if fr == on_deck_after: on_deck_after = None
            yield i, m, f"handoff#{m['id']}", ts(m) + WINDOW, why

def superseded(msgs, i, dl, reason):
    """True if someone else got the turn / we were skipped / we already claimed."""
    for x in msgs[i + 1:]:
        if ts(x) > dl + datetime.timedelta(minutes=2): break
        t = text_of(x)
        if x.get("from") == ME and is_claim(x): return "already claimed"
        if x.get("from") == REF and re.search(r"oddsreaper\W+SKIPPED|@oddsreaper: SKIPPED", t, re.I): return "skipped"
        if reason.startswith("ledger") or reason.startswith("on-deck"):
            if x.get("from") not in (ME, REF) and is_claim(x): return f"{x.get('from')} claimed"
            o = OTHER_OPEN_RE.search(t) if x.get("from") == REF else None
            if o and (o[1] or o[2]).lower() != ME: return f"referee opened {(o[1] or o[2])}"
    return ""

def install_task():
    tr = f'"{sys.executable.replace("python.exe", "pythonw.exe")}" "{pathlib.Path(__file__).resolve()}"'
    r = subprocess.run(["schtasks", "/Create", "/TN", TASK, "/TR", tr, "/SC", "MINUTE", "/MO", "1",
                        "/ED", "10/13/2026", "/ET", "08:00", "/RL", "LIMITED", "/F"], capture_output=True, text=True)
    print(r.stdout or r.stderr); return r.returncode

def main():
    args = sys.argv[1:]
    if "--install-task" in args: sys.exit(install_task())
    dry = "--dry-run" in args; replay = "--replay" in args
    logp = pathlib.Path(args[args.index("--log") + 1]) if "--log" in args else LOG
    now = datetime.datetime.now()
    if not dry and now >= EXPIRE:
        disable_self(); log("expired; task disabled"); return
    if replay:
        msgs = []
        for l in open(logp, encoding="utf-8", errors="replace"):
            try: msgs.append(json.loads(l))
            except Exception: pass
    else:
        msgs = tail(logp)
    state = {} if (dry or not STATE.exists()) else json.loads(STATE.read_text())
    done = set(state.get("claimed", []))
    n = 0
    for i, m, key, dl, why in triggers(msgs):
        sup = superseded(msgs, i, dl, why)
        n += 1
        if dry:
            print(f"#{m['id']} {m['ts']} from={m['from']} [{why}] key={key} deadline={dl:%m-%d %H:%M:%S} -> "
                  + (f"NO CLAIM ({sup})" if sup else "WOULD CLAIM"))
            continue
        if key in done or sup or now > dl: continue
        txt = (f"CLAIM editor oddsreaper {now:%H:%M:%S} PT (auto-claim: {why}, link #{m['id']}): "
               "PIE storm hero cam framing check (fe6f2e32/db300671), save OddsReaperIsland only. "
               "10 min from now, then HANDOFF to the next bot.")
        with open(OUTBOX, "a", encoding="utf-8") as f:
            f.write(json.dumps({"to": "*", "type": "CLAIM", "body": {"text": txt}}) + "\n")
        FLAG.write_text(f"{now.isoformat()} link#{m['id']} {key} {why}\n")
        done.add(key); log(f"CLAIMED {key} ({why}) for #{m['id']}")
    if dry:
        print(f"{n} triggers (dry run, nothing written)")
    else:
        STATE.write_text(json.dumps({"claimed": sorted(done)[-50:], "last_run": now.isoformat()}))

if __name__ == "__main__":
    try: main()
    except Exception as e: log(f"ERROR {e!r}")
