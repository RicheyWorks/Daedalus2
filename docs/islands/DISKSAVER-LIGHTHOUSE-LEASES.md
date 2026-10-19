# DiskSaver Island: Lighthouse Leases (contest G171, quest q_lighthouse_leases)

Source-only minigame in `tools/streaming/lighthouse_leases.py`, data in
`data/islands/disk-saver/lighthouse-leases-v1.json`. The keepers are the G86
Compaction Shoals islands (`compaction-shoals-v1.json`, read-only).

## Play
Only one lighthouse keeper (leader) may write the island save log at a time.
The harbour store grants each epoch a lease of `lease` ticks and then hands the
light to another keeper. Every keeper's clock drifts by a seeded per-mille rate
(up to `max_drift_permille`), and with `pause_permille` odds a keeper freezes
for up to `max_pause` ticks between checking its lease and its write landing.
Keeper Ines picks the rule:

| mode | rule | what goes wrong |
|---|---|---|
| none | no lease; the old keeper stops only when news arrives (`news_delay`) | split brain after every hand-over |
| naive | lease checked on the keeper's own clock | a slow clock writes after the lease ended |
| guard | lease shortened by `guard` ticks | safe against drift, but a pause still lands a stale write |
| fenced | guard + fencing token (epoch number) | none: the store rejects tokens below the highest it accepted |

Win: the store never accepts a stale write. Fail reason `stale_write_accepted`.

## Science (pinned in `lighthouse_leases_test.py`)
- `drift_bound(L, d) = L - floor(L*(1000-d)/1000)` is the smallest safe guard (equals brute force).
- With no pauses and `guard >= drift_bound`, zero writes land outside the lease.
- Fencing rejects exactly the stale writes the guard alone accepts; accepted tokens never go down.
- Stale count equals a brute-force oracle over the store log; seeded replays are identical.

## Run
`python tools/streaming/lighthouse_leases.py data/islands/disk-saver/lighthouse-leases-v1.json [--mode none|naive|guard|fenced]`
prints Keeper Ines, a JSON quest receipt (G12 style) and exits 0 on a win. CI job: `Lighthouse Leases`.
Editor work (lighthouse props) is later and belongs to the Unreal owners; nothing here touches the editor.
