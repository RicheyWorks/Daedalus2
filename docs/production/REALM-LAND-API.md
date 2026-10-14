# Realm land district API

`GET /api/v1/realms/{realm}/lands?district=0..99` returns operator-provisioned physical estate
placements from [RealmLayoutStore](REALM-LAYOUT-STORE.md). Authenticate with the existing bearer JWT.
The controller also requires a nonblank principal outside the production filter chain. Requests use
the existing per-subject `oceanChunks` rate limit, shared with terrain and realm-directory reads.
There is no public write endpoint. This is a placement ledger, not ownership or a sale listing.

Enable reads with `daedalus.realm-layout.directory=<operator-controlled-directory>` and provision
versioned `.dlay` files through the core store. Blank configuration or a missing realm file returns
404. No empty layouts, terrain or reservations are silently created. Invalid district or missing
required query parameters return 400; corrupt/unreadable layouts return generic 503 without local
paths. Canonical realm IDs are exact: WORLD-ZERO, GALLERY-CITY, PARCELS, BRICKS, LABYRINTH, OCEAN, PORTAL.
Unknown names return 404. A file's existence does not establish that this process hosts its terrain.

Example response shape (illustrative values, not a production ownership record):

```json
{
  "schemaVersion": 1,
  "realm": "WORLD-ZERO",
  "revision": 2,
  "district": 66,
  "gridSide": 100,
  "pitchMetres": 256.0,
  "coordinates": "east-north-realm-metres",
  "reservedCells": [],
  "lands": [{
    "landNumber": 15,
    "cellX": 60,
    "cellY": 60,
    "size": 2,
    "seed": "-9223372036854775808",
    "originEastMetres": 2560.0,
    "originNorthMetres": 2560.0
  }]
}
```

`landNumber` is immutable estate identity; `cellX/cellY` are current south-west footprint cell.
They can diverge after a move. `size` is cells per side, not metres. Origin metres locate that
south-west cell's centre relative to the realm hub's cell centre. The estate's footprint centre
is origin plus `(size-1)*pitchMetres/2` on each horizontal axis. Add the editor realm origin and
convert metres to centimetres on the Unreal boundary. Java terrain axes use east=X/north=Z with
Y vertical; the DTO deliberately uses named horizontal axes. Vertical placement is not supplied.

Seeds are signed decimal strings so a JSON double parser cannot discard 64-bit precision. Parse
them as signed int64. Layout revision is an optimistic-write version, not a blockchain height.
Reserved numbers are current grid cell numbers for this district, not estate identities. An
estate cannot cross districts. Responses contain at most 100 estates and 100 reserved cells;
larger estates reduce the count through footprint occupancy. Absence of a row says only that no
estate is placed there; do not infer mintability, vacancy for sale or an ownership entitlement.

Reads reload the atomically replaced snapshot, so host updates become visible on the next request.
Use revision to replace a cached district consistently; do not combine districts from different
revisions into an authoritative allocation view. The API does not yet provide streaming push,
editor import, a wallet ownership check, mint bundles or a distributed authority service.

## Validation, 2026-10-13

Full server reactor verify passes in 170 seconds: 731 core, 26 plugin API, 8 wallet, 33 plugin
runtime and 805 server tests; coverage and SpotBugs checks pass. Six new API tests cover
district partitioning, exact int64 seed strings, disabled/missing/corrupt stores, identity checks,
and actual loopback production-JWT HTTP across a full server restart. HTTP assertions include
an estate move with unchanged identity, per-subject quota isolation, 401/400/404/429/503 responses
and corrupt-file error redaction. This is local API evidence; shared Unreal consumption and
production deployment are not established. `realm-land-api-proof.json` records source/log hashes.

The workbook adds LAND-GRID, LAND-STORE and LAND-API scoped rows and SYS02–SYS04 mechanics,
preserving the earlier asset/production records. Its 31 verified rows and five pending checks
are verification scopes, not 31 shipped realms or a complete project acceptance count.

## Integration lesson

A JSON number cannot safely carry every procedural int64 seed through Unreal's double-backed
JSON accessors. Keep seeds as decimal strings at this boundary and test both int64 extremes.
Also preserve estate identity through realm transfers and moves; never derive it from current cells.
New `@Value` settings must also appear in application.yml: the configuration coverage gate checks
operator discoverability, independently of endpoint behavior and the README's authentication table.
