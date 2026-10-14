# Portal Expedition

Realm owner: Buckwild Portal coder. Entry point: `/portal-expedition.html?seed=7`.
Status: browser expedition source implemented; no tests, builds, native runs or deployment performed in this pass.

## Story and scope

The cube changes a hero, a sage and a scout into pixels, but does not erase their history. They are descendants
of the ark crews that survived the meteor. Across two towns, a castle and the long dark beneath the island,
they follow the queen's promise: “Our world broke, but we endure.” The final homecoming carries a recovered
star blade back to the portal. These scenes follow `docs/STORY.md`, `docs/REALMS.md` and ADR-052; all page art
is original canvas drawing, with the existing realm's original item and creature names.

The browser is a read-only consumer of the seeded realm. It is a local expedition with simplified duels,
not a replacement for `DaedalusRealmCore.h`, an Unreal integration, a multiplayer authority or a wallet.
The native engine retains its complete hero/sage/scout stats, learned spells, encounters, monster traits,
12-slot bag, animation, saves, party presence hooks and jukebox bridge.

## What is implemented

| Surface | Behavior |
|---|---|
| Seed selection | Signed 64-bit seeds remain strings/BigInts so Java long seeds are not rounded by JavaScript. Reads `GET /api/v1/retro/{seed}`. |
| DRR 1 reader | Parses every emitted fact: seed/name, item, monster, map/row/zrow/end, zone, link, chest, door, NPC, shop, boss, spawn, portal and news. Checks record identifiers, numeric bounds, map dimensions/tiles, duplicate keyed records, references, placed chests/locks and portal tile. Rejects unsupported specs. |
| Seeded travel | Moves on the actual Java tile grids, with impassable water/mountains/stone/walls/counters. Town gates, field entrances and reciprocal cave stairs follow actual DRR links and map exits. Entering a destination stair does not immediately bounce back. |
| Visuals | Original pixel terrain, party trail, NPC palettes from the spec, original monster silhouettes, torch light, discovery fog, zone overlays, local duel screen and responsive seed atlas. No external library, font or image dependency. |
| Inputs | Arrow/WASD hold movement, E/Space interaction, touch direction controls, canvas/atlas taps and clicks. BFS walks an actual reachable route and stops on a transition. Escape, direct movement, focus loss or page hiding stops a route. |
| Keepers | Reads their real dialogue and seed-specific directions. News speakers show real news lines. Shopkeepers are reachable across counters, use actual stock/prices and accept eligible sales. Innkeepers use actual inn prices; the queen restores the party and establishes a refuge. |
| Locks and chests | Matching bronze/silver/star keys are consumed. Gold, item and mimic chest kinds come from the seed. Mimics resolve through a local duel before the chest is marked open. A guardian blocks traversal until its local duel is won. |
| Supplies | Herbs, tonics, torches, wings, might/life seeds and equipped weapons/armor have local expedition effects. Found-only goods are never inserted into shop stock. Equipped gear cannot be sold until replaced. |
| Journal | Nine tracked chapters: portal registration, first-town conversation, queen's blessing, far-town conversation, cave entry, silver key, Shard Tyrant, star blade and homecoming. Tracks visited maps, spoken NPCs, collected items, opened chests/locks, observations and guardian victories. |
| Field research | Displays exact zone weights as percentages of table total and group ranges. A local seeded PRNG draws optional sightings from those weights. First observation of a zone gives local survey experience. Field ambushes are reserved for the full native game. |
| Persistence | Debounced `localStorage` saves, keyed by realm seed and a normalized spec fingerprint. Restores bounded local progress only for that spec. Exports a JSON visitor journal with explicit lack of ownership authority. Storage failures leave play available and show the export path. |
| Server unavailable | Offers an explicit button for the existing shipped `Content/Realm/realm-7.drr`, embedded in the script. It is always labelled **offline visitor / shipped seed 7**. A failed requested seed is never silently fabricated or substituted. |

## Browser expedition rules

These rules are deliberately smaller than native party combat and are labelled in the UI.

1. The party starts with a local expedition kit: 160 shared health, 36 focus, 180 local gold, three herbs,
   one tonic, two torches, wings, a club and clothes, when those items are present in the spec. This kit is a
   visitor game allowance, not a server entitlement.
2. The bag holds up to 12 distinct item kinds, with stacks. This differs from the native 12-slot inventory.
   Consumables and sales make room. Matching keys remain consumable, and item discovery remains recorded
   after the item is used or sold.
3. Encounters occur at mimics and guardians. Commands are strike, blaze, mend, guard, herb, tonic and retreat.
   Spec health/attack/defense, `DOUBLE`, `BOSS`, experience, gold and drop weights drive these local duels.
   Other native traits are shown as field notes and are not simulated here.
4. Rank is `1 + floor(local XP / 80)`, capped at 13. Strike uses local base attack, rank, weapon and might;
   defense uses local base defense, rank and armor. Blaze costs 6 focus, mend costs 5; guard halves the next
   enemy response and restores 3 focus. Duels share one party health pool rather than three native members.
5. Defeat returns the crew to the queen's refuge if blessed, otherwise the original spawn, and halves local
   gold. A battle itself is not resumed after a reload; the journal keeps its last saved party supplies and
   confirmed encounter outcomes.
6. Torch light persists through cave stair travel and ends on leaving the cave. Wings provide a local return
   to the portal. Neither action changes any world server state.
7. Discovery fog limits route planning to known cells. Turning it off exposes the spec atlas for visitors
   who want to plan a full walking route. Cave sight remains limited by torch light in the main viewport.

## Ownership and NFT release boundary

The realm seed is not a deed. This page sends no POST, wallet request, contract transaction, edit operation,
claim or mint. Its local gold and exported journal never confer property, NFT eligibility or native save
authority. The parent release hub can link here for a seeded visitor preview without inventing land supply,
prices or release dates.

Portal land release steps:

1. Product/canon owners decide whether Portal Realm land has an independent deed, is attached to the entry
   island's deed, or is purely a game instance. Record the decision and the portal-seed relationship.
2. Contract and server owners supply the real collection/chain identifiers, authoritative seed-to-deed
   mapping, mint eligibility, owner read surface and signed edit permissions.
3. Release operators approve supply, allocation, pricing, metadata, preview disclosures and a release date.
   Keep the browser's status as visitor preview until these facts exist.
4. Integrate authoritative ownership reads in the shared release hub. A claim/mint call belongs behind the
   approved pipeline; local journal state must never be used as proof of ownership or entitlement.
5. Release art through the existing queue. Seed previews can use original pixel art while READY sprites
   are integrated by the native realm owner under ADR-052's named trigger.

## Next steps for the Portal crew

1. Link the expedition from the shared metaverse/release hub, preserving `/portal-expedition.html?seed=<long>`.
2. Let the native owner wire `SetPartyNames` to real presence and `SetNews` to the town-board service.
3. Resolve the held jukebox API, then wire the existing native FIELD/TOWN/CASTLE/CAVE/BATTLE/BOSS/VICTORY/
   DEFEAT/INN cues. The browser currently labels cues as visual only and never invents a sound endpoint.
4. Integrate the first READY original sprite row through the existing art pipeline; keep source spec and
   save compatibility with ADR-052's native engine.
5. Agree the property model above before advancing Portal NFT release status.
6. When verification is authorized, review browser movement, counters, gates, stairs, spent keys, mimics,
   guardian passage, save restoration, offline identity and the absence of write/ownership requests.

## Integration contract and files

No dependencies or build step. Spring's existing static resource handling serves these four new files:

- `daedalus-server/src/main/resources/static/portal-expedition.html`
- `daedalus-server/src/main/resources/static/portal-expedition.css`
- `daedalus-server/src/main/resources/static/portal-expedition.js`
- `docs/realms/PortalExpedition.md`

The only remote request is `GET /api/v1/retro/{seed}` with `Accept: text/plain`. The client does not call the
server's `/check` route. It limits fetched specs to 512,000 text characters at parse time, 16 maps, and maps
up to 128×128. Fetches time out after 12 seconds and are cancelled when superseded. Errors leave an existing
expedition intact and identify which seed remains on screen.

Local save namespace: `daedalus.portal-expedition.v1:<seed>:<fingerprint>`. The fingerprint is a non-security
FNV-style compatibility tag, not a cryptographic proof. A server response and the embedded seed 7 can share
local progress when their normalized specs are identical; neither source upgrades that progress into authority.

Coordination: shared portal profile, server generation, native gameplay, release authority and this browser
expedition remain separate ownership lanes. The browser crew edits only the files listed above. The parent
crew lead handles team-link announcements and Pootscoot's engineering pipeline briefing.

Validation in this pass was source inspection only, per the request for no testing. No browser session,
test runner, build, Unreal/native execution, deployment or external publication was performed.
