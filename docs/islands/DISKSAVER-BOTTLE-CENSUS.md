# DiskSaver Island: Bottle Census (contest G179, quest q_bottle_census)

Source-only minigame in `tools/streaming/bottle_census.py`, data in
`data/islands/disk-saver/bottle-census-v1.json`. The islands are the G86
Compaction Shoals islands (`compaction-shoals-v1.json`, read-only); each starts
with weight x `credits_per_weight` save credits.

## Play
Every tick each island with credits may (`send_permille`) throw a bottle of up to
`max_amount` credits down its sea lane to another island. A bottle sails 1 ..
`max_delay` seeded ticks, and lanes are FIFO (a later bottle never overtakes an
earlier one on the same lane). Credits are never made or lost. Harbourmaster
Tilde must count them all at tick `start` while the bottles keep sailing:

| mode | rule | what goes wrong |
|---|---|---|
| local | each island counts at `start` + a seeded skew (0..`max_skew`) | bottles at sea are missed, and a bottle sent after its sender counted but received before its receiver counted is counted twice (inconsistent cut) |
| sync | every island counts at `start` | every credit at sea is missed |
| marker | Chandy-Lamport: `initiator` counts and sends a marker down every lane; an island counts on its first marker and passes markers on, then adds every bottle arriving on a lane before that lane's marker | none on FIFO lanes |

Win: census total = true total and the cut is consistent. Fail reasons
`total_wrong`, `inconsistent_cut`.

## Science (pinned in `bottle_census_test.py`)
- Marker census total = true total with a consistent cut, for every seed and every initiator.
- Recorded lane bottles = brute-force in-transit oracle (sent inside the cut, received outside it).
- Sync shortfall = credits at sea at `start` exactly.
- Local skew breaks the cut on some seeds; with zero skew local = sync.
- Lanes without FIFO can break the marker census; equal delays make them FIFO again.
- Seeded replays are identical.

## Run
`python tools/streaming/bottle_census.py data/islands/disk-saver/bottle-census-v1.json [--mode local|sync|marker]`
prints Harbourmaster Tilde, a JSON quest receipt (G12 style) and exits 0 on a win. CI job: `Bottle Census`.
Editor work (bottle props) is later and belongs to the Unreal owners; nothing here touches the editor.
