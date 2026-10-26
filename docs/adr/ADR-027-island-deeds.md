# ADR-027: Island deeds — ERC-721 metadata and a portrait from the seed

**Status:** Accepted
**Date:** 2026-10-10
**Deciders:** RicheyWorks
**Prompted by:** "so we could use it to make a nft land ecosystem?"

## Question

ADR-018 said a seed *is* an island, so a token can carry a number instead of a world. What does a
marketplace need to show an island, and how do we make it without a chain, a wallet or a picture
someone draws by hand?

## Decision

**1. Metadata first, chain later.** A contract needs only a base URI: `tokenURI(n)` is
`<host>/api/v1/world/world-zero/tokens/<n>`. **The token id is the island's lane slot.** The route
answers in the ERC-721 metadata JSON schema, plus the `attributes` and `external_url` fields that
marketplaces read:

- `name`: "Isle 1 · Rose Kite" (the slot and its ark's name)
- `description`: the seed and the story (the meteor, the ark that sails from its pier)
- `image`: the portrait below
- `external_url`: `realm.html#isle=1`, which opens the realm on that island with its Life panel
- `attributes`: Seed (string, so a 64-bit seed survives JavaScript), Radius, Ground columns,
  Trees, Blossom trees, Crystals (`display_type: number`), Waterfall, Pond, Ark, Kinds living

Everything but *Kinds living* comes from the seed and never changes. *Kinds living* is the island's
ecology right now, a live trait, the way game-backed tokens show a level.

**2. The portrait is grown from the seed, server-side, in pure Java** (`IslandPortrait`, core). It
is a 512×512 isometric view from +X+Y+Z. Cubes are painted far to near, faces shaded 100/80/64%
with the realm mesher's per-cube grain, water and glass blended, over the realm's sky gradient. The
frame fits the island; clouds do not count toward it and may crop. Cubes hidden behind three opaque
neighbours are skipped. The PNG encoder is about 40 lines: RGB, no filter, zlib, CRC32. No AWT and
no fonts, so it renders the same headless. `IslandPortraitTest` pins seed 11's pixel digest, checks
that `ImageIO` decodes the bytes to exactly those pixels, and checks the frame.
`GET /islands/{slot}/portrait.png` serves it with a day of public caching and an ETag of
`seed-radius`. It renders once per seed (about 50 ms) and is kept, because it can never change.

The portrait is the island **as its seed grew it**, not as players have since built on it. A deed
shows the land, not the latest graffiti. A live render is a different, later image.

**3. The realm shows the deed.** The Life panel carries the portrait as a thumbnail linking to the
token JSON, and `#isle=N` opens the realm on that island.

## What the slice found

- **Two arks moored at one pier sat inside each other.** Since ADR-020, every ark at an island used
  the same berth. Once the Cobalt Lark sailed to Isle 1, it and Isle 1's own Rose Kite overlapped,
  labels on labels; the deed screenshot made it obvious. Arks at the same pier now lie side by
  side, 26 cubes apart, in id order (0, +1, −1, +2, …), and the harness checks they are at least
  20 apart.
- **Framing on everything was wrong.** The first portrait fitted clouds and the waterfall, so the
  island used about a quarter of the frame. Framing on everything except clouds doubled its size.
  The margin check is now made on a cloudless plan, because a cloud cropping at the edge is
  intended.
- The first sprite test asserted the wrong pixel: row *a* is the rhombus's bottom tip, not its
  centre. The test was fixed, not the sprite.

## Held

- **The contract and minting** (ADR-028 with the wallet provider). Minting binds `ownerOf(slot)` to
  the claim from ADR-026. Until then the realm's own owner is authoritative and the metadata does
  not state an owner, because metadata is not where marketplaces read ownership from.
- **Pinning images to IPFS.** The portrait is deterministic, so its CID is too, and pinning can
  happen at mint.
- **A live portrait** that shows the island as built.
