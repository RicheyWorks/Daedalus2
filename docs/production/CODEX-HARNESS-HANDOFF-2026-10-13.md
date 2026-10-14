# Codex harness handoff — 2026-10-13

## Narrow upgrade
This branch is stacked on Poot PR89 (a303d9e2668ac26db451969b4178e0af70d3f3d7).
After CIM accepts a pc-job child, failure writing its .started receipt now warns but still
returns `started <id> pid=<pid>` with success. Use explicit `-Wait -Id`; never relaunch an
accepted job just because its receipt could not be written. Existing child failure codes,
atomic completion markers and CIM refusal behavior remain covered.

Validation: `python engines/unreal/core-test/pc_job_test.py` on native Windows.
The regression uses a CIM stand-in and executes its captured synthetic child command;
no real CIM launch, editor call, engine installation or reload is performed.

## Integration order and preserved editor state
Review PR89 plus this follow-up before installing. Current stable live-team client remains
at aae0f1bd7cbfb0cc657b63c1aea184e67d95142d; recipient validation PR86 is also uninstalled.
Poot PR96 base construction and PR99 PNG capture remain separate review candidates.
Poot owns the saved Unreal handoff, team message29276:
`C:/Users/730ri/Documents/Codex/2026-10-13/task-3/live/final_editor_handoff.evidence.json`.
Saved map SHA256:33768f3f9579255cbc697c2f29ed7c40e112cb9a0ba2f2635a451eb736ecfe2b.
Loaded source:b886df28b39dbb32484a94fd6304019218a9fee4.
No late engine reload is authorized by this handoff; coordinate the next editor lease first.
Construction/import success is not runtime traversal, collision, boarding or realm travel acceptance.

## Other pushed work
PR95 -> PR98 -> PR100 is the container resource, world recovery, Redis recovery stack.
PR100 head4098052c1c23209b62acf5b341d01c81ce7cc53e has actual Linux CI success:
https://github.com/RicheyWorks/Daedalus2/actions/runs/38513003829
Typed Redis leaderboard, TTL and world edits survived a stopped-source backup into distinct volumes.
This does not establish live concurrent backup consistency or public hosting readiness.
PR92 test storage isolation is merged; older stacked branches still require fresh explicit
world-file paths when running local production-profile tests.

Latest workbook:
`C:/Users/730ri/Documents/Codex/2026-10-13/redis-tracker/outputs/01a13192-73df-7d32-8fae-49ff6efe1bee/Realm-production.xlsx`.
Remaining product work includes runtime realm/vehicle tests, Ocean host wiring, native Portal
session integration, populations and quests, cooked client verification and public deployment.
The full metaverse goal is unfinished. All source changes require normal review before integration.

The Engines workflow includes the PR89 base branch so this stacked follow-up receives
Windows pc-job and existing engine-free integration checks before merging.


## Unreal build-launch follow-up
The branch stacked on PR101 changes unreal-job.ps1 Start only: GUID-suffixed build IDs,
terminating CIM errors, and explicit rejection of nonzero return values or missing PIDs.
The new unreal_job_launch_test.py freezes the clock and checks two accepted launches plus
three refusal/transport cases. It captures but NEVER executes -Run. No actual engine build,
restart, autosave restoration or project configuration write occurs in this fixture.
Local native Windows result: all five cases passed in1.927s. Existing pc-job cases remain
in the same CI job; the workflow also covers the PR101 dependency base.
Known remaining issues outside this change: build completion markers/Wait exit status,
error handling before the current Run try block, and fail-closed git pull handling still
need dedicated review. Start acceptance must never be described as build success.


## Build completion follow-up, stacked on PR102
Unreal -Wait now validates the completion marker and returns the actual failed code. Invalid
markers fail closed; compiler errors without a marker remain RUNNING diagnostics. A zero
marker with compiler errors fails. Completion writes use .tmp then same-directory rename.
Native synthetic regressions exercise stale success text, malformed/overflow/multiple markers,
preflight code2, child code23, live diagnostics and marker replacement. No build/editor calls.
Earlier Run-stage exceptions outside its current try block and fail-closed git pull handling
remain follow-ups; this change does not claim all build lifecycle failures are covered.
