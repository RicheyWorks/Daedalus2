# Realm layout ledger

`RealmLayout` and `RealmLayoutStore` provide bounded persistent placement for the seven canonical realms.
This is physical layout data. It contains no owner, wallet, contract, token or mint authorization.
The server must authenticate and authorize writers before exposing any mutation endpoint.

Each realm has a revision, an explicit reserved-cell mask, and at most 10,000 estates. The host chooses
the reservation mask; the library does not guess the hub's footprint. Estates have an immutable
`landNumber`, current cell x/y, size 1–4 and seed. `place()` initially assigns the lowest covered
spiral number. `move()` retains number, seed and size while checking the new footprint. A number can
therefore differ from the lowest cell at the estate's current position. A moved identity cannot be
reallocated by placing another estate with the same identity.

Every snapshot rejects overlapping footprints, hub/reserved-cell collisions, duplicate identities,
off-grid estates and district splits. Realms have independent identity spaces. `district(0..99)`
returns only placed estates in that district, with at most 100 single-cell estates. Missing cells
are not implicitly sold, minted, reserved or generated. Layouts and their collections are immutable.

## Persistence contract

One `<CANONICAL-REALM>.dlay` file per realm, version 1 (`DLAY` magic), at most 1 MB on read.
Counts are bounded before allocation. The format stores realm, revision, sorted reserved numbers,
then estates sorted by immutable identity. It rejects unknown versions, realm mismatch, bad counts,
duplicate reservations, invalid footprints, truncation and trailing bytes. Structurally valid bit
changes are not detected by a checksum; an external backup/hash ledger remains future hosting work.

Create an empty revision-zero layout and save with expected revision -1. Each placement/move returns
the next revision. Save with the prior revision; stale writers fail without replacing the snapshot.
A per-realm OS lock serializes cooperating processes. Same-JVM overlapping locks fail as an IOException
so hosts can retry after reloading rather than overwrite another writer. Readers see the previous or
next complete snapshot through atomic replacement. Temporary bytes are flushed and forced before
replacement; an unsupported atomic move fails rather than falling back to truncating the target.
This is not a distributed database, shared-filesystem guarantee or tested power-loss recovery claim.

The directory is operator-controlled. Canonical realm validation prevents path input from becoming
a filename traversal. Do not let untrusted clients choose the storage directory or replace its files.
No process is writing the production layout store yet; editor import and authenticated district API
integration are separate pending work, with the proposed DTO sent to Claude in hub29168.

Example host sequence:

```java
var store = new RealmLayoutStore(operatorLayoutDirectory);
var layout = RealmLayout.empty("WORLD-ZERO", reservedHubCells);
store.save(layout, -1);
var placed = layout.place(52, 52, 2, 42L);
store.save(placed, layout.revision());
var moved = placed.move(placed.estates().getFirst().landNumber(), 60, 60);
store.save(moved, placed.revision());
```

The host must reload on revision conflict. Do not retry an old expected revision indefinitely or
silently replace a damaged snapshot with an empty one. Restore and verify a backup instead.

## Validation, 2026-10-13

Full core verify passes in 50.348 seconds: 731 tests, zero failures/errors/skips, coverage ratchet
met and SpotBugs zero. Eight new tests cover restart recovery, deterministic bytes, 10,000-estate
snapshots under 300 KB, stale revisions, duplicate creation, lock contention, corrupt/truncated/
oversized snapshots, realm isolation, reservation collisions, overlap and identity-preserving moves.
These tests prove local storage and placement rules; they do not prove a deployed API or Unreal import.

## Integration lesson

After a tug, current spiral position and immutable identity are different fields. Never regenerate
an existing estate's identity from its new coordinates. Likewise, a structurally valid placement
record establishes no wallet ownership: keep that check in the authenticated authority layer.
Do not silently create an empty ledger when loading a corrupt file; corruption must stop the write.
