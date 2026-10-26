# DiskSaver Island: Tidemark Chunks (contest G175, quest q_tidemark_chunks)

Source-only minigame in `tools/streaming/tidemark_chunks.py`, data in
`data/islands/disk-saver/tidemark-chunks-v1.json`. The saves belong to the G86
Compaction Shoals islands (`compaction-shoals-v1.json`, read-only; save size =
weight x `bytes_per_weight`). The vault quota is the G39 Byte Spring streaming
budget cap (`byte-spring-v1.json`, read-only) x `byte_unit` bytes.

## Play
Each season every island saves a new version with up to `edits` seeded edits
(insert, delete or overwrite a run of up to `max_run` bytes). The vault keeps
one copy of every chunk (sha256), and each stored chunk plus each chunk
reference in a save's recipe costs `ref_bytes` of index. Tallyman Oro picks the
chunker:

| mode | rule | what goes wrong |
|---|---|---|
| whole | one chunk per save | any edit stores the whole save again |
| fixed | `fixed_size` chunks | one inserted byte shifts every later cut; nothing after it dedupes |
| cdc | cut after a byte when the rolling hash of the last 16 bytes has its low 7 bits zero (`min_chunk`..`max_chunk`) | none: cuts follow the content and resync right after an edit |

Win: the vault cost of all versions fits the quota. Fail reason `over_quota`.
Shipped seed 175: whole 122291, fixed 86978, cdc 39197 against a 48000 quota.

## Locked chunker
`BASE = 257`, `PRIME = 2**31 - 1`, `WINDOW = 16`, `MASK_BITS = 7` are module
constants; a config with another window or mask is rejected, and a golden
fixture test pins one window hash, the cut sizes of a seeded 4 KiB blob and the
shipped vault cost, so CI fails if the chunker drifts.

## Science (pinned in `tidemark_chunks_test.py`)
- The rolling hash equals the from-scratch window hash at every byte.
- Chunks rebuild the save exactly; CDC chunks respect `min_chunk`/`max_chunk`.
- One byte inserted at the front: fixed shares at most 1 old chunk, CDC shares >= 90% (at most 2 new chunks).
- An insert mid-save keeps exactly the fixed chunks before it.
- Mean CDC chunk = `min_chunk - 1 + 2**mask_bits` within 10% (seeded Monte Carlo).
- Vault cost equals a brute-force oracle that compares chunk bytes directly; seeded replays are identical.

## Run
`python tools/streaming/tidemark_chunks.py data/islands/disk-saver/tidemark-chunks-v1.json [--mode whole|fixed|cdc]`
prints Tallyman Oro, a JSON quest receipt (G12 style) and exits 0 on a win. CI job: `Tidemark Chunks`.
Editor work (tidemark props) is later and belongs to the Unreal owners; nothing here touches the editor.
