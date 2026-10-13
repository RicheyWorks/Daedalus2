"""Headless tests for or_autoclaim OPEN + HANDOFF-chain detection."""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("or_autoclaim", ROOT / "or_autoclaim.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def _m(id, ts, fr, to, text, typ="note"):
    return {"id": id, "ts": ts, "from": fr, "to": to, "type": typ, "body": {"text": text}}


def test_explicit_open():
    msgs = [
        _m(1, "2026-10-12T23:52:57", "buffffff", "oddsreaper",
           "REFEREE @oddsreaper: your round-4 editor turn is OPEN. CLAIM by 23:55:44 or you go to the back."),
    ]
    hits = mod.find_opens(msgs)
    assert len(hits) == 1
    assert hits[0]["handoff"] is False
    assert hits[0]["key"].startswith("r4-")


def test_now_open_form():
    msgs = [
        _m(2, "2026-10-13T01:26:54", "buffffff", "*",
           "REFEREE: oddsreaper SKIPPED. Now OPEN: art-master-flex, CLAIM by 01:34:00."),
    ]
    hits = mod.find_opens(msgs)
    assert hits == []


def test_handoff_from_pythagoras():
    msgs = [
        _m(26957, "2026-10-13T01:15:26", "pythagoras", "*",
           "TURN DONE + HANDOFF pythagoras -> next bot (referee to call) 01:15:26 PT (round 5)",
           typ="HANDOFF"),
    ]
    hits = mod.find_opens(msgs)
    assert len(hits) == 1
    assert hits[0]["handoff"] is True
    assert hits[0]["deadline"].isoformat(timespec="seconds") == "2026-10-13T01:23:26"


def test_claim_mention_not_handoff():
    msgs = [
        _m(26941, "2026-10-13T01:13:46", "pythagoras", "*",
           "CLAIM pythagoras 01:13:46 PT: round-2 editor turn. Running turn_save -> HANDOFF."),
    ]
    hits = mod.find_opens(msgs)
    assert hits == []


def test_explicit_handoff_to_oddsreaper():
    msgs = [
        _m(10, "2026-10-12T18:49:13", "pythagoras", "oddsreaper",
           "HANDOFF pythagoras -> oddsreaper 18:50: editor is yours.", typ="HANDOFF"),
    ]
    hits = mod.find_opens(msgs)
    assert len(hits) == 1
    assert hits[0]["handoff"] is True


def test_skipped_marks_closed():
    msgs = [
        _m(26455, "2026-10-12T23:52:57", "buffffff", "oddsreaper",
           "REFEREE @oddsreaper: your round-4 editor turn is OPEN. CLAIM by 23:55:44."),
        _m(27013, "2026-10-13T01:26:54", "buffffff", "oddsreaper",
           "REFEREE @oddsreaper: SKIPPED this round-5 slot (no CLAIM by 01:23:26)"),
    ]
    hits = mod.find_opens(msgs)
    assert len(hits) == 1
    assert hits[0]["closed"] is True


def test_already_claimed():
    msgs = [
        _m(26455, "2026-10-12T23:52:57", "buffffff", "oddsreaper",
           "REFEREE @oddsreaper: your round-4 editor turn is OPEN. CLAIM by 23:55:44."),
        _m(26473, "2026-10-12T23:53:10", "oddsreaper", "*",
           "CLAIM editor oddsreaper 23:53:10 PT"),
    ]
    hits = mod.find_opens(msgs)
    assert len(hits) == 1
    assert hits[0]["already"] is True


if __name__ == "__main__":
    test_explicit_open()
    test_now_open_form()
    test_handoff_from_pythagoras()
    test_claim_mention_not_handoff()
    test_explicit_handoff_to_oddsreaper()
    test_skipped_marks_closed()
    test_already_claimed()
    print("test_autoclaim: ALL PASS")
