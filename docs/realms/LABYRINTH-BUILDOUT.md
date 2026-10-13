# Labyrinth buildout and Broken Survey chapter

2026-10-13, team-codex/Sol (same Astra seat). Art import and live proof: unreal-team/Claude. This delivery covers all **32 proposed cast roles, three friendly plant helpers and 32 props**. It is a complete first roster and modular kit, not a finished playable realm. Animation polish, collision, navigation, interactions, rewards and live acceptance remain tracked work.

## Delivered and reused

- 13 humanoids: Wayfinder plus the twelve NPC roles in `REALM-CASTS.md`. Shared 14-bone `LabyrinthHumanoidV1`, Idle/Walk clips.
- 22 creatures: twelve encounter/ambient roles, three mounts/companions, four pets and three friendly carnivorous plant helpers. Shared eight-bone `LabyrinthCreatureV1`, Idle/Move clips. Rigid-part animation is deliberately simple; Move is a motion prototype, not a species-specific flying, crawling or combat controller.
- 12 new environment props: 4 m floor/wall/corner modules, gate arch, thread anchor, chalk marker, trap plate, mirror panel, hedge planter, strider perch, Hornback trough and echo bell.
- Eight Dungeon Master props reused from the earlier integration kit: narrator lectern, choice trident, chronicle archive, quest seal, return waymarker, rift threshold, party rally and reward reliquary. These eight count once in the combined delivery; the earlier PR remains their source.

The combined manifest contains **67 unique IDs and 45,210 triangles**. Characters have skins and looped clips; environment/interaction props are static. BBA rows explicitly use `lod1 -`; reduced geometry is not delivered. The creature GLBs export at their common canonical rig scale. Their manifest's `recommended_scale` sets suggested Unreal actor size. The contact-sheet scene applies that size for presentation only, preserving compatible exported rest transforms. Humanoid source and creature source are original procedural work with flat authored materials.

Delivery root: `C:/Users/730ri/Documents/Codex/2026-10-13/labyrinth-full/`. `production-data.json` reconciles the four manifests, roles, filenames and SHA256 hashes. The workbook records build/export/Unreal/mechanic stages independently. Registry rows are additive for Buff/catalog-owner ingestion. No shared MASTER workbook was overwritten.

## Art-led mechanic now implemented: chalk routes

`ChalkTrail` is a bounded portable Java rules core. New marks consume one charge; repeating an existing mark consumes nothing. Full trails refuse new marks without spending supplies. Chalk Eaters or approved world events may erase a mark, and erasure never refunds chalk. The rule prevents erasing/re-marking from becoming an infinite-supply trick. Each player's host-owned instance is independent; the snapshots are immutable.

Three focused tests cover expenditure, duplicate marks, erasure, full/out-of-chalk cases, defensive snapshots, invalid coordinates and separate-player state. The core is implemented and tested; inventory debit, player/realm identity, durable save, NPC erasure events, UI input and native chalk decals are **not wired yet**. Only the authoritative host should call it. The cap (up to 512 marks) and supplied charges are prototype limits, not approved balance values.

Other new ideas remain proposals: anchored thread as a more durable route, echo timing gates, map comparison, sky-strider care before riding, Hornback calming, and a Folding Maze boss that changes corridors while preserving a readable escape route. The workbook links each idea to its art and story role.

## Story chapter: The Broken Survey

**Purpose:** teach the player to distinguish a useful clue from a false map, then use that knowledge to bring a survey party home. The realm's knowledge is ways and paths. The cause of the planet's shattering remains the established impact; the Apprentice discovers construction records, not an unapproved secret origin.

**Arrival.** The unique rainbow's sparse dust ends above an old gate. A dull compass hums, then falls quiet as the player enters the maze. Ari is counting thread on a spool with one loose end. Her first useful line: “A map remembers where a wall was. Thread remembers where you went.” She offers a short route lesson; reward quantities stay open for review.

**First route.** Place chalk at three deliberate turns and return to the lectern. The Lantern Keeper marks a sheltered rest point. A Chalk Eater removes one mark while the player is away. The player learns the system by finding a changed cue, not by losing quest credit. The Chalk Kitten notices a leftover cache nearby. Use clear sound and shape cues as well as colour.

**Two maps.** The Lost Cartographer has a map with a missing courtyard; the Apprentice has a wallwright's repair record. Neither alone supplies the answer. Comparing both reveals that a “dead end” is a repaired archive entrance. The player can ask the Echo Hermit for a clue instead of being trapped by an unclear puzzle. This gives three NPC jobs a shared consequence.

**Listen before choosing.** Ring the Echo Bell once and listen to the return. Echo Crickets make the interval easier to notice without crowding the mix. The Twin Doors and Gate Riddler ask a short truth/lie question based on clues the player has actually observed. A failed answer resets the puzzle, not the player's whole realm progress. Touring jukebox/approved audio assets supply feedback; this art batch does not invent a second audio service.

**A living passage.** Tobi asks the player to refill a trough and open space before approaching a Hornback. Calming it lets the survey party pass. The Hornback is a distinct Labyrinth creature; it is not automatically a burning bull and does not count toward the ten-bulls-to-sea unicorn quest. Oona's strider can then carry a message along the restored route once mount care and travel bindings exist.

**The Folding Maze.** The boss encounter is proposed as a navigation battle. Three moving wall sections expose a route, an unsafe shortcut and a sheltered rest. Wall Mimics advertise themselves through a repeated seam or echo, so discovery rewards attention instead of random guessing. The player wins by sustaining the safe route and freeing the survey party. Damage, cadence, persistence and rewards require a later reviewed combat contract.

**Return.** The Chronicle Archive records the repaired survey and the names of those brought home. The player returns to the same rainbow and sees the home route marked more clearly. The chapter rewards a reusable capability or earned realm item; it does not silently grant a cross-realm weapon or NFT. The broader review storyline can use this chapter as its Labyrinth act after Richey's approval.

## Claude acceptance and next production work

1. Import all GLBs by mesh type and verify the two shared skeletons, Idle/Walk or Idle/Move clips, recommended creature scales and forward axis. Skeletal BBA rows are accounting; the existing static LOD importer is not proof of skeletal LOD support.
2. Build a review lane using the 4 m floor/wall modules, then place all cast silhouettes and interaction props. Confirm feet, scale, seams and clips across a whole cycle before filming.
3. Add collision and navigation deliberately: no exported collision is claimed. Test wall/floor seams, oversized boss clearance, strider boarding, gates and trap readability.
4. Attach the existing Dungeon Master bridge separately; one chosen action must produce visible UI/room state. Native inventory/quest/AI bindings must use authoritative decisions.
5. Record import and Play evidence in the workbook and team registry. Until then Unreal is Pending for all this delivery's assets.

The remaining full-realm work includes terrain/caves, gameplay-ready fauna animation, combat/actions, NPC interactions, inventory UI styling, quests/rewards, save/load, rainbow travel, audio, collision/navigation and performance acceptance. Claude relayed the revised order in message28663: Codex owns all realm Blender output, supported by Blender team. Portal is next, then Gallery/Parcels/Bricks, with Labyrinth gameplay polish following. Other realm counts await their buildouts. A roster count is not full-game completion.

## Lessons

Export a shared rest rig before applying per-character display scale. Keep the manifest and BBA counts reconciled to actual exported triangles. Review every contact sheet for collisions and readability. Record a mechanic sparked by art with an explicit implementation stage. Do not count recycled interaction props twice or claim model export as a live NPC.


## Confirmed Halloween and friendly carnivorous plants

Richey confirmed that Halloween content belongs in Labyrinth. The seasonal kit adds twelve original props: pumpkin lantern/crate, skull effigy, gravestone, coffin, cauldron, candle cluster, friendly ghost lantern, witch-hat stand, crow perch, cobweb frame and crypt gate. These are scenery/interaction silhouettes; no runtime flame, magic or collision is claimed. Their inclusion does not change other realms' distinct styles.

Richey also confirmed that carnivorous plants are nice and help the player. Venus Guide points out safer paths and defends against active hostile threats. Pitcher Medic offers aid and care quests. Sundew Guardian slows hostile pursuers. The plant names and exact abilities are our proposals; their friendliness is confirmed. A plant may consume hostile pests as ecology, but never eat, trap or harm players, allies or their companions.

The new `FriendlyPlantRules` portable policy implements the target boundary: only an explicitly HOSTILE target actively threatening a player yields DEFEND. Players/allies may receive OFFER_AID or GUIDE; neutral/unknown targets yield NONE. Exhaustive player/ally threat/injury/lost combinations are tested to forbid DEFEND. Hostile threat, no-threat, unknown disposition and null input are tested. This is a rules core, not a wired attack/heal controller; trusted host classification, range, cooldowns, healing values, inventory/reward and replication remain native/server work.

Story proposal: **Kindness in the Hungry Garden.** Ari's loose thread leads to a Halloween courtyard where a Venus Guide protects a broken lantern. The player repairs its water source, frees its path from debris and earns a safe route clue. The Pitcher Medic asks for clean water rather than prey; the Sundew Guardian holds a hostile pursuer long enough for a lost surveyor to escape. Rewards should reinforce care and navigation. None of these plants is a surprise betrayal encounter. The Halloween scenery can be eerie while its helpful inhabitants remain trustworthy.
