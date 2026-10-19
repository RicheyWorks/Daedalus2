# Quorum Quays (contest G110, DiskSaver Island)

Quest `q_quorum_quays`, NPC **Harbourmaster Quill**. Code: `tools/streaming/quorum_quays.py`,
tests `tools/streaming/quorum_quays_test.py`, data `data/islands/disk-saver/quorum-quays-v1.json`,
CI job `Quorum Quays`.

## Rules
- Saves are the G86 Compaction Shoals islands x keys_per_island (read-only). Each save is kept on `replicas` quays,
  every copy tagged with a version (the G90 Merkle Mangroves replicas, now as a quorum store).
- Each tick storms close up to `max_down` quays. One operation per tick: a write (`write_permille`) or a read.
- A write counts once W open quays have it. A read asks R open quays and trusts the highest version.
  Too few open quays and the operation is unavailable.
- Win: zero stale reads (a read older than the last counted write) and at least `min_available_permille`
  of operations succeed. R + W > replicas guarantees no stale read; the storms decide how big R and W may be.

## Quorums (shipped data, seed 1, 5 quays, up to 2 closed, need 950 permille)
| R / W | stale reads | available | Result |
|---|---|---|---|
| 3 / 3 (majority) | 0 | 1000 | won |
| 1 / 1 | 1559 | 1000 | fails: stale |
| 2 / 3 | 276 | 1000 | fails: stale |
| 2 / 4 | 0 | 895 | fails: unavailable |
| 1 / 5 (read one, write all) | 0 | 735 | fails: unavailable |
| 5 / 5 | 0 | 334 | fails: unavailable |

## Run
`python tools/streaming/quorum_quays.py data/islands/disk-saver/quorum-quays-v1.json [--r R] [--w W]`
