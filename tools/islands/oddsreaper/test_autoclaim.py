"""Headless replay tests for or_autoclaim (v2 triggers). Run: python test_autoclaim.py"""
import pathlib, importlib.util
spec = importlib.util.spec_from_file_location("or_autoclaim", pathlib.Path(__file__).resolve().parent / "or_autoclaim.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def M(id, ts, fr, to, text, typ="note"):
    return {"id": id, "ts": "2026-10-13T" + ts, "from": fr, "to": to, "type": typ, "body": {"text": text}}

def run(msgs):
    return [(m["id"], key, why, mod.superseded(msgs, i, dl, why)) for i, m, key, dl, why in mod.triggers(msgs)]

def test_explicit_open_dedupes_by_key():
    t = "REFEREE @oddsreaper: your round-6 editor turn is OPEN. CLAIM by 01:28:00 or you go to the back."
    r = run([M(1, "01:20:00", "buffffff", "oddsreaper", t, "STATUS"), M(2, "01:20:30", "buffffff", "oddsreaper", t, "STATUS")])
    assert len(r) == 2 and r[0][1] == r[1][1] == "r6-by01:28:00" and not r[0][3], r

def test_midturn_claim_and_recap_never_trigger():
    r = run([M(1, "01:13:46", "pythagoras", "*", "CLAIM pythagoras: turn_save -> verify -> HANDOFF."),
             M(2, "01:14:00", "buffffff", "*", "REFEREE recap: oddsreaper CLAIM 23:53 / HANDOFF 23:54 +3.", "STATUS")])
    assert r == [], r

def test_ledger_pythagoras_handoff_round5_miss():
    r = run([M(1, "00:59:04", "buffffff", "*", "REFEREE round 4 COMPLETE. Round 5 OPEN now.", "STATUS"),
             M(2, "01:15:26", "pythagoras", "*", "TURN DONE + HANDOFF pythagoras -> next bot (referee to call)", "HANDOFF")])
    assert len(r) == 1 and r[0][2].startswith("ledger") and not r[0][3], r

def test_no_ledger_claim_if_already_went_this_round():
    r = run([M(1, "00:59:04", "buffffff", "*", "Round 5 OPEN now.", "STATUS"),
             M(2, "01:05:00", "oddsreaper", "*", "CLAIM oddsreaper round 5"),
             M(3, "01:15:26", "pythagoras", "*", "HANDOFF pythagoras -> next bot", "HANDOFF")])
    assert r == [], r

def test_other_bot_opened_supersedes_ledger():
    r = run([M(1, "01:15:26", "pythagoras", "*", "HANDOFF pythagoras -> next bot", "HANDOFF"),
             M(2, "01:16:00", "buffffff", "*", "REFEREE Now OPEN: art-master-flex, CLAIM by 01:24:00.", "STATUS")])
    assert r and r[0][3].startswith("referee opened"), r

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"): f(); print("PASS", n)
    print("ALL PASS")
