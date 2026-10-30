# DiskSaver Island: Harbour Cryptogram (G552)

Telegraphist Philippa sends the evening harbour news in a letter-substitution cipher.

`tools/streaming/harbour_cryptogram.py` reads a world census (the `tools/world_census` output,
read-only) and builds true sentences from it: each world's title and island count, its cargo
names, how many of its islands are empty, and the harbour totals. Numbers are spelled out. A
seed picks up to three sentences (joined by `STOP`) and a cipher key that is a derangement of
A-Z, so no letter stands for itself. Python dev tooling only; nothing runs inside Unreal.

The puzzle shows the ciphertext, a few given letters (about one in five of the letters used,
at least two), a frequency table, and a board with the given letters filled in.

```
python tools/streaming/harbour_cryptogram.py census.json --seed 7               # the telegram
python tools/streaming/harbour_cryptogram.py census.json --seed 7 --guess "SYNTHETIC ALPHA ..."
python tools/streaming/harbour_cryptogram.py census.json --seed 7 --mapping key.json
python tools/streaming/harbour_cryptogram.py census.json --seed 7 --solution
```

`key.json` maps cipher letters to plain letters (`{"Q": "S"}`); the given letters are added
for you and unmapped letters read as `?`. Grading counts every letter position:

| verdict | meaning |
|---|---|
| `decoded` | the whole message is right |
| `partial` | at least half of the letter positions are right |
| `garbled` | fewer than half |

CI (`.github/workflows/harbour-cryptogram.yml`) runs the tests, including the real census
fixtures, and prints the seed-7 telegram. Hook: `data/islands/disk-saver/harbour-cryptogram-v1.json`.
