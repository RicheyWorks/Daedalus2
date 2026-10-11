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

## The next slices, in order

1. **ADR-030 Worlds.** Mount many worlds on one server: a world registry with id, style and seed;
   `GET /worlds`; each world gets its own sidecars. World Zero and the islands keep working as they
   are.
2. **ADR-031 Portals between worlds.** Walk into a portal and arrive in another world; the realm
   loads the destination and keeps your identity.
3. **ADR-032 The Parcels world** (Decentraland look): generator, renderer theme, claims and deeds per
   parcel.
4. **ADR-033 The Bricks world** (Roblox look) and blocky avatars.
5. **ADR-034 The Gallery world** (Cryptovoxels look): streets, plots, height limits.
6. **ADR-035 Mazes in every world.** A maze parcel in each style, entered by portal; solved runs
   recorded.
7. **ADR-036 Presence.** See other players move, from SudokuPro's presence pieces.
8. **ADR-037 VR.** WebXR in the realm; a portal into the OpenXR explore host.
9. **ADR-038 The realm follows the chain.** Deed transfers move claims; a world registry contract.
10. **ADR-039 Portals and items on chain.**

Each slice ships the way the Realm's did: a gate-green build, a browser harness that drives the real
pages, an ADR that says what it found, and a push to `main`.
