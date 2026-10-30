# SPDX-License-Identifier: MIT
"""Read-only verifier for an R22 producer session that saved its last chunk but failed at lease release.

It proves, from files plus two read-only probes (process liveness, broker GET /locks), that:
  - the failure is a release-stage broker connection failure, not a save/native failure;
  - ledger saved == source counts, both kinds equal, contiguous chunk history, next_index == end + 1;
  - the latest native receipt is the ledger's last chunk, saved, clean (no dirty/play/import/sequence),
    and its item records cover exactly that chunk's range for both kinds;
  - the producer PID recorded in owner/lock/failure is not running (or the PID was reused by a process that
    started after the session's recorded start);
  - the coordinator lock names that same dead PID, owner and session (stale by that rule);
  - no newer source chunk or native receipt exists past the ledger; no STOP marker is unpinned;
  - the broker's current lease view is reported as-is (held by the lease owner / free / foreign).

It writes ONE attestation JSON (refuses any path inside the campaign root or the runs folder) whose
`attestation_sha256` is the SHA-256 of its canonical body. `check` re-hashes every pinned input, re-runs the
probes and refuses on any change. It never writes, renames, deletes or unlocks anything else, never touches
the editor, and never calls a broker write route.

    python verify_closeout.py attest --campaign-root <dir> --session <dir> --out <file> [--broker URL]
    python verify_closeout.py check  --attestation <file> [--broker URL]

Exit 0 = admissible, 1 = refused (reasons printed), 2 = bad input.
"""
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

SCHEMA = "daedalus-r22-closeout-attestation/1"
KINDS = ("skull", "toter")
RELEASE_ERRORS = ("WinError 10061", "Connection refused", "actively refused")


def sha_file(p):
    raw = Path(p).read_bytes()
    return {"path": str(Path(p).resolve()), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def canonical(body):
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def default_process(pid):
    """Return {'state': 'absent'|'running', 'start_utc': iso or None}. Read-only."""
    if os.name == "nt":
        cmd = ["powershell", "-NoProfile", "-Command",
               "$p=Get-Process -Id %d -EA 0; if($p){$p.StartTime.ToUniversalTime().ToString('o')}else{'ABSENT'}" % pid]
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout.strip()
        return {"state": "absent", "start_utc": None} if out in ("", "ABSENT") else {"state": "running", "start_utc": out}
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return {"state": "absent", "start_utc": None}
    except PermissionError:
        pass
    return {"state": "running", "start_utc": None}


def default_locks(broker):
    with urllib.request.urlopen(broker.rstrip("/") + "/locks", timeout=5) as r:
        return json.loads(r.read().decode())


def _instant(s):
    return datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00"))


def evaluate(campaign_root, session, process=default_process, locks=default_locks, broker="http://127.0.0.1:9890"):
    """Return (reasons, facts, inputs). reasons == [] means admissible."""
    base, sess = Path(campaign_root).resolve(), Path(session).resolve()
    reasons, facts = [], {}
    need = {"owner": base / "owner.json", "active": base / "active-status.json", "terminal": base / "owner-terminal.json",
            "ledger": base / "ledger.json", "session": sess / "session.json", "failure": sess / "failure.json",
            "lock": sess.parent / "active-owner.lock"}
    missing = [r for r, p in need.items() if not p.exists()]
    if missing:
        return ["missing inputs: " + ",".join(missing)], facts, {}
    d = {r: read(p) for r, p in need.items()}
    owner, ledger, failure, lock, session_j, active, terminal = (d[k] for k in
        ("owner", "ledger", "failure", "lock", "session", "active", "terminal"))
    pid = owner.get("pid")
    lease_owner = owner.get("lease_owner")
    facts.update(pid=pid, lease_owner=lease_owner)

    # 1. failure classification: release-stage broker connection failure only.
    err = str(failure.get("error", ""))
    if failure.get("stage") != "blocked" or not any(e in err for e in RELEASE_ERRORS):
        reasons.append("failure is not a broker-connection release failure")
    for role, j in (("active", active), ("terminal", terminal.get("status", {}))):
        if j != failure:
            reasons.append("%s status differs from failure.json" % role)
    if failure.get("owner_pid") != pid or terminal.get("pid") != pid:
        reasons.append("failure/terminal pid differs from owner pid")
    if Path(failure.get("r22_session", "")).resolve() != sess or Path(owner.get("r22_session", "")).resolve() != sess:
        reasons.append("session identity differs")
    for name in ("normal-lease-release.json", "released-producer-lock.json"):
        facts["has_" + name] = (sess / name).exists()

    # 2. ledger consistency.
    saved, src = ledger.get("saved_counts", {}), ledger.get("source_counts", {})
    chunks = ledger.get("completed_chunks") or []
    if not chunks:
        reasons.append("no completed chunks")
        return reasons, facts, {}
    end = chunks[-1]["range"][1]
    if saved != src or len({saved.get(k) for k in KINDS}) != 1 or saved.get("skull") != end:
        reasons.append("saved/source counts disagree or are not the chunk prefix")
    if ledger.get("next_index") != end + 1:
        reasons.append("next_index is not end + 1")
    prev = None
    for c in chunks:
        if prev and (c["chunk"] != prev["chunk"] + 1 or c["range"][0] != prev["range"][1] + 1):
            reasons.append("chunk history not contiguous at %s" % c["chunk"])
            break
        prev = c
    last = chunks[-1]
    facts.update(chunk=last["chunk"], saved=saved, next_index=ledger.get("next_index"))

    # 3. latest native receipt.
    rec_path = Path(ledger.get("last_native_receipt", ""))
    if rec_path.resolve() != Path(last["receipt"]).resolve() or not rec_path.exists():
        reasons.append("last native receipt missing or not the last chunk's")
        return reasons, facts, {}
    native = read(rec_path).get("native", {})
    if native.get("saved") is not True or native.get("dirty") != {"maps": [], "content": []}:
        reasons.append("native receipt not saved clean")
    for k in ("play", "open_sequence", "import_active"):
        if native.get(k) not in (False, None, "", "None"):
            reasons.append("native receipt %s not idle" % k)
    items = [r.get("source", r) for r in (native.get("item_records") or {}).values()]
    want = {(k, i) for k in KINDS for i in range(last["range"][0], end + 1)}
    if {(r.get("kind"), r.get("index")) for r in items} != want or len(items) != len(want):
        reasons.append("native item records do not cover exactly the last chunk range")
    lw = ledger.get("last_world", "")
    if not str(native.get("world", "")).startswith(lw):
        reasons.append("native world differs from ledger last_world")

    # 4. nothing past the ledger.
    nxt = "Chunk%04d" % (last["chunk"] + 1)
    for p in (base / "NativeReceipts" / (nxt + ".json"), base / "SourceChunks" / nxt):
        if p.exists():
            reasons.append("work past the ledger exists: %s" % p.name)
    if (base / "STOP-AFTER-CURRENT-CHUNK").exists():
        facts["stop_marker"] = sha_file(base / "STOP-AFTER-CURRENT-CHUNK")

    # 5. stale lock + dead producer.
    if lock.get("pid") != pid or lock.get("owner") != lease_owner or Path(lock.get("session", "")).resolve() != sess:
        reasons.append("coordinator lock does not name this producer/session")
    proc = process(pid)
    facts["process"] = proc
    if proc.get("state") == "running":
        started = proc.get("start_utc")
        if not started or _instant(started) <= _instant(session_j["started_utc"]):
            reasons.append("producer pid %s is still running" % pid)
        else:
            facts["pid_reused_after_session"] = True

    # 6. broker lease view (reported; foreign holders refuse).
    try:
        view = locks(broker)
        facts["leases"] = {n: {k: view.get(n, {}).get(k) for k in ("holder", "left_s")} for n in ("unreal", "compute")}
        for n in ("unreal", "compute"):
            h = view.get(n, {}).get("holder")
            if h not in (None, lease_owner):
                reasons.append("lease %s held by foreign %s" % (n, h))
    except Exception as e:  # broker down is a refusal: lease state must be known
        reasons.append("broker unreadable: %s" % e)

    inputs = {r: sha_file(p) for r, p in need.items()}
    inputs["native"] = sha_file(rec_path)
    return reasons, facts, inputs


def _inside(path, roots):
    p = Path(path).resolve()
    return any(p == r or r in p.parents for r in roots)


def attest(campaign_root, session, out, **kw):
    roots = [Path(campaign_root).resolve(), Path(session).resolve().parent]
    if _inside(out, roots):
        return ["refusing to write inside the campaign root or runs folder"], None
    reasons, facts, inputs = evaluate(campaign_root, session, **kw)
    body = {"schema": SCHEMA, "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "campaign_root": str(Path(campaign_root).resolve()), "session": str(Path(session).resolve()),
            "admissible": not reasons, "reasons": reasons, "facts": facts, "inputs": inputs}
    doc = dict(body, attestation_sha256=hashlib.sha256(canonical(body)).hexdigest())
    Path(out).write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return reasons, doc


def check(attestation, **kw):
    doc = read(attestation)
    body = {k: v for k, v in doc.items() if k != "attestation_sha256"}
    if hashlib.sha256(canonical(body)).hexdigest() != doc.get("attestation_sha256"):
        return ["attestation body hash differs"]
    if body.get("schema") != SCHEMA or not body.get("admissible"):
        return ["attestation not admissible"]
    reasons = []
    for role, row in body["inputs"].items():
        if not Path(row["path"]).exists() or sha_file(row["path"]) != row:
            reasons.append("pinned input changed: " + role)
    if reasons:
        return reasons
    try:
        now, _, _ = evaluate(body["campaign_root"], body["session"], **kw)
    except (OSError, ValueError, KeyError) as e:
        return ["re-evaluation failed: %s" % e]
    return now


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("attest")
    a.add_argument("--campaign-root", required=True)
    a.add_argument("--session", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--broker", default="http://127.0.0.1:9890")
    c = sub.add_parser("check")
    c.add_argument("--attestation", required=True)
    c.add_argument("--broker", default="http://127.0.0.1:9890")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "attest":
            reasons, doc = attest(args.campaign_root, args.session, args.out, broker=args.broker)
            if doc:
                print(json.dumps({"admissible": doc["admissible"], "facts": doc["facts"],
                                  "attestation_sha256": doc["attestation_sha256"]}, indent=1))
        else:
            reasons = check(args.attestation, broker=args.broker)
    except (OSError, ValueError, KeyError) as e:
        print("bad input: %s" % e)
        return 2
    for r in reasons:
        print("REFUSED: " + r)
    print("OK" if not reasons else "REFUSED")
    return 0 if not reasons else 1


if __name__ == "__main__":
    sys.exit(main())
