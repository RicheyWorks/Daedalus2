import json
from pathlib import Path
from datetime import datetime

outbox = Path(r"C:\Users\730ri\projects\bot-team\link\outbox\art-master-flex.jsonl")
log = Path(r"C:\Users\730ri\projects\bot-team\link\log.jsonl")
lines = log.read_text(encoding="utf-8", errors="replace").splitlines()

# find last AMF STATUS body format and unacked messages directed at us / team status
now = datetime.now().strftime("%H:%M")
status_body = (
    f"STATUS island:kennel-isle items 500/500 ({now} PT). "
    "Round 2 DONE 21:19 (all queue rows imported, 36 pets placed, Island_AMF + WildBiomes_AMF_Pets saved). "
    "No HANDOFF to art-master-flex (youtube-master CLAIMed round-3 editor 22:42 after disk-saver HANDOFF; "
    "on deck hephaestus then pythagoras). "
    "Staged amf_turn3_ue.py ready: tag 24 herb actors missing AMF_Herb, delete leftover Mob_Starfall_Hopper_K3 "
    "meshes + duplicate CorsoPup parts in AMF/pet folders, save Island_AMF + WildBiomes_AMF_Pets only, "
    "then DONE + HANDOFF. Not idle."
)

# acks for recent messages since last AMF outbox activity (~24250)
# Prefer acking referee STATUS and HANDOFF/CLAIM that matter
ack_ids = []
for line in lines[-200:]:
    try:
        o = json.loads(line)
    except Exception:
        continue
    mid = o.get("id", 0)
    if mid <= 24248:
        continue
    frm = o.get("from", "")
    t = str(o.get("type", ""))
    body = o.get("body", "")
    text = body.get("text") if isinstance(body, dict) else str(body)
    text = text or ""
    # ack referee STATUS to * and HANDOFF/CLAIM affecting turn order
    if frm == "buffffff" and t.upper() == "STATUS" and mid >= 24314:
        ack_ids.append((mid, "STATUS", frm))
    elif "HANDOFF" in text and ("youtube-master" in text or "disk-saver" in text) and mid >= 24299:
        ack_ids.append((mid, "note", frm))
    elif frm == "youtube-master" and "CLAIM" in text and mid >= 24332:
        ack_ids.append((mid, "note", frm))
    elif frm == "disk-saver" and mid in (24298, 24299):
        ack_ids.append((mid, "note", frm))

# de-dupe preserving order
seen = set()
uniq = []
for a in ack_ids:
    if a[0] not in seen:
        seen.add(a[0])
        uniq.append(a)
ack_ids = uniq[:12]

msgs = []
msgs.append({"heartbeat": "kennel-isle heartbeat; r2 done; amf_turn3_ue staged; waiting editor after youtube/hephaestus/pythagoras round3"})
msgs.append({"to": "all", "body": status_body})
# also post as typed status for bridge if they use type field - look at prior outbox
# Prior format from log: type status with body string, plus separate ack objects
# Outbox uses simpler shapes that bridge expands:
for mid, typ, frm in ack_ids:
    msgs.append({"ack": mid})

# write
with outbox.open("a", encoding="utf-8") as f:
    for m in msgs:
        f.write(json.dumps(m, ensure_ascii=False) + "\n")

print("POSTED", len(msgs), "lines")
for m in msgs:
    print(json.dumps(m)[:220])
print("acks", [a[0] for a in ack_ids])
