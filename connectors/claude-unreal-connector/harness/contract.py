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
    r = c("no.such")
    check("an unknown command is code UNKNOWN and lists the known ones",
          r.get("code") == "UNKNOWN" and "test.count" in r.get("message", ""), r)


def main():
    with standin() as port:
        run(port)
    print("%d/%d" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
