# Toll Bridge Tokens (contest G158, DiskSaver Island)

Quest `q_toll_bridge_tokens`, NPC **Tollkeeper Bram**. Code: `tools/streaming/toll_bridge_tokens.py`,
tests `tools/streaming/toll_bridge_tokens_test.py`, data `data/islands/disk-saver/toll-bridge-tokens-v1.json`,
CI job `Toll Bridge Tokens`.

## Rules
- Arrivals per tick are the G126 Breakwater Queue harbour waves: the landed `breakwater_queue.arrivals` run on its
  shipped `breakwater-queue-v1.json`, read-only (a test checks the file bytes are unchanged). 19669 writes over
  4000 ticks, with swells and a storm season.
- The bridge sways if more than `buffer` (180) writes cross in any `window` (20) consecutive ticks.
- Gates: `open`; `fixed_window` (at most `limit` = 120 per aligned block of 20 ticks); `token_bucket` (integer
  milli-tokens, 120/20 = 6 tokens a tick drip into a jar of `burst` tokens; one token per write).
- Win: the bridge never sways and at least `min_admitted_permille` (900) of writes cross.

## Science (pinned by tests)
- Token bucket envelope: any span of t ticks admits at most burst + (t-1) x rate (rate = limit / window), checked
  on the harbour waves for spans 1-80, and **tight** under saturation (spans 1, 7, 20, 60 hit it exactly; long-run
  rate is exactly 6 a tick). Tight whenever the jar holds at least one tick's drip.
- Fixed window boundary: 500 writes on the last tick of one block and 500 on the first tick of the next let exactly
  2 x limit = 240 through inside one 20-tick window, above the 180 buffer. On the seeded harbour waves the worst
  fixed-window span (197) straddles a block edge while every aligned block stays within 120.
- Solver: largest safe jar = buffer - (window-1) x rate = 180 - 114 = 66, equal to brute force under saturation
  and to the largest jar that never sways on the harbour waves.

## Gates (shipped data)
| Gate | admitted permille | worst 20-tick span | Result |
|---|---|---|---|
| token_bucket, jar 66 | 927 | 180 | won (jars 49-66 win) |
| open | 1000 | 304 | fails: sways |
| fixed_window | 905 | 197 | fails: sways at a block edge |
| token_bucket, jar 30 | 819 | 144 | fails: too many turned back |
| token_bucket, jar 96 | 951 | 210 | fails: sways |

## Run
`python tools/streaming/toll_bridge_tokens.py data/islands/disk-saver/toll-bridge-tokens-v1.json [--gate G] [--burst N]`
