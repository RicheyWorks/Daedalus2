# brew-melody-v1: server-authoritative Youtube Master Island melody brew

POST `/api/v1/brew/melody`, `application/json` request and response
(`MelodyBrewController`, decided with unreal-epic-boss, link #49586 option a). Schema:
`brew-melody-v1.schema.json`; examples checked by `MelodyBrewControllerTest`: `http-cases.json`.

The server wraps `daedalus-core` `world.brew` (G25 `MelodyBrew` + `BrewBench` found tunes on the
`PitchTable.ISLAND_CANON`) and packages `engines/unreal/ytm-island/found_tunes.csv` at build time
(classpath `/brew/found_tunes.csv`); no second tune database.

- Request: `herbs` (3-5 ordered island herb ids), optional `stages` (1-4 per herb, default 3),
  optional `records` (record item ids the player has played; stands in for `playRecord`, so the
  server stays stateless).
- Response: `item`, `cadence`, `contour`, `quality`, `tier`, `effect`, `magnitude`, `durationS`,
  `notes`, `foundTune`, `foundTuneBonus`, `recordId`, `why`. A matched found tune replaces the
  generic tonic item and fills `foundTune` / `foundTuneBonus` / `recordId`.
- 400 for bad input (unknown herb, wrong count, stage out of range, unknown record); 403 when the
  caller is not the configured host.

Auth posture is the same as `/api/v1/kennel/brew`: set `daedalus.brew.host-subject` to the verified
JWT subject of the trusted engine host; blank denies everything. Production JWT chain, no anonymous
bypass, per-caller rate limit `melodyBrew`. It is a pure calculation: it does not spend herbs, grant
items, purify water or remember records. The gameplay host checks inventory, consumes the herbs
once and applies the result once. The kennel `TonicBrewer` route and the jukebox/audio routes are
untouched.
