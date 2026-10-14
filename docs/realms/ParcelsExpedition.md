# Parcels: The Signal District

This browser visitor expedition lives at `/parcels-realm.html`. It extends the district in ADR-033 with an original local story: surveyor Neri Vale asks a traveler to trace Heartstone echoes, observe surviving life and water, reach the northern beacon, and return to the public helipad. The meteor, shattered planet, arks, Heartstones and unreachable sky gates follow `REALMS.md` and the current story draft. Neri and the field survey are new visitor fiction.

## What is implemented

- Responsive canvas district explorer, schematic low-poly plot scenes, helicopter illustration, compass, coordinates, six sequential checkpoints, and a gold waypoint.
- Keyboard walking with WASD or arrows, Shift to run, E to survey; touch direction buttons; canvas click/tap and accessible plot directory inspection; zoom and overview/follow camera.
- Exact district footprint: 148 × 148, origin X −26 / Z −148, sixteen 2 × 2 city blocks, sixty 16 × 16 plots, four-unit roads with sidewalks, plaza X 30…65 / Z −92…−57, and a ten-unit helipad centered at X 48 / Z −74. IDs 27, 28, 35, 36 are public plaza cells. Plot heights stop at Y 32.
- Seeded local opening kinds use a source port of the initial Java SplittableRandom bounded draw, intended to match `DistrictOps.pick`. Parity is unverified; no runtime check was run. Browser objects illustrate opening kinds rather than reproduce exact live cube geometry.
- Local visited plots, pinned plot notes, and checkpoint progress. Versioned storage keys include the exact signed 64-bit seed and world ID. Restore validates size, version, seed, district identity, progression range, player bounds and plot ID arrays. Unavailable browser storage leaves a usable page-session expedition.
- Read-only server connection: `GET /api/v1/worlds` selects only mounted PARCELS worlds, followed by `GET /api/v1/world/{id}/plots`; optional gates and arks reads populate travel information. Long seeds are preserved as strings before JSON decoding. Ownership, builders and footprint rows are validated before replacing a local draft.
- `?seed=<signed-long>&world=<mounted-id>` opens the requested existing district when readable, otherwise the explicitly labeled local draft. API failure preserves the current expedition. Failed refresh labels previous ownership snapshots as offline.

## Land release boundary

Server plot claims already exist through `/api/v1/world/{id}/islands/{n}/claim`, `/abandon` and `/builders`. Plot building is owner/builder restricted and excludes public streets, plaza and heights over 32. This visitor page sends no claim, builder, voyage, cube-write, mint or world-creation requests. Its local journal grants no reservation, ownership, items, economy credits or NFTs.

The current `WalletController` deed voucher route looks up actual island entries. The existing `realm.js` also excludes district plots from its mint UI. Plot NFT minting is not implemented by this expedition. No mint price, release date, scarcity beyond sixty plots per district, or claimed deployment is invented. Ownership actions and server travel link to `/realm.html?world=<id>`.

## Crew finish outline

1. Keep the visitor page tied to the accepted sixty-plot geometry; add original district storefront, civic, grove and helicopter assets through the existing art queue with Parcels-specific prefixes.
2. Integrate actual built plot scenes through the world's block/package data and renderer. The visitor canvas currently draws opening scene illustrations, so custom construction needs a live renderer bridge.
3. Use the server realm for authenticated claims and builders. Promote the read-only snapshot to live ownership events when the shared transport is ready, and surface refusal reasons from the existing server.
4. Pair and operate sky gates through the current gate/voyage pipeline, including server travel state and arrival. The visitor survey never hails or moves a helicopter automatically.
5. Define the plot deed contract, world registry, plot seed/footprint metadata, wallet ownership authority and release terms before exposing NFT mint. Existing island vouchers are not a substitute for plot deeds.
6. Move approved survey achievements to a server-owned quest service if the team wants persistent shared progression. Keep current local notes distinct from ownership and the economy.

## Delivery record

This source implementation adds only `parcels-realm.html`, `parcels-realm.css`, `parcels-realm.js` and this document. Per the requested coding pass, no tests, builds, browser executions or deployment were performed. Playability and API behavior remain unverified at runtime.
