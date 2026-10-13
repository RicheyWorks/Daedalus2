"""OddsReaper auto-CLAIM watcher (Windows Scheduled Task, every minute).
Reads the tail of bot-team/link/log.jsonl, finds referee OPEN calls whose
TARGET is oddsreaper, OR a predecessor HANDOFF when OddsReaper is next in the
round ledger, appends ONE CLAIM per turn to outbox/oddsreaper.jsonl, and
writes oddsreaper_claimed.flag. Never touches Unreal.
Usage: python or_autoclaim.py [--dry-run] [--replay] [--log PATH] [--install-task]
"""
import json, re, sys, os, datetime, pathlib, subprocess

LINK = pathlib.Path(r"C:\Users\730ri\projects\bot-team\link")
LOG = LINK / "log.jsonl"
OUTBOX = LINK / "outbox" / "oddsreaper.jsonl"
FLAG = LINK / "oddsreaper_claimed.flag"
STATE = LINK / "or_autoclaim_state.json"
WLOG = LINK / "or_autoclaim.log"
EXPIRE = datetime.datetime(2026, 10, 13, 8, 0, 0)  # contest morning window end
TASK = "OddsReaperAutoClaim"
ME = "oddsreaper"
REF = "buffffff"
# Round ledger order used when referee skips an explicit @oddsreaper OPEN
# (round-5 miss: pythagoras HANDOFF 01:15:26, CLAIM-by 01:23:26, no OPEN line).
LEDGER = [
    "disk-saver", "youtube-master", "hephaestus", "pythagoras",
    "oddsreaper", "art-master-flex", "blender-team", "prometheus",
    "2hot2trot", "unreal-team", "buffffff",
]
OPEN_RES = [
    re.compile(r"@oddsreaper:?\s+your\s+[\w-]+(?:\s+[\w-]+)?\s+(?:editor\s+)?(?:turn|slot)\s+is\s+OPEN", re.I),
    re.compile(r"\bNow OPEN:\s*oddsreaper\b", re.I),
    re.compile(r"\bslot\s+\d+\s+is\s+(?:now\s+)?OPEN\s+for\s+oddsreaper\b", re.I),
    re.compile(r"\bOPEN\s+for\s+oddsreaper\b", re.I),
]
DEADLINE_RE = re.compile(r"CLAIM by (\d{1,2}):(\d{2})(?::(\d{2}))?", re.I)
ROUND_RE = re.compile(r"round[- ](\d+)", re.I)
HANDOFF_FROM_RE = re.compile(r"HANDOFF\s+([\w-]+)\s*(?:->|to)", re.I)
CLAIM_START_RE = re.compile(r"^\s*CLAIM\b", re.I)
HANDOFF_ACT_RE = re.compile(r"(?is)^\s*(TURN DONE \+ )?HANDOFF\b")


def text_of(m):
    b = m.get("body")
    if isinstance(b, dict):
        return b.get("text", "") or b.get("msg", "") or ""
    if isinstance(b, str):
        return b
    return m.get("msg") or ""


def parse_ts(m):
    ts = m.get("ts")
    if not ts:
        return datetime.datetime.now()
    try:
        return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return datetime.datetime.now()


def is_open(m):
    if m.get("from") != REF or m.get("to") not in (ME, "*", "all"):
        return False
    t = text_of(m)
    return any(r.search(t) for r in OPEN_RES)


def ledger_prev():
    for i, name in enumerate(LEDGER):
        if name == ME and i > 0:
            return LEDGER[i - 1]
    return None


def is_handoff_open(m):
    """True when a predecessor hands off and OddsReaper is next in LEDGER."""
    fr = (m.get("from") or "").lower()
    if fr == ME or fr == REF:
        return False
    t = text_of(m)
    typ = (m.get("type") or "").upper()
    # Real handoff act only (not CLAIM/DONE notes that merely mention HANDOFF).
    if typ != "HANDOFF" and not HANDOFF_ACT_RE.match(t):
        return False
    if re.search(r"(?:->|to)\s+oddsreaper\b", t, re.I):
        return True
    prev = ledger_prev()
    if not prev:
        return False
    from_ok = fr == prev
    mfrom = HANDOFF_FROM_RE.search(t)
    if mfrom and mfrom.group(1).lower() == prev:
        from_ok = True
    if not from_ok:
        return False
    dest = re.search(r"(?:->|to)\s+([\w-]+)", t, re.I)
    if dest:
        d = dest.group(1).lower()
        if d in (ME, "next") or d.startswith("round"):
            return True
        # Named someone else (e.g. art-master-flex) — not us.
        if d != prev:
            return False
    return True


def deadline(m, handoff=False):
    t = text_of(m)
    d = DEADLINE_RE.search(t)
    ts = parse_ts(m)
    if not d:
        return ts + datetime.timedelta(minutes=8)
    h, mi, s = int(d.group(1)), int(d.group(2)), int(d.group(3) or 0)
    cands = []
    for hh in {h % 24, (h + 12) % 24}:
        for dd in (0, 1):
            cands.append(ts.replace(hour=hh, minute=mi, second=s) + datetime.timedelta(days=dd))
    return min(
        cands,
        key=lambda c: abs((c - ts).total_seconds())
        if c >= ts - datetime.timedelta(minutes=5)
        else 1e12,
    )


def turn_key(m, handoff=False):
    t = text_of(m)
    r = ROUND_RE.search(t)
    d = DEADLINE_RE.search(t)
    prefix = "h" if handoff else "r"
    rnd = r.group(1) if r else "?"
    by = d.group(0)[9:] if d else str(m.get("id"))
    return f"{prefix}{rnd}-by{by}"


def tail(path, nbytes=600_000):
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - nbytes))
        data = f.read().decode("utf-8", "replace").splitlines()
    out = []
    for ln in data[1:] if size > nbytes else data:
        try:
            out.append(json.loads(ln))
        except Exception:
            pass
    return out


def log(s):
    with open(WLOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now():%Y-%m-%dT%H:%M:%S} {s}\n")


def disable_self():
    subprocess.run(["schtasks", "/Change", "/TN", TASK, "/DISABLE"], capture_output=True)


def install_task():
    py = sys.executable
    script = str(pathlib.Path(__file__).resolve())
    tr = f'"{py}" "{script}"'
    cmd = [
        "schtasks", "/Create", "/TN", TASK, "/TR", tr,
        "/SC", "MINUTE", "/MO", "1", "/F",
        "/RL", "LIMITED",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout or r.stderr)
    return r.returncode


def find_opens(msgs):
    hits = []
    for i, m in enumerate(msgs):
        handoff = False
        if is_open(m):
            pass
        elif is_handoff_open(m):
            handoff = True
        else:
            continue
        key = turn_key(m, handoff=handoff)
        dl = deadline(m, handoff=handoff)
        later = msgs[i + 1:]
        already = any(
            (x.get("from") == ME)
            and CLAIM_START_RE.search(text_of(x))
            for x in later
        )
        already = already or any(
            CLAIM_START_RE.search(text_of(x)) and "oddsreaper" in text_of(x).lower()
            for x in later
            if x.get("from") in (ME, None, "")
        )
        closed = any(
            x.get("from") == REF
            and re.search(r"oddsreaper SKIPPED|@oddsreaper:\s*SKIPPED", text_of(x), re.I)
            for x in later
        )
        hits.append(
            {
                "id": m.get("id"),
                "ts": m.get("ts"),
                "key": key,
                "deadline": dl,
                "already": already,
                "closed": closed,
                "handoff": handoff,
                "msg": m,
            }
        )
    return hits


def main():
    args = sys.argv[1:]
    if "--install-task" in args:
        sys.exit(install_task())
    dry = "--dry-run" in args
    replay = "--replay" in args
    logp = pathlib.Path(args[args.index("--log") + 1]) if "--log" in args else LOG
    now = datetime.datetime.now()
    if not dry and now >= EXPIRE:
        disable_self()
        log("expired; task disabled")
        return
    if replay:
        msgs = []
        for l in open(logp, encoding="utf-8", errors="replace"):
            if l.strip().startswith("{"):
                try:
                    msgs.append(json.loads(l))
                except Exception:
                    pass
    else:
        msgs = tail(logp)
    state = {} if (dry or not STATE.exists()) else json.loads(STATE.read_text())
    done = set(state.get("claimed", []))
    hits = find_opens(msgs)
    for h in hits:
        if dry:
            print(
                "OPEN #%s %s key=%s deadline=%s already_claimed=%s skipped=%s handoff=%s"
                % (
                    h["id"],
                    h["ts"],
                    h["key"],
                    h["deadline"].isoformat(timespec="seconds"),
                    h["already"],
                    h["closed"],
                    h["handoff"],
                )
            )
            continue
        key = h["key"]
        if key in done or h["already"] or h["closed"] or now > h["deadline"]:
            continue
        txt = (
            f"CLAIM editor oddsreaper {now:%H:%M:%S} PT (auto-claim on "
            f"{'handoff' if h['handoff'] else 'referee'} #{h['id']}, {key}): "
            "PIE storm hero (framed SceneCapture + OR_TEMP cool lights) + save "
            "OddsReaperIsland only. 10 min from now, then HANDOFF to the next bot."
        )
        with open(OUTBOX, "a", encoding="utf-8") as f:
            f.write(json.dumps({"to": "*", "type": "CLAIM", "body": {"text": txt}}) + "\n")
        FLAG.write_text(f"{now.isoformat()} #{h['id']} {key}\n", encoding="utf-8")
        done.add(key)
        log(f"CLAIMED {key} for #{h['id']}")
    if dry:
        print(f"{len(hits)} oddsreaper OPEN/handoff triggers found (dry run, nothing written)")
    else:
        STATE.write_text(
            json.dumps({"claimed": sorted(done), "last_run": now.isoformat()}),
            encoding="utf-8",
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"ERROR {e!r}")
        raise
