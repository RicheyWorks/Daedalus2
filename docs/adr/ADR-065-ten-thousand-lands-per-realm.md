# ADR-065: Ten thousand lands per realm

Status: proposed, 2026-10-13 (unreal-team). Needs: Astra (Java lane), blockchain-ruffff (deeds/items on testnet).

## Why

These are Richmond's words from 2026-10-13:
- "the nft islands all need to be right next to each other"
- "they are to spread out"
- "if people dont like where they are at they can be tugged by a air boolloon plane"
- "we will have a total of 10k islands nfts. every realm will have plots for sale as nfts and the items in them are
  nfts. like the dragon warrior realm we will have eggs that hatch that we sell that come with the land. its a
  dragon. and holding certain lands give more rewards"
- "each realm has 10k lands"

Today World Zero has 64 island slots in one row, 96 m apart (ADR-018/026). The 14 team islands were placed by hand
up to 60 km out. Neither approach scales to 10,000 lands per realm.

## Decision

**1. A land is (realm, number), with number 0..9999.** The number is the NFT's identity. It never changes, and the
deed (ADR-027/028) points at it.

**2. Each realm is a 100 x 100 grid of cells, and the numbers spiral out from the hub.**
- Cell 0 is at the realm's hub (World Zero: the spawn lane).
- Numbers wind outward in a square spiral, so low numbers are close to spawn and the gates. They are scarce, the
  way a city's centre is.
- Cell pitch is 256 m (rule 8): a land plus sky, with room for lands to grow after mint. At launch a 92 m land
  (ADR-050) has open sky around it, and neighbours are still a short flight apart.
- The grid is 25.6 km square. One formula, `cell(n) -> (x, y)`, shared by Java and C++ like the mesher and parsers,
  gives every land's place.

**3. Bigger holdings are estates.** An estate takes a 2x2, 3x3 or 4x4 block of cells and is sold as one deed with
one number (its lowest cell). The 14 team islands, up to 780 m across, become the first estates in World Zero's
ring next to the hub. They move once, as whole levels, with `daedalus_layout.py` and its undo table, after this ADR
is accepted. Estates are placed so they never split a district (rule 5).

**4. Tugging moves a land, not its number.**
- The land number and the cell it sits in are stored separately. The default cell is `spiral(n)`.
- The Tugboat Balloonist (REALM-CASTS) moves a land to a free cell of the same size.
- The deed stays the same. Only the land-to-cell table changes, and that table is part of the realm save.
- Swaps need both owners to agree.

**5. Only nearby lands exist in memory.**
- Lands are grouped into districts of 10x10 cells (2.56 km), 100 per realm.
- The streamer (ADR-063, budget DSB 1) loads districts within its load radius and unloads them past the unload
  radius.
- A land is a seed plus its edits. It is generated on load by `LandGenerator` and stored as v14 palette runs
  (ADR-064). An untouched land costs a few bytes on disk; one in RAM costs what its chunks cost.
- The test: 10,000 lands in a realm while RAM stays at what about 4 districts cost.

**6. Every realm has its own grid, and its lands fit its game.**
- Gallery City has plots on hung frames.
- The Parcels has fenced fields.
- Brick Realm has baseplates.
- The Labyrinth has maze blocks.
- The 8-bit realm uses overworld tiles. Its land comes with a dragon egg that hatches.

The grid math and deed shape are shared. What a land looks like, and what comes with it, belongs to the realm.

**7. Items in a land are their own tokens, and the rewards are not designed yet.**
- Items that come with a land, such as the dragon egg, are minted with the land and listed on its deed. Hatching
  changes the item's state, not its identity.
- "Holding certain lands gives more rewards" is recorded as a goal. The reward and income design belongs to Astra
  and blockchain-ruffff, and Richmond will brainstorm it.
- Testnet only. Mainnet, real money, prices and sales need Richmond's explicit yes (standing rule).

**8. Room to grow is reserved before mint.** Richmond (09:20): "after they mint i can keep upgrading the realms and
their lands and the game play ... i want to make the lands larger but we got to keep in mind blockchain constraints".
- The chain holds only a land's number, owner and a metadata pointer. Size, terrain, edits and items live in our
  world store. Bigger lands therefore cost nothing on chain.
- The one thing that cannot change after mint is where a land sits relative to its neighbours. Buyers pay for
  position (low spiral numbers sit near the hub). If lands grow past the cell pitch, neighbours collide, and moving
  everyone breaks that promise.
- So mint at a 256 m pitch (grid 25.6 km), not 128 m. Lands launch at today's 92 m and can later grow up to about
  240 m across (about 7x the area) in place, with no one moving. Depth can grow as well. Streaming by district
  keeps RAM flat whatever the pitch.
- What is promised at mint is fixed: number, position rank, size tier, richness roll (ADR-050) and the included
  items. Everything else, such as the look, the gameplay and new features, is an upgrade that only adds. Metadata is
  served versioned from our server (or IPFS with a version index), so upgrades show in wallets without re-minting.

**9. A mint is a bundle with random rolls (Richmond, 09:30).** "the nft always comes with a bundle of lands and
avatars and creatures at random like say one person may get a super rare bat a neon mummy ... minting is a chance at
a lot of different chances at rares legendaries and ultra rares".
- Every mint gives a bundle: one or more lands (rule 3 estates are bundles of land numbers), plus avatars and
  creatures rolled from the realm's roster (REALM-CASTS).
- Each roll uses a rarity ladder: common, rare, legendary, ultra rare. The odds are published.
- Rolls must be provably fair and fixed at mint. Use on-chain verifiable randomness (VRF, or commit-reveal), so
  nobody, including us, can steer who gets the neon mummy. The roll is recorded on the token and never re-rolled by
  an upgrade.
- **Shiny** (Richmond, 09:32): "shiny is also a very rare case any creature can have or avatar and it increases
  everything including max level increase".
  - Shiny is an independent, very rare roll on top of the rarity tier, so a common bat or an ultra-rare neon mummy can
    both be shiny.
  - A shiny raises every stat and its maximum level. The boost values are game balance, owned by Astra.
  - It is rolled at mint with the same fair randomness, stored on the token, and shown in game with a distinct
    sparkle.
- Risk to check before any paid mint: paid random rewards are regulated like loot boxes or gambling in some places.
  Richmond, the blockchain team and a lawyer decide this before mainnet. Testnet until then.

## Consequences

- `IslandOps` slots (64, 96 m) stay as World Zero's starter lane. Grid lands are a new addressing scheme alongside
  them, so no saved world changes.
- The 14 team islands get the one move they need, to their estate cells, instead of an interim pack and then a
  second move.
- Server: land table per realm (number, cell, size, seed, owner), plus a tug and swap endpoint.
- Unreal: the streamer gains districts.
- Blender: realm land kits, and the dragon egg with its hatch stages.

## Not decided here

- Reward formulas, prices, mint mechanics and supply per item type.
- Whether all 10,000 cells of a realm are generated at launch or opened in waves (the spiral makes waves natural).
