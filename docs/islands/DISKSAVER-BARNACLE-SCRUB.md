# Barnacle Scrub (contest G151, DiskSaver Island)

Quest `q_barnacle_scrub`, NPC **Diver Pell**. Code: `tools/streaming/barnacle_scrub.py`,
tests `tools/streaming/barnacle_scrub_test.py`, data `data/islands/disk-saver/barnacle-scrub-v1.json`,
CI job `Barnacle Scrub`.

## Rules
- Every G86 Compaction Shoals save (6 islands x 200 keys = N = 1200, read-only) is kept as two 64-byte copies,
  A and B. The save's **CRC32** (zlib, IEEE 802.3 polynomial) is on the diver's slate.
- `barnacles_per_kilotick` barnacles land per 1000 ticks; each flips one random bit of one random copy.
- The diver visits `rate` saves a tick, round robin, reading both copies (2 reads per visit, counted against
  `max_reads`). With checksums a copy whose CRC32 fails is rewritten from the copy that passes. Without checksums
  the diver only sees that the copies differ and copies A over B. A save whose two copies both fail is lost.
- Win: at season end at most `max_lost` saves are lost and reads stay within `max_reads`.
- Not G90 Merkle Mangroves: that game finds drift between two whole replicas; this one is silent corruption,
  checksums and the scrub interval.

## The checksum
CRC32 detects **every single-bit flip** (a test flips all 512 bits of a copy) and any burst up to 32 bits; random
multi-bit damage goes undetected with probability about 2^-32 per corrupted copy (a test runs 3000 seeded
multi-bit corruptions, all caught). One barnacle is one bit flip, so the slate never misses a barnacle. SHA-256
would also work at higher cost; CRC32 is enough for detecting accidental rot, not for tampering.

## Science
- Rot rate per copy per tick: r = (barnacles_per_kilotick / 1000) / 2N. Scrub window: T = N / rate ticks.
- A save is lost when both copies are hit inside one window: (1 - e^(-rT))^2, about (rT)^2.
  Expected losses: N x (ticks / T) x (1 - e^(-rT))^2. Reads per tick: 2N / T.
- Tests pin the model against a seeded Monte Carlo (seeds 1-5, within 12%) and reads per tick exactly.
- Without checksums a mismatch is resolved by copying A over B, which is the wrong copy about half the time
  (shipped data: 1040 wrong picks vs 1119 right ones); that blind repair is the visible failure mode.
- `solve` picks the largest window T (smallest rate) whose predicted loss meets `max_lost` within `max_reads`;
  `brute_force` simulates every rate on seeds 1-5. Both give rate 10 (T = 120 ticks), the shipped dive plan.

## Choices (shipped data: 8000 ticks, 720 barnacles per 1000 ticks, budgets 105 lost and 200000 reads)
| Rate (T) | Checksums | lost (model) | reads | Result |
|---|---|---|---|---|
| 10 (120) | CRC32 | 94 (100.0) | 160000 | won (seeds 1-5 all win) |
| 6 (200) | CRC32 | 145 (162.8) | 96000 | fails: lost |
| 16 (75) | CRC32 | 65 (63.4) | 256000 | fails: reads |
| 10 (120) | none | 1081 (1040 wrong-copy repairs) | 160000 | fails: lost |

## Run
`python tools/streaming/barnacle_scrub.py data/islands/disk-saver/barnacle-scrub-v1.json [--rate N] [--no-checksum]`
