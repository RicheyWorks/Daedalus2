# ADR-018: The Realm — seeded floating islands and a WebGL client

**Status:** Accepted
**Date:** 2026-10-10
**Deciders:** RicheyWorks
**Prompted by:** "go frankenstein mode and port what we need and begin the metaverse build" —
a Sandbox/Minecraft-style shared world of floating voxel islands, with land ownership and an
ecology twist, built from the projects already on disk rather than from scratch.

## Question

World Zero and World One finished every phase they set out (`DAEDALUS_WORLD_ARCHITECTURE.md` §8,
`DAEDALUS_WORLD_ONE_ARCHITECTURE.md` §6). Both docs park the next two ambitions as **NOT NOW**:
*large procedural terrain* and *a browser WebGL voxel client*. Those are exactly what a metaverse
needs first. What is the smallest honest slice that lifts both, and where do the other projects'
pieces go after it?

## Decision

**Daedalus is the host.** It already is an authoritative voxel server: chunked 16³ storage, a
durable DAEW store, parcels with ACLs and lease strings, STOMP world events, JWT prod posture,
determinism goldens and a plugin runtime. Every other project grafts onto it at a seam; nothing
replaces it.

**1. Island terrain is a pure function of a seed** (`com.daedalus.world.island`, core, no Spring).
`IslandGenerator.generate(seed, radius)` returns an `IslandPlan` — cubes relative to an origin
plus `IslandTraits` (area, trees, blossoms, pond, stream, waterfall, crystals, boulders, top,
bottom). It is the Blender `voxel_island.py` generator ported to world axes (Y up). Determinism is
the contract: `IslandNoise` is integer hashing on a lattice, every other choice is one
`SplittableRandom` drawn in a fixed order, and no hash-ordered collection is ever iterated to make
a decision. `IslandGeneratorTest` pins seed 11's SHA-256 digest. A seed *is* an island — which is
what later lets a token carry a number instead of a world.

**2. Islands live on a lane.** Slot *k* is centred at `(96k, 40, −96)` — up in the sky, clear of
World Zero's fixtures at the origin and of the +X maze street. 96 is not decoration: at the largest
radius an island reaches 40 cubes from its centre, and the footprint test failed at 64. Raising is
all-or-nothing, the same rule `stamp.apply` follows: if any target cube holds matter, nothing is
placed. The lane (slot, seed, radius) persists beside the DAEW file as `world-zero.daew.islands`;
traits regrow from the seed, so the sidecar stores three numbers per island and cannot drift from
the terrain.

**3. Block types are appended, never reordered.** `BlockType` ordinals are the DAEW byte format.
AIR..GLASS keep 0..4; GRASS, SAND, WATER, LOG, LEAVES, BLOSSOM, GRAVEL, CRYSTAL, CLOUD follow. The
old five-type pin became an ordinal-stability pin. Every saved world reads the same.

**4. The renderer reads the same REST and STOMP surface every other client uses.**

| Route | Prod | Purpose |
|---|---|---|
| `GET /world/{id}/chunks` | public | every non-empty chunk with revision and occupancy |
| `GET /world/{id}/chunk/blocks?x=&y=&z=` | public | 4096 ordinal bytes (base64) + the palette |
| `GET /world/{id}/islands` | public | the lane with traits |
| `POST /world/{id}/islands` | required | raise a seed into the next free slot; `LANE_FULL` is named |

Raising an island emits **one** `WORLD_REVISION_CHANGED` frame typed `ISLAND`, not sixteen
thousand block frames. Cube edits keep using `PUT/DELETE /block`, which go through `WorldOps` and
the parcel gate exactly as the well's and the automation driver's do.

**5. `/realm.html` is the fourth client.** Vanilla JS plus an import map (three.js 0.160.0 from
jsDelivr; SockJS and STOMP from cdnjs with the well's SRI hashes) — no build step, like the well.
Meshing is per chunk with hidden-face culling and a separate translucent pass for water and glass.
Look / Build / Break modes with 44 px targets; a tap acts, a drag orbits, so it works on a tablet.
Edits are optimistic and corrected by the server's answer or its frame. The well at `/` is
untouched and remains the default page.

**6. Island raising is not (yet) a drive capability.** `WorldOps.drive` has no parameter bag for
a seed and radius, and smuggling them through `mazeRef` would be a lie in the trace. Held:
`island.raise` joins `WorldZeroCapabilities` and `WorldZeroDrive.DRIVEN` together when the drive
signature grows a typed argument.

## The graft map (what comes next, and from where)

Surveyed 2026-10-10 across `C:\Users\730ri\projects`. Each row is a later slice; none is in this one.

| Need | Donor | Piece | Lands as |
|---|---|---|---|
| Island ecology | CSRBT | `experimental/ecology/TheoreticalModels` (MacArthur–Wilson with `Environment(area, temp, wind, distance)`, logistic, Lotka–Volterra), `CommunityMetrics`, `BetaDiversity`, `LifeTable` — pure `java.*` | a per-island stepper fed by `IslandTraits.columns` (area) and lane distance |
| Creatures | ComputerPets | the ~210-kind canon (`PetType`, `roster.json`, `catalog.ts`: rarity, habitat, temperament, dialogue) | species for the ecology pool and NPCs; new 3-D art needed |
| Land ownership | ComputerPets | `nft/EthereumNftService` (real ERC-721 `ownerOf` / ERC-1155 `balanceOf` via web3j), `WalletSignature.recoverAddress` | a **provider module** beside core (World One §4.5: no web3 in `daedalus-core`); add SIWE nonces |
| Provable deed history | echoes | hash-chain + Merkle proofs (`echoes-wasm`), verifiable in the browser | parcel transfer log |
| Multi-replica real time | SudokuPro | `GameSessionRegistry` (with its join-race fix), `RedisBroadcastRelay`, `RedisPresence`, `WsTicketService` | when one process is no longer enough (today ADR-005 single-instance holds) |
| Shard routing | LoadBalancerPro | `ConsistentHashRing`, `ReverseProxyWebSocketHandler`, `UpstreamHealthProber` | region → shard routing; needs a query-param key source (browsers cannot set WS headers) |
| NPC voices and quests | AI Dungeon Master | `LLMProvider` + `LocalStubProvider` + `TokenBudgetProvider`, content-pack format, `SandboxVerifier` | NPC dialogue with an offline fallback; a stricter mod gate |
| Arcades | BlackJackPro, minesweeper-pro | pure rules engine; Redis leaderboard | in-world cabinets |
| Assets | Blender connector | `claude-blender-connector` + `voxel_island.py` | props and creature models; the same island design on both sides |

## Consequences

- World Zero's acceptance list still holds: every KEEP row is untouched and the full reactor build
  is the proof.
- Two pre-existing failures were fixed on the way in, because a slice cannot start on a red build:
  `world.js` was missing from `ProdSecurityConfig.STATIC_SCRIPTS` (the well's world panel was 401
  in prod), and two `WebUiSmokeTest` style pins still asserted colours that the 2026-09-18 well
  commits had deliberately changed. `spotbugs:check` also failed at HEAD on six `EI_EXPOSE_REP`
  findings in World One classes that hold the caller's live `MazeGrid` by design; they now have a
  documented `<Match>` beside the maze cache's identical one.
- `.mvn/jvm.config` sets `-Xss16m`: on a stock Linux JDK 21 the server's test compile overflowed
  javac's stack. Windows did not; the setting is harmless there.
- The picking bug found by the browser harness (a ray exactly on a cube edge chose the empty
  neighbour) is fixed by locating the cube from the hit triangle's centroid.
