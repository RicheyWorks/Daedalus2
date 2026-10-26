# Lighthouse Backoff (contest G134, DiskSaver Island)

Quest `q_lighthouse_backoff`, NPC **Keeper Wren**. Code: `tools/streaming/lighthouse_backoff.py`,
tests `tools/streaming/lighthouse_backoff_test.py`, data `data/islands/disk-saver/lighthouse-backoff-v1.json`,
CI job `Lighthouse Backoff`.

## Rules
- One boat per save write: the first `writes_per_island` keys of each G86 Compaction Shoals island (read-only).
  All boats arrive at tick 0, while the lighthouse is dark for `outage` ticks.
- Once lit, the keeper berths `capacity` boats a tick; the rest of that tick's wave is turned away.
- A turned-away boat waits by the retry policy (attempt a, base b, cap c): `fixed` b; `expo` min(c, b*2^a);
  `full_jitter` 1 + rand(min(c, b*2^a)).
- Win: every write berths by tick `deadline` and total retries stay within `max_retries`. Every boat is
  accounted for (berthed or still at sea).

## Policies (shipped data: 300 writes, outage 30, 20 berths a tick, cap 64, deadline 150, retry budget 2400)
| Policy | retries | last berth | Result |
|---|---|---|---|
| full_jitter | 1935 | 92 | won (seeds 1-5 all win) |
| fixed (b=1) | 11100 | 44 | fails: retry storm |
| expo, no jitter | 2500 | 191 (80 of 300 by tick 215) | fails: deadline (thundering herd, waves of 300) |

## Run
`python tools/streaming/lighthouse_backoff.py data/islands/disk-saver/lighthouse-backoff-v1.json [--policy fixed|expo|full_jitter]`
