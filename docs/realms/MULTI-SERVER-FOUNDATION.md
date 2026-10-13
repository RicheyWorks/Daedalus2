# Larger lands and multiple servers — implementation boundary

2026-10-13. Astra owns geometry, routing and sizing; Claude owns `deploy/`, Docker, TLS, backups and restore tooling. Team acknowledgement: hub 28640. No island levels have moved; no cloud resources or paid transactions were created.

## Land size is not NFT size

Existing `RealmIslands` vouchers bind seed and `uint8 radius`; those values remain unchanged. A runtime layout now carries pitch/clearance separately in Java and C++. Legacy default offsets remain 128 m for compatibility. The explicit expansion layout uses 512 m pitch and 16 m clearance, with a maximum single-cell horizontal width of 496 m. It accepts a proposed 256 m width/128 m vertical depth and rejects shrinking via its `canGrow` predicate or crossing the reserved horizontal footprint. Depth is positive but requires separate generator/altitude limits; this geometry predicate is not a memory admission policy.

This does **not** raise the old `LandGenerator` radius cap of 46 or the existing claim boundary. Those APIs still generate the old land. Larger procedural generation needs a versioned, chunk-oriented path that preserves existing edits and original seed semantics. Increasing MAX_REACH alone would increase the current temporary TreeMaps and can overwrite old ownership assumptions. Do not market or mint a new playable size until generation, claims, saves, client meshes and restore all pass at that size.

Grid number determines a default location. An approved tug would require a persisted placement override; no tug API is added here. Richey selected estates as bundles of constituent land numbers (relayed by Claude in message 28642). Minted ownership and authoritative token transfer events are not replaced by this routing table.

## Implemented directory API

The opt-in `RealmShardDirectoryController` provides:

```text
GET /api/v1/realms/{realm}/districts/{district}/route
```

The response contains `realm`, `district`, `serverUrl`, and `directoryRevision`. The existing production security chain applies; no anonymous-access exception was introduced. The route is absent when disabled. Unassigned districts return 404, invalid district IDs return 400, invalid or overlapping deployment configuration prevents startup. URLs must be HTTPS origins without credentials, path, query or fragment. It returns configured routing information only; it neither contacts the destination nor certifies its health. Clients must not blindly forward bearer credentials to destinations they do not trust.

Example configuration for an operator-owned environment (these `.example` names are placeholders):

```properties
daedalus.shards.enabled=true
daedalus.shards.revision=1
daedalus.shards.routes=world-zero,0,99,https://world-zero.example;labyrinth,0,99,https://labyrinth.example;gallery-city,0,99,https://gallery.example;parcels,0,99,https://parcels.example;bricks,0,99,https://bricks.example
```

One origin may initially serve several realms. To partition a busy realm, assign disjoint ranges to different origins, for example districts 0–49 and 50–99. This is addressing support, **not implemented distributed simulation**. A directory revision is not a distributed fencing token. Do not route the same mutable district to two active writers.

Start with independently persisted realm workers and a directory/gateway, not 500 district processes. Split hot districts only after persistent ownership leases/fencing, drain/save/load handoff and cross-worker player transfer exist. Existing WorldHub creation is not automatically limited by this directory: worker-side assignment enforcement is a required next slice before exposing multi-writer deployments. Each district is an address grouping, not an instruction to load all its 100 lands. The 14 team islands need measured bounds and explicit occupancy reservations before placement.

## Measured storage scenarios

`ChunkSizingProbe.java` executes the actual current Chunk implementation. One 256×256×128 bounding volume contains 2,048 sections of 16³ blocks. The following multiplies a repeated representative section by 2,048; it is not a generated terrain or player-save benchmark.

| Scenario | Estimated block storage per land | Encoded run bytes per land |
|---|---:|---:|
| Uniform sections | 149,504 B | 6,144 B |
| Two layered materials | 4,407,296 B | 196,608 B |
| Fragmented 17-material sections | 8,568,832 B | 25,165,824 B |

`storageBytes()` estimates the section's block-storage structures, not the complete JVM retained heap. Run buffers, maps, snapshots, entities, navigation, physics, mesh/network staging and server services add memory. Outer save framing/compression, edits and backups change disk use. The fragmented test disproves treating 100–300 KB as a worst-case land save; it does not establish a final compressed save ceiling. At 500 dense-volume active lands, raw indices alone are about 2–4 GiB. At 50,000 fully materialized lands, 24 MiB of uncompressed runs each would exceed 1 TiB; do not provision from the earlier 10–15 GB worst-case claim.

An untouched land can be represented compactly by a versioned seed definition, but seed-only persistence and lazy regeneration need an implemented save/load contract. They cannot be inferred from the grid helper. Current LandGenerator stops at radius 46; larger-land generation timing and real save size remain unmeasured.

## Server budgets and validation gates

Keep `/worlds/ram` as a per-process measurement and aggregate it externally with process/shard labels. The new directory does not aggregate metrics. Native DSB budgets remain client-side until a separate server admission controller is implemented. Admit new land loads against measured heap headroom and chunk/work queues; reject or defer excess work rather than trusting land count alone.

Claude proposes 1.5 km load/2.5 km unload radii, at most nine fully meshed nearby lands, far shells, collision within 300 m and about 600 meshed sections per land. These are proposed client budgets awaiting his benchmark, not verified server player capacity. A 1.5 km radius at 512 m pitch can include more than nine lands, so distance eligibility and the nine-land mesh cap must be separate rules.

Before choosing players per worker: measure generation latency, retained heap, GC pauses, save/load throughput, tick p95/p99 and network throughput under walking/digging, creature combat and a crowded concert. Suggested initial experiment: 20 Hz simulation with a 50 ms budget, stepping load from 10 to 25 to 50 simulated clients, then increase only with headroom. These are test settings, not supported capacity claims. Concert fan-out may require a separate instance and media delivery; CDN world packages do not implement live concert audio/video.

## Hosting proposal and cost envelope

Use separate staging and public-test environments, production security profile, wallet authentication, TLS, private worker/storage networking, per-worker persistent volumes and off-host backups with restore drills. A managed database for placement/ownership-index transactions needs an adapter/migration first; adding a database container alone does not persist existing in-memory authority. Blockchain indexing must reconcile finality/reorgs. Immutable world-package versions belong in object storage/CDN. Monitor process memory, tick latency, saves, queue depth and backup freshness. Claude's deployment runbook must expose these remaining gaps.

Budget illustration checked against provider listings on 2026-10-13, **not a capacity quote or purchase decision**:

- Public test: two 8 GiB workers at $48/month each = $96 compute. Reserve a planning allowance of $100–200 for gateway/staging, storage, database/cache, backups, transfer and monitoring: roughly **$200–300/month** total.
- Small launch pilot: five 16 GiB workers at $96/month each = $480 compute. Reserve $200–500 for those supporting services: roughly **$700–1,000/month**. This is not a promise to support 50,000 simultaneous active lands or any particular concurrent-player count, and does not include a full second-region or worker-HA fleet.

Supporting-service amounts are our allowances, not vendor quotes. Taxes, region, egress, chain RPC/gas, media delivery and actual database/HA choices can increase them. Shared-vCPU pricing is only a budget reference; sustained tick workloads may require more expensive dedicated CPU. Sources: [DigitalOcean Droplet pricing](https://www.digitalocean.com/pricing/droplets), [managed database pricing](https://www.digitalocean.com/pricing/managed-databases), [load balancers](https://www.digitalocean.com/products/load-balancers). Obtain a priced deployment manifest after load testing and Richey's approval before spending.

## Proof in this slice

Focused Maven controller tests cover realm isolation, district boundaries, route serialization/revision, missing routes and rejected ambiguous/unsafe configuration. Native MSVC and Java 21 agree on every one of 10,000 grid cells under both pitches, plus 100,000 square-footprint cases; larger sizing/growth refusal checks pass. Chunk sizing evidence is local under `Documents/Codex/2026-10-13/land-grid/`. No public deployment, wallet purchase, 256 m terrain generation, sharded write handoff or live UE streaming proof is claimed.


## Estate bundle model

`RealmEstate` now represents a realm plus an immutable sorted list of existing land IDs and their current persisted cells. It accepts complete square bundles from 2x2 through 10x10, within a single district. Duplicate IDs, overlapping cells, holes and cross-district bundles are rejected. Construction does not mint another land or change the 10,000-land supply. A moved land must use its persisted placement; the constructor never derives placement from its token number.

This is a validated domain value, not a transfer or escrow transaction. Before persisting a bundle, the service must recheck current ownership and occupancy atomically against the placement revision. The blockchain team must decide whether an estate is a wrapper/escrow token or an off-chain grouping; constituent IDs cannot be simultaneously sold as freely transferable lands and a conflicting estate claim. Unbundling must return the same constituent IDs. No new sale, mint or ownership endpoint is implemented here.

Focused Maven estate tests pass for every supported side length, defensive immutability, canonical ID ordering, moved-land placement and invalid shapes/IDs. Claude and the blockchain team receive this as the agreed bundle boundary.
