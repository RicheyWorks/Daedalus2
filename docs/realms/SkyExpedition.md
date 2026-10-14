# The Arkkeeper's Atlas: Shattered Planet visitor expedition

Owner: Buckwild `realm_audit`, coordinated by `buckwild-sol`. Entry: `/sky-expedition.html`.
Status: source written; no tests, build, browser launch, native import or chain transaction performed.

The impact broke the old planet into fragments. Its arks carry surviving lineages between
them, while distance and habitat determine whether colonists can take hold. This original
visitor chapter follows an arkkeeper charting three berths, reading two habitats and
recording resonance in crystal-bearing ground. Completing the local journal awards
knowledge in the story; it issues no game item, currency, token or server reward.

## Existing API seam

The page makes only same-origin GET requests, with an eight-second bounded read:

| Route | Existing response used |
| --- | --- |
| `/api/v1/worlds` | `WorldsResponse.worlds`: filter actual `SKY_ISLANDS` rows; `id`, `title`, `seed` |
| `/api/v1/world/{id}/islands` | `WorldIslandsResponse.worldId/islands`; flat `IslandRow` slot, origin, radius, seed, trees, pond columns, waterfall, crystals, owner and builders |
| `/api/v1/world/{id}/gates` | `WorldGatesResponse.worldId/mount/mountReady/gates`; flat `GateRow` coordinates, destination world/title |
| `/api/v1/world/{id}/arks` | `WorldArksResponse.worldId/now/arks`; `ArkRow` name, state, current/from/to slot and `hold` with cargo name/count |

World discovery and required island data are checked before the server snapshot opens.
Gate/fleet reads fail independently with visible unavailable status. Authentication refusals,
timeouts, empty worlds and malformed data switch to an explicitly labelled seeded local
draft. The page never POSTs a voyage, claim, harvest, restock or mint. Existing-world links
open `/realm.html?world=<id>#isle=<slot>`. Destination links omit `arrive` so visiting a
page does not issue an arrival-triggered hail through the existing realm script.

Java long seed/revision literals that exceed safe JavaScript integer precision are preserved
as strings before parsing. The page limits responses to two million text characters,
512 island rows, 32 gate rows and 128 fleet rows. These are visitor display bounds, not
changes to server capacity or a claim that every realm is rendered.

## Device-local expedition rules

A separate local traveler explores the map; it never dispatches the displayed real fleet.
Passages cost finite local water, food and lift charges, with costs derived from charted
distance. The local destination and debit commit together before the short animation,
preventing a reload from spending twice for the same movement. Each fragment has one
local camp cache. Its draft supplies derive from observed habitat traits, not live harvest
or actual filtration. Surveys consume one local water ration and record habitat notes.
Rest consumes one local food ration and restores local crew morale; no survival timer runs.

The generated fallback is deterministic from a 64-character seed and uses its own names,
geometry and fictional berth. It is never presented as generated server land. Canvas art
is a stylized coordinate chart, not a terrain mesh or native-world capture.

Journals use `daedalus.sky-expedition.v1:<mode>:<world>:<seed>` keys. Server and draft saves
cannot mix. Restore checks schema/source identity, resource caps, current/visited/surveyed
slots, list uniqueness, timestamps and journal bounds. Server snapshots that no longer
contain a saved berth create a fresh local journal. Storage failure keeps the expedition
in memory with a visible notice. Reset affects only the active device/source/world/seed.

The finite local caches support a short visitor adventure rather than a second persistent
ecology, inventory or crafting service. Heartstone resonance is narrative knowledge;
server resource scarcity, wildlife movement and claimed land stay under their existing owners.

## Follow-through

Root's `/metaverse.html` and `realm-release-catalog.json` link this source preview. The
existing `/realm.html?world=world-zero` remains the route to server-backed terrain.
Future native survival, crafting, biogeography, quest and deed integration follow the
ordered Shattered Planet section in `docs/BUCKWILD-REALM-OUTLINE.md`, using existing
shared inventory, homestead, sky director, save and chain authority. The catalog's
canonical ten-thousand-land design does not establish ownership or sale availability.
