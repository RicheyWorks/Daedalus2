# Barnacle Scrub (contest G151, DiskSaver Island)

Quest `q_barnacle_scrub`, NPC **Diver Pell**. Code: `tools/streaming/barnacle_scrub.py`,
tests `tools/streaming/barnacle_scrub_test.py`, data `data/islands/disk-saver/barnacle-scrub-v1.json`,
CI job `Barnacle Scrub`.

## Rules
- Every G86 Compaction Shoals save (6 islands x 200 keys, read-only) is kept as two copies, A and B.
- `barnacles_per_kilotick` barnacles land per 1000 ticks, each on a random copy; a good copy that is hit rots
  silently.
- The diver visits `rate` saves a tick, round robin, reading both copies (2 reads per visit, counted against
  `max_reads`). With checksums a rotted copy is rewritten from the good one. Without checksums the diver only sees
  that the copies differ and copies A over B, which destroys the save when A was the rotted one. A save with both
  copies rotted is lost.
- Win: at season end at most `max_lost` saves are lost and reads stay within `max_reads`.
- Not G90 Merkle Mangroves: that game finds drift between two whole replicas; this one is silent corruption,
  checksums and the scrub interval.

## Choices (shipped data: 8000 ticks, 720 barnacles per 1000 ticks, budgets 105 lost and 200000 reads)
| Rate | Checksums | lost | reads | Result |
|---|---|---|---|---|
| 12 | yes | 83 | 192000 | won (seeds 1-5 all win) |
| 6 | yes | 153 | 96000 | fails: lost |
| 16 | yes | 72 | 256000 | fails: reads |
| 12 | no | 1101 (1065 spread by blind repairs) | 192000 | fails: lost |

## Run
`python tools/streaming/barnacle_scrub.py data/islands/disk-saver/barnacle-scrub-v1.json [--rate N] [--no-checksum]`
