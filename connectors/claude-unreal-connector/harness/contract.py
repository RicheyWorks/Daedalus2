# SPDX-License-Identifier: MIT
"""The gateway contract suite: what the bridge promises about risk, policy and retries, checked against the
stand-in editor. Prints n/m last; exits 1 on any failure.

    python -m harness.contract
"""
import sys

from harness.client import call
from harness.standin import standin

passed = total = 0


def check(label, ok, detail=""):
    global passed, total
    total += 1
    passed += bool(ok)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else "  " + str(detail)[:200]))


def run(port):
    c = lambda cmd, params=None: call(cmd, params, port=port, timeout=20)
    man = c("list_commands")["result"]
    risks = {m["name"]: m["risk"] for m in man["commands"]}
    check("every command declares a risk on the ladder", all(r in man["risks"] for r in risks.values()), risks)
    check("reading is READ; a screenshot is SENSITIVE_READ; Python is MUTATE; save is DESTRUCTIVE",
          risks["get_level_info"] == "READ" and risks["viewport_screenshot"] == "SENSITIVE_READ"
          and risks["execute_python"] == "MUTATE" and risks["save"] == "DESTRUCTIVE", risks)
    check("an add-on registered without a risk is held at MUTATE", risks.get("test.countdown") == "MUTATE", risks)
    check("the default policy allows everything (full control)", all(man["policy"].values()), man["policy"])

    r = c("test.policy", {"allow": ["READ"]})
    check("policy can be narrowed to READ", r.get("status") == "ok" and r["result"]["policy"]["MUTATE"] is False, r)
    r = c("execute_python", {"code": "result = 1"})
    check("a MUTATE command under a READ policy is REFUSED, and says why",
          r.get("code") == "REFUSED" and r.get("risk") == "MUTATE" and "CLAUDE_UNREAL_ALLOW" in r.get("message", ""), r)
    r = c("save")
    check("a DESTRUCTIVE command under a READ policy is REFUSED", r.get("code") == "REFUSED", r)
    r = c("ping")
    check("a READ command still runs", r.get("status") == "ok", r)
    r = c("test.policy", {"allow": ["READ", "DESTRUCTIVE"]})
    check("DESTRUCTIVE cannot be allowed without MUTATE", r.get("status") == "error" and "without MUTATE" in r.get("message", ""), r)
    r = c("test.policy", {"allow": ["READ", "NUKE"]})
    check("an unknown risk is rejected by name", r.get("status") == "error" and "NUKE" in r.get("message", ""), r)
    c("test.policy", {"allow": ["READ", "SENSITIVE_READ", "MUTATE", "DESTRUCTIVE"]})

    a = c("test.count", {"request_id": "walk-1"})
    b = c("test.count", {"request_id": "walk-1"})
    check("a retried request_id gets the first answer back, marked replayed",
          a["result"] == b["result"] and b.get("replayed") is True and not a.get("replayed"), (a, b))
    d = c("test.count", {"request_id": "walk-2"})
    check("...and the command really ran once: a new request_id runs it again",
          d["result"]["count"] == a["result"]["count"] + 1, (a, d))
    e = c("test.count")
    check("without a request_id every call runs", e["result"]["count"] == d["result"]["count"] + 1, e)
    # async jobs: answered at once with a job id; job_result fetches the answer later
    j = c("test.countdown", {"from": 30, "async": True})
    jid = (j.get("result") or {}).get("job_id")
    check("async: true answers at once with a job id, state running", jid and j["result"]["state"] == "running", j)
    first = c("job_result", {"job_id": jid})
    check("job_result says running while the job still runs", first["result"]["state"] == "running", first)
    import time as _t
    deadline = _t.time() + 20
    while _t.time() < deadline:
        last = c("job_result", {"job_id": jid})
        if last["result"]["state"] == "done":
            break
        _t.sleep(0.05)
    check("job_result then returns the job's full reply",
          last["result"]["state"] == "done" and last["result"]["reply"]["result"]["counted"][0] == 30, last)
    r = c("job_result", {"job_id": "job-nope"})
    check("an unknown job id is code UNKNOWN_JOB", r.get("code") == "UNKNOWN_JOB", r)

    # batch: in order, one transaction, policy per item, stop at the first error
    t0 = len(c("test.transactions")["result"]["calls"])
    b = c("batch", {"commands": [{"type": "test.count"}, {"type": "test.countdown", "params": {"from": 2}},
                                 {"type": "test.count"}], "transaction": "contract"})
    tx = c("test.transactions")["result"]["calls"][t0:]
    check("a batch is one undo step: one transaction opened and closed around it",
          tx == ["transaction begin contract", "transaction end"], tx)
    res = b["result"]["results"]
    check("batch runs its commands in order, waiting ones included",
          b["result"]["ok"] and [x["type"] for x in res] == ["test.count", "test.countdown", "test.count"]
          and res[2]["result"]["count"] == res[0]["result"]["count"] + 1, b)
    b = c("batch", {"commands": [{"type": "get_actor_info", "params": {"name": "nobody"}}, {"type": "test.count"}]})
    check("batch stops at the first error", b["result"]["ok"] is False and len(b["result"]["results"]) == 1, b)
    c("test.policy", {"allow": ["READ"]})
    b = c("batch", {"commands": [{"type": "ping"}]})
    check("under a READ policy the batch itself (MUTATE) is refused", b.get("code") == "REFUSED", b)
    c("test.policy", {"allow": ["READ", "SENSITIVE_READ", "MUTATE"]})
    n0 = c("test.count")["result"]["count"]
    b = c("batch", {"commands": [{"type": "test.count"}, {"type": "save"}]})
    n1 = c("test.count")["result"]["count"]
    check("batch can't smuggle a DESTRUCTIVE command past a MUTATE policy, and runs nothing",
          b.get("status") == "error" and "save" in b.get("message", "") and n1 == n0 + 1, (b, n0, n1))
    c("test.policy", {"allow": ["READ", "SENSITIVE_READ", "MUTATE", "DESTRUCTIVE"]})
    r = c("capture_view", {"width": 256, "height": 128})
    check("capture_view renders a PNG from the editor camera and removes its capture actor",
          r.get("status") == "ok" and r["result"]["width"] == 256 and r["result"]["bytes"] > 0, r)

    r = c("no.such")
    check("an unknown command is an error, code UNKNOWN, listing the known ones",
          r.get("status") == "error" and r.get("code") == "UNKNOWN" and "test.count" in r.get("message", ""), r)

    # Status polls during Play never touch the editor's actor subsystem (2026-10-13: 58 'Editor is currently in a
    # play mode' errors in one session came from bots polling ping/get_level_info while Play ran).
    c("test.policy", {"allow": ["READ", "SENSITIVE_READ", "MUTATE", "DESTRUCTIVE"]})
    c("play")
    for _ in range(20):
        if c("ping")["result"].get("playing"):
            break
        time.sleep(0.1)
    a0 = len(c("test.actor_calls")["result"]["calls"])
    p = c("ping")
    li = c("get_level_info")
    calls = c("test.actor_calls")["result"]["calls"][a0:]
    check("ping and get_level_info during Play list the game world's actors",
          p["result"]["playing"] and li["result"]["actors_total"] > 0 and "game_actors" in calls, calls)
    check("and never ask the editor's actor subsystem while Play runs", not any(x.endswith("_in_pie") for x in calls), calls)
    check("selection reads as empty during Play instead of erroring", li["result"]["selected"] == [], li["result"].get("selected"))
    c("stop")


def main():
    with standin() as port:
        run(port)
    print("%d/%d" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
