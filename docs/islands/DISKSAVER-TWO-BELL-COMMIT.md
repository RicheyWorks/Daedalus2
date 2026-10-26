# Two-Bell Commit (contest G144, DiskSaver Island)

Quest `q_two_bell_commit`, NPC **Harbourmaster Ines**. Code: `tools/streaming/two_bell_commit.py`,
tests `tools/streaming/two_bell_commit_test.py`, data `data/islands/disk-saver/two-bell-commit-v1.json`,
CI job `Two-Bell Commit`.

## Rules
- Saves are the G86 Compaction Shoals keys (read-only), each starting on its home island. The seeded plan has
  `moves` moves; each move is one transaction: the source island deletes the save, the destination writes it.
- A participant refuses with chance `refuse_permille` (full disk). The coordinator crashes with chance
  `crash_permille` while ringing the decision, after 0 or 1 participants heard it, and recovers `recover_ticks`
  later; each in-doubt participant holds its lock that long.
- Protocols: `one_bell` commits at once (a refusal or crash tears the move); `two_bell` prepares, votes, then
  rings the decision, but after a crash it presumes abort, tearing a move a participant already committed;
  `two_bell_log` logs the decision before ringing it and replays the log after a crash.
- A torn move leaves a save on no island (lost) or on two (doubled). Win: no torn move, every save on exactly
  one island, lock-hold ticks <= `max_blocked`, committed >= `min_committed`.

## Protocols (shipped data: 600 moves, 4% refusals, 3% crashes, 12-tick recovery, lock budget 400)
| Protocol | committed | torn | lost / doubled | lock ticks | Result |
|---|---|---|---|---|---|
| two_bell_log | 541 | 0 | 0 / 0 | 240 | won (seeds 1-5 all win) |
| one_bell | 530 | 53 | 24 / 24 | 0 | fails: torn |
| two_bell (no log) | 528 | 3 | 3 / 0 | 240 | fails: torn (presumed abort after a crash) |
| two_bell_log, 60-tick recovery | 541 | 0 | 0 / 0 | 1200 | fails: lock budget |

## Run
`python tools/streaming/two_bell_commit.py data/islands/disk-saver/two-bell-commit-v1.json [--protocol one_bell|two_bell|two_bell_log]`
