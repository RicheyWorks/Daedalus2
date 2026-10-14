# Base-layer integration evidence — Codex handoff, 2026-10-13

This supplements Claude's `BASE-LAYER.md`; it does not replace that owner's placement ledger.
The accompanying [source census](base-layer-codex-evidence.json) records source hashes and manifest counts.
Regenerate it with `python tools/realms/base_layer_audit.py --output <file> [--layout <saved-layout.json>]`.
Counts describe the inspected files, not a complete project census, installed gameplay, or minted ownership.

## 1. Server endpoints and realm coverage

| Realm | Existing source support | Missing or unproven foundation |
|---|---|---|
| WORLD-ZERO | SKY_ISLANDS WorldHub mount, world manifest/chunks, legacy island claim/voucher/metadata | Persisted 10,000-cell allocation registry, estate ownership and realm-aware mint |
| GALLERY-CITY | GALLERY mount, world manifest/chunks, gallery-city DIC and DCS | Grid/estate registry and authenticated live realm handover |
| PARCELS | PARCELS mount, world manifest/chunks, parcels DIC and DCS | Grid/estate registry and live handover |
| BRICKS | BRICKS mount, world manifest/chunks, bricks DIC and DCS | Grid/estate registry and live handover |
| LABYRINTH | Separate maze generation/solve API, labyrinth DIC and DCS | WorldStyle.LABYRINTH is not ready; Maze API does not itself mount streamed terrain |
| OCEAN | Optional separate bounded OceanHost and chunk store, authenticated read-only manifest/chunks | Full district coverage, authoritative travel network, Ocean DIC/DCS, live handover |
| PORTAL | Retro realm generation/check and classic DRR items | No chunk-host directory entry; empty native session catalog is intentional |

World mounts are runtime configuration, not evidence of public hosting. Source routes include
`GET /api/v1/worlds`, `POST /api/v1/worlds`, `GET /api/v1/world/{id}`,
`GET /api/v1/world/{id}/chunk/blocks?x=&y=&z=`, legacy `/islands` and `/islands/{slot}/claim`,
`POST /api/v1/world/{id}/islands/{slot}/deed-voucher`,
`GET /api/v1/world/{id}/tokens/{tokenId}`, wallet nonce/login/config, inventory catalogs,
`GET /api/v1/retro/{seed}`, and the separate maze API.

PR80 (`753fba9d4933e63291ec74e54773b9e19abc269c`, consumer approved in hub29139)
adds authenticated `GET /api/v1/realms`, with optional canonical realm/catalog fields.
It advertises existing mounted providers; it does not create new terrain or deploy a server.
Treat it as a candidate until its merge state is checked. Ocean must not be duplicated as a WorldService.

Sources: `WorldsController.java`, `WorldController.java`, `WalletController.java`,
`RetroRealmController.java`, `OceanHostController.java`, `InventoryCatalogController.java` under
`daedalus-server/src/main/java/com/daedalus/server/controller/`; `WorldStyle.java` in daedalus-core.
No generic persisted `/lands` or estate/tug/swap API was found in this source audit.

## 2. Land supply and mint contract

[ADR-065](../adr/ADR-065-ten-thousand-lands-per-realm.md) is proposed: each realm has a
100×100 clipped spiral, land numbers 0–9999, pitch 256 m, and 10×10 districts. An estate
occupies multiple cells and uses the lowest covered number as its identity. A movable estate's
current cell is not its immutable identity. Hub reservations and estate coverage mean 10,000
cells must not be advertised as 10,000 independent mintable deeds without a supply allocation.

The actual legacy [contract](../../chain/contracts/RealmIslands.sol) signs
`Deed(address to,uint256 slot,uint64 seed,uint8 radius,uint256 deadline)`;
ERC721 token ID is `slot`. Java IslandOps has 64 slots. The voucher/controller uses one configured
contract and does not sign realm, estate size, contents, egg entitlement, or fair randomness.
Reusing a bare slot across realms needs a new identity scope. A uint8 radius also needs revision
for larger estates. Existing seed/radius metadata is not the proposed bundle metadata.

Locations: `chain/scripts/deploy.ts`, `chain/scripts/lib/{confirm,fees,record}.ts`,
`chain/test/fixtures/java-deed-voucher.json`, `daedalus-wallet/.../DeedVoucher.java` and
`WalletController.java`. Neither inspected checkout contained `chain/deployments`; external
deployment remains unverified. This audit reads no keys and performs no chain transaction.

**Candidate V2 fields for blockchain-owner review, not an implemented mint contract:**
domain version, chainId, verifyingContract; recipient; canonical realmId; landNumber;
estate size; seed and generatorVersion; gridSpecHash; contentsHash; metadataHash/version;
nonce and deadline. Derive token identity from realm plus land number rather than bare slot.
Keep current placement in an authorized allocation/movement ledger. Commit explicit bundled
avatar/creature/egg/item token references in contentsHash. A hash does not prove fair randomness;
VRF or commit/reveal fulfillment remains separate work. Plot tags must say proposed/unminted
until ownership is verified. [Egg-land parity](DRR-EGG-LAND-PARITY.md) is gameplay annotation,
not an on-chain mint or ownership authorization.

Saved layout audit: artifact SHA256 `cbe244ca25e513cb81ae13133747613dc49e160d67446c20d5f1d10d6ceab8e0`
contains 14 levels / 13 estate groups covering 71 cells, plus the owner's 9-cell hub reservation;
no footprint overlap or district split. Undo values are two-dimensional move deltas, not actor
lists. Claude's 7,552-root-actor result is owner-reported runtime evidence, not independently
counted by this file. His hub29130 report adds 89 plot markers in six rings (169−9−71).
These labels do not establish minted ownership or a sellable supply.

## 3. Ocean host and docks

Ocean owns a bounded persistent sector, seeded seafloor/water/pier and manifest berth anchors.
Default address window is 64 chunks with resident capacity 128; this is not a complete 10,000-land sea.
Native vessel possession, hull and dock-policy tests exist, but manifest berth anchors are not an
authoritative production dock/sub-dock catalog. DockRegistry currently uses display realm strings
while RealmSession uses canonical IDs: an explicit adapter and actual travel proof are required.
Boats/submarines enter Ocean at docks; shore return uses the departure realm; underwater docks
can reach other realms. See `OCEAN-DOCK-TRAVEL-CONTRACT.md` and `OCEAN-HOST-API.md`.
The three original GLBs total 16,794 triangles; the 25-file native archive includes materials,
not 25 independent models. Public hosting, TLS, reconnect/rollback and live transfer remain unproven.

## 4. Blender and content counts

| Manifest | Cast/humanoids | Creatures/monsters | Other records | Total |
|---|---:|---:|---:|---:|
| Gallery | 13 | 19 | 24 environment | 56 |
| Parcels | 13 | 19 | 24 environment | 56 |
| Bricks | 13 | 19 | 24 environment | 56 |
| Labyrinth | 13 | 22 | 12 environment + 8 dungeon-master + 12 Halloween | 67 |
| Portal | 16 | 48 | 27 environment | 91 |
| Ocean | — | — | skiff, submarine, dock | 3 |

Sources are `data/art/<realm>/production-manifest.json` and `data/art/ocean/manifest.json`.
329 records across these manifests; `Validated` is their recorded export status, not a new runtime test.
World Zero additionally has tracked island corpora outside these manifests: Kennel 500 GLBs
(400 Props/100 Items), DiskSaver 500 GLBs, Prometheus 500 FBXs. These are format/file counts,
not an additive census of unique metaverse models or proof of 500 unicorn characters.

Portal population plan has 1,000 individuals: 500 enemies and 500 friendlies, 50 types per side
×10 each. It records 10 export-validated / 990 planned and all 1,000 Unreal-pending. Its reference
to a separate 500-unicorn collection does not independently verify that collection.
Four DCS files have 12 roles each; five DIC files contain 63 item records. Ocean lacks both;
PORTAL uses classic DRR items. Gallery's 13 imported casts and 26 Attack/Hurt bindings were
checked separately; that evidence does not verify every creature's gameplay.

## 5. Workbook and acceptance corrections

`Realm-production-2026-10-13.xlsx` tracks 343 asset references (329 above +14 reused Kennel refs),
379,408 triangles and a 134 Props/Items baseline. It is not the full metaverse inventory or NFT registry.
The canonical update records 28 scoped runtime verifications and five pending gates, not a count
of every possible Unreal action or proof of shippability. Broad `Unreal=Pending` manifest rows can
lag individual import/clip proofs: keep separate import, binding, placement and Play evidence,
with source SHA and job/log references, rather than flipping an entire realm green.

Claude's later hub29138 report places four realm hubs, 160 plot slabs per realm and environment
kits (96 imports); these are owner-reported editor results. Ground slabs and named gate/dock
markers do not prove streamed terrain, navigable docks, interactive creatures, minted ownership,
public hosting or authenticated realm travel. Preserve these structures and add the missing systems.
