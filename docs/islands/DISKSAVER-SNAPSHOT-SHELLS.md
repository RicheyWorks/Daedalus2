# Snapshot Shells (contest G113, DiskSaver Island)

Quest `q_snapshot_shells`, NPC **Shellwright Marrow**. Code: `tools/streaming/snapshot_shells.py`,
tests `tools/streaming/snapshot_shells_test.py`, data `data/islands/disk-saver/snapshot-shells-v1.json`,
CI job `Snapshot Shells`.

## Rules
- Saves are the G86 Compaction Shoals islands x keys_per_island (read-only), 1200 in the shipped data.
  Each window `writes_per_window` seeded writes bump save versions (the G59 Save Vault, now with history).
- At the end of each window a copy-on-write shell (snapshot) is pressed; the newest `keep` shells are kept.
- Space = distinct (save, version) blocks referenced by the live saves or any kept shell; it must stay within
  `space_budget` every window. Full-copy shells pay for every block.
- With chance `restore_permille` per window a villager asks for the island as it was 1..`restore_depth` windows ago;
  the restored shell must equal the recorded snapshot exactly.

## Keep counts (shipped data, seed 1, budget 1700 blocks, restores up to 8 back)
| Shells kept | worst space | restores ok | Result |
|---|---|---|---|
| 8 copy-on-write | 1615 | 16/16 | won 40/40 |
| 9 copy-on-write | 1673 | 16/16 | won 40/40 |
| 7 | 1555 | 14/16 | fails: restore |
| 0 (no shells) | 1200 | 0/16 | fails: restore |
| 10 | 1732 | 16/16 | fails: space |
| every shell | 3476 | 16/16 | fails: space |
| 8 full copies | 10800 | 16/16 | fails: space |

## Run
`python tools/streaming/snapshot_shells.py data/islands/disk-saver/snapshot-shells-v1.json [--keep N|-1] [--full-copy]`
