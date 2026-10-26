# The connector's harness

This harness proves the bridge works, and proves the proof can fail. It is target-neutral and uses only the
standard library, so any agent on the team can run it against the stand-in editor (no Unreal needed) or a
real editor's bridge on port 9877.

| Command | What it does |
|---|---|
| `python -m harness.run_all -j 3` | Runs every suite in `suites.json` and judges each one: ok, FAIL, FAIL*, SHORT (below its floor) or EMPTY. Writes `ledgers/runs.json`. |
| `python -m harness.e2e` | Runs the MCP extension over stdio, as Claude does, against the stand-in editor. |
| `python -m harness.contract` | Checks the risk ladder, policy refusals, "DESTRUCTIVE needs MUTATE", and request_id replay. |
| `python -m harness.walk --standin` | Drives every listed command from its declared params. Every command must be accounted for. Writes `ledgers/walk.json`. |
| `python -m harness.walk --port 9877 --max-risk SENSITIVE_READ` | Walks a live editor without changing anything. |

The patterns come from the CSRBT and FlowersForever harnesses:
- **A gateway contract with a risk ladder.** Every command declares a risk (READ, SENSITIVE_READ, MUTATE,
  DESTRUCTIVE), and a policy says which risks run.
- **A walk robot with an accounting identity.** Every command the bridge lists is driven, refused, declined,
  excluded with a reason, or counted as a failure, and the totals must add up.
- **Per-suite floors.** A suite that counts fewer checks than its floor is red, even if it exits 0.
- **Ledgers instead of hand-typed numbers.** The results are written by the tools themselves.

Next: a mutant runner (deliberate breaks that a suite must catch) and a board page rendered from the ledgers.
