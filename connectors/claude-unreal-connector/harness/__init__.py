# SPDX-License-Identifier: MIT
"""The claude-unreal-connector harness: proves the bridge works, and proves the proof can fail.

Target-neutral and standard-library only, so any agent on the team can run it against the stand-in editor
(no Unreal needed) or against a real editor's bridge:

    python -m harness.walk --standin               # drive every command the bridge lists; ledger + n/m
    python -m harness.walk --port 9877 --max-risk SENSITIVE_READ   # a live editor, read-only
    python -m harness.mutate                       # break the bridge on purpose; every mutant must be caught
    python -m harness.run_all -j 3                 # every suite, floors enforced, one verdict
    python -m harness.board [--check]              # docs/board.html from the ledgers (no hand-typed numbers)

Patterns from the CSRBT and FlowersForever harnesses: a gateway contract with a risk ladder, a walk robot
with an accounting identity, mutant runners with a ledger, per-suite floors, and a board rendered from ledgers.
"""
