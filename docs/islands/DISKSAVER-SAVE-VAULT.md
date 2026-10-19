# DiskSaver Island: Save Vault Keeper (contest G59, quest `q_save_vault`)

Under DiskSaver Island, the Archivist Ledger keeps every island's save snapshots on
vault shelves with a hard quota. It is the island's version of the real disk-saver rule:
**back it up and check it before you delete it, and never delete the newest work.**

## Story
After the Byte Spring (G39) was steadied, the caches it waters started writing saves
faster than the shelves could hold them. The Archivist asks the player to keep the vault
for one season (30 ticks): every island keeps its newest save, nothing is lost, and the
shelves never overflow. The Reef vault, across the lagoon, is the far backup. Copying to it
is slow, since only `mirror_kib_per_tick` KiB cross the lagoon each tick.

## Mechanics (code: `tools/streaming/save_vault.py`)
- A **snapshot** is a list of content-addressed chunks (`island:cN`). Chunks shared by
  snapshots are shelved once (**dedupe**), so vault use = the sum of the unique chunks.
- Each tick runs in this order:
  1. The player acts: `mirror` queues a snapshot for the Reef, and `prune` clears its shelf.
  2. The Reef upload runs in queue order and only sends chunks the Reef lacks. A snapshot
     is mirrored when all its chunks are on the Reef and its sha256 digest re-verifies.
  3. Islands write new snapshots (seeded `write_permille`). Each chunk is replaced with
     probability `churn_permille`.
  4. If the vault is over quota, the game is **failed: quota_overflow**.
  5. When `win_ticks` is reached, the game is **won**.
- **Pinned:** the newest snapshot of every island cannot be pruned (the Archivist refuses).
- **Loss:** pruning a snapshot that has not been mirrored is an instant **failed: lost_unmirrored**.
- Score on a win = free space kept, in permille of the quota.

## Daedalus tie-in
- Units are KiB, the DSB 1 streaming cost unit (ADR-063, `tools/streaming/dsb.py`).
- `quota_from_byte_spring()` sets the vault quota from the G39 Byte Spring cistern
  `budget_cap`. The shipped `save-vault-v1.json` uses that cap (600).
- `receipt()` returns a G12-style activity receipt (`activity: save_vault`).

## Checks
`python -m unittest tools/streaming/save_vault_test.py -v` covers strict validation, dedupe,
pinned refusal, loss on an unmirrored prune, the bandwidth cap, idle overflow, seeds 1-20
(the reference keeper wins and greedy pruning loses), LCG goldens, the G39 tie-in and the CLI.
The CI job is `Save Vault Keeper`. Source only, with no editor work. Later editor work:
vault shelves and a Reef mirror prop.
