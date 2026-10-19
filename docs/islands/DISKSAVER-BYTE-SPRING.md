# DiskSaver Island — Byte Spring (contest G39)

Offline minigame: a leaking spring budgets RAM/disk "water" for resident island
caches against the DSB streaming budget cap.

## Rules
- One water unit = 1 KiB of (ram + disk) from a DSB-style island cost.
- Each tick residents drink their total cost from the cistern.
- Wet tick: spring fills `spring_fill`, then residents drink.
- Dry tick: leak + drink; `dry_streak` increments.
- If resident cost exceeds `budget_cap`, dump lowest `priority` (then highest cost, then id).
- Fail: cistern empty for `drought_limit` consecutive dry ticks.
- Win: survive `win_ticks` with cistern level > 0.

## Files
- `tools/streaming/byte_spring.py` — sim
- `tools/streaming/byte_spring_test.py` — tests
- `data/islands/disk-saver/byte-spring-v1.json` — fixture

## Quest
`q_byte_spring` — keep the cistern alive through dry season without dumping the home island.
