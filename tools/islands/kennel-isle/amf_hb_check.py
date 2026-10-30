import json
from pathlib import Path
from datetime import datetime

log = Path(r"C:\Users\730ri\projects\bot-team\link\log.jsonl")
outbox = Path(r"C:\Users\730ri\projects\bot-team\link\outbox\art-master-flex.jsonl")
lines = log.read_text(encoding="utf-8", errors="replace").splitlines()

print("LAST_ID", json.loads(lines[-1]).get("id"))
print("=== recent >=24270 HANDOFF/CLAIM/REFEREE/youtube/disk ===")
for line in lines[-150:]:
    try:
        o = json.loads(line)
    except Exception:
        continue
    if o.get("id", 0) < 24270:
        continue
    body = o.get("body", "")
    if isinstance(body, dict):
        text = body.get("text") or str(body)[:280]
    else:
        text = str(body)[:280]
    frm = o.get("from", "")
    t = str(o.get("type", ""))
    show = (
        "HANDOFF" in text
        or "CLAIM" in text
        or "REFEREE" in text
        or t.upper() in ("STATUS", "HANDOFF", "CLAIM")
        or frm in ("youtube-master", "disk-saver", "buffffff", "art-master-flex", "hephaestus", "pythagoras")
    )
    if show:
        print(f"#{o.get('id')} {o.get('ts')} {frm}->{o.get('to')} [{t}] {text[:300]}")

# detect if HANDOFF to art-master-flex is open (unclaimed)
print("=== HANDOFF scan for art-master-flex ===")
handoffs = []
claims = []
for line in lines[-400:]:
    try:
        o = json.loads(line)
    except Exception:
        continue
    body = o.get("body", "")
    text = body.get("text") if isinstance(body, dict) else str(body)
    text = text or ""
    low = text.lower()
    if "handoff" in low and ("art-master-flex" in low or "art master flex" in low or " amf" in low):
        handoffs.append((o.get("id"), o.get("ts"), o.get("from"), text[:200]))
    if "claim" in low and "art-master-flex" in low:
        claims.append((o.get("id"), o.get("ts"), text[:200]))
print("handoffs", handoffs[-5:])
print("claims", claims[-5:])
