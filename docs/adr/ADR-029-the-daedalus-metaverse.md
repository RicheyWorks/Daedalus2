# ADR-029: The Daedalus metaverse — many worlds, one chain, portals between them

**Status:** Accepted (charter)
**Date:** 2026-10-11
**Deciders:** RicheyWorks
**Prompted by:** "everything Daedalus is, we add to this. This is just one part, the islands." · "a true
metaverse, where you can explore and take portals that can lead you to VR or different worlds — the
Minecraft or Sandbox look, the Decentraland look, the Roblox look, the Cryptovoxels look — and of
course the mazes will be in all worlds. We are using everything Daedalus was trying to be now." · "and
it all will live on the blockchain."

## The idea

Daedalus is no longer a maze lab with a world attached. It is a **multiverse**: many worlds, each
with its own look, joined by portals, with mazes in every one, and ownership on a public chain. The
floating islands (ADR-018..028) are the first world, not the whole project.

## One server truth, many looks

Every world is the same thing underneath: chunked cubes (World Zero's 16³ store), parcels with ACLs
and owners (ADR-026), STOMP frames, the plugin runtime. A world's **style** decides how it is
generated and drawn, not how it is stored, so a portal, a deed, a claim or a maze works the same in
all of them.

| Style | The look | Generated as | Drawn as |
|---|---|---|---|
| `SKY_ISLANDS` | Minecraft / The Sandbox | seeded floating islands, arks (today's Realm) | per-face voxel mesh |
| `PARCELS` | Decentraland | a flat grid of square parcels with roads; owners build scenes on theirs | smooth low-poly, soft light |
| `BRICKS` | Roblox | baseplate and studded bricks; blocky avatars | plastic studs, bright primaries |
| `GALLERY` | Cryptovoxels (Voxels) | a city grid: streets, plots with height limits | small voxels, pastel street city |
| `LABYRINTH` | Daedalus itself | World One mazes (23 generators, 10 solvers) at walking scale | stone walls, torchlight |

**Mazes are in every world.** World One's stamp (`StampOps`, the maze cache, living slabs) already
writes a maze into any world's cubes, so every style gets maze parcels, and a maze can be a portal's
destination.

**VR is a way of seeing, not a world.** In the browser, WebXR on the same three.js scene; on the
desktop, `daedalus-explore`'s OpenXR host (ADR-017). Any world can be entered in a headset.

## Portals

A portal is a typed link `(world, at) → (world, at)` that a player walks into. World Zero's `Portal`
object (open/seal, parcel-gated) is the start. Portals carry you between worlds, into a maze, or
into VR. Opening one where both ends are owned land needs both owners.

## On chain

| What | Contract | Today |
|---|---|---|
| Land (an island, a parcel, a plot) | ERC-721 deeds, one collection per world style, minted by realm voucher (ADR-028) | RealmIslands |
| Worlds | a registry: world id → style, seed, metadata, owner | — |
| Portals | links between two deeds, recorded when both owners sign | — |
| Items, avatars, skins | ERC-1155 | — |
| Assets | portraits and models pinned to IPFS; content-addressed, so the hash is the proof | — |

The realm **follows the chain**. When a deed moves on chain, the realm's claim moves with it,
following ComputerPets' `EthereumNftService` `ownerOf` pattern. Everything stays open source (MIT),
testnet first, and mainnet only behind a Safe and an audit, as fast-food-punks does.

## What we graft, and from where

| Need | Donor |
|---|---|
| Presence, many players | SudokuPro (`GameSessionRegistry`, `RedisPresence`, `RedisBroadcastRelay`) |
| Shards when one process is not enough | LoadBalancerPro (`ConsistentHashRing`, WebSocket proxy) |
| NPCs and quests | AI Dungeon Master (`LLMProvider` with offline fallback) |
| Creatures | ComputerPets canon (ADR-021) |
| Ecology | CSRBT TheoreticalModels (ADR-022) |
| Chain pipeline | fast-food-punks-token (ADR-028) |
| Models and art | the Blender connector |
| Arcades in-world | BlackJackPro, minesweeper-pro |

## Engines (amended 2026-10-11)

"Daedalus + Java + Claude + Blender + Unreal Engine 5 + blockchain. Generate a world once and deploy
it into different game engines. That has always been the goal."

**Daedalus is engine-independent.** The Java server owns the truth: worlds, cubes, islands, gates,
ecology, claims and deeds. Engines are ways of drawing and playing that truth. A world is generated
once and exported as a **Daedalus World Package**: a versioned manifest plus glTF 2.0 geometry and
the world's entities. Every engine loads that package and follows the same live API and frames.

| Component | Role |
|---|---|
| Daedalus (Java) | the world's truth and its rules: generation, persistence, ownership, frames |
| Claude | lead developer, architect and orchestrator, driving every tool below |
| Blender | the workhorse for 3D: models, animation, environments and textures (mounts, creatures, gate art); driven through the Blender connector |
| Unreal Engine 5 | the high end: world, gameplay, physics and rendering, the engine Halo moved to; a Daedalus plugin loads World Packages and follows the live API |
| The web realm (three.js) | the way in from anywhere: phone, tablet, browser and WebXR |
| MCP servers | give Claude hands in Blender (built) and Unreal (to build) |
| Python | automates the Blender and Unreal editors |
| C++ / Blueprints | Unreal gameplay systems |
| Blockchain | land, worlds, portals and items (above) |
| GitHub | every change versioned, tested and pushed |
| The RTX 4090 | local rendering, Unreal development and testing |

## The next slices, in order

1. **ADR-030 Worlds.** Mount many worlds on one server: a world registry with id, style and seed;
   `GET /worlds`; each world gets its own sidecars. World Zero and the islands keep working as they
   are.
2. **ADR-031 Sky gates.** Portals in the clouds past the rainbow, reached only by a mount (done).
3. **ADR-032 The Daedalus World Package.** Export a world once (manifest + glTF); load it in Blender,
   the realm and Unreal. The UE5 plugin and its PowerShell setup start here.
4. **ADR-033 The Parcels world** (Decentraland look): generator, renderer theme, claims and deeds per
   parcel.
5. **ADR-034 The Bricks world** (Roblox look) and blocky avatars.
6. **ADR-035 The Gallery world** (Cryptovoxels look): streets, plots, height limits.
7. **ADR-036 Mazes in every world.** A maze parcel in each style, entered by portal; solved runs
   recorded.
8. **ADR-037 Presence.** See other players move, from SudokuPro's presence pieces.
9. **ADR-038 VR.** WebXR in the realm; a portal into the OpenXR explore host.
10. **ADR-039 The realm follows the chain.** Deed transfers move claims; a world registry contract.
11. **ADR-040 Portals and items on chain.**

Each slice ships the way the Realm's did: a gate-green build, a browser harness that drives the real
pages, an ADR that says what it found, and a push to `main`.
