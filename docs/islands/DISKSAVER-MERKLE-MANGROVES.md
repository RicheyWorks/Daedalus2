# Merkle Mangroves (contest G90, DiskSaver Island)

Quest `q_merkle_mangroves`, NPC **Warden Hashroot**. Code: `tools/streaming/merkle_mangroves.py`,
tests `tools/streaming/merkle_mangroves_test.py`, data `data/islands/disk-saver/merkle-mangroves-v1.json`,
CI job `Merkle Mangroves`.

## Rules
- Saves (G86 Compaction Shoals islands x keys_per_island, read-only) live on a shore replica and a mangrove replica.
- Each window, storms flip up to `max_drift` mangrove saves. At dawn the warden runs anti-entropy.
- Both sides build a binary Merkle tree of `depth` levels; keys go to leaf buckets by CRC32.
- Merkle descent: compare a node's hash (cost 1); skip it if equal, otherwise descend; a differing leaf copies all its keys (cost 1 each).
- A window's sync must cost at most `bandwidth`. Win: every window in budget, replicas equal afterwards (checked every window).

## Syncs (shipped data, seed 1)
| Sync | worst window (budget 200) | total | Result |
|---|---|---|---|
| Merkle descent | 115 | 1713 | won 30/30 |
| flat leaf-hash scan | 298 | 8221 | fails: bandwidth |
| full copy | 1200 | 36000 | fails: bandwidth |

## Run
`python tools/streaming/merkle_mangroves.py data/islands/disk-saver/merkle-mangroves-v1.json [--sync merkle|leaf_scan|full_copy]`
