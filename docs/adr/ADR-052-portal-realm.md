# ADR-052: The portal realm, an 8-bit RPG the Java engines generate and C++ plays

Status: accepted, 2026-10-12

## Why

Richmond showed NES Dragon Quest screenshots. His asks:
- "when we go through one of the new portals it should be this type game and look."
- "our character will change and our team will become this in this world."
- "we will use our jukebox that dev team is working on for music."
- "use our java engines as much as possible for helping generate."
- "the mechanics for keys chests randomness of creatures etc pls make it robust. lets make that game what it should
  of been."

Dragon Quest is Square Enix's. We take the genre and the NES feel, and only that. All art, monsters, names, font,
music cues and maps are original.

## Decision

**The Java engines make the realm.** `daedalus-core` `world.retro` generates a whole realm from one seed.

The field:
- A 64x64 island built from layered value noise: mountains, hills, forest, swamp, sand and sea.
- The portal home sits beside the spawn.
- Places are strung along breadth-first walking distance, the way the maze solvers search:
  - the first town a short walk out;
  - the castle further on;
  - the second town and the cave mouth at the far end.

Encounter zones follow the walk:
- Danger rises in rings out from the portal.
- Hills, forests and swamps keep their own tables wherever they are.
- Every zone's weights carry rarity. A lucky drip turns up about once in fifty fights.

Two towns and the castle come from templates that the seed varies:
- Each town has an inn, an item shop and a smithy, each with a counter and a keeper behind it.
- Each town has a storeroom behind a bronze lock.
- Townsfolk give hints the generator writes from the real map ("the cave mouth lies far to the southeast").
- The castle has the queen, a treasury behind a silver lock and a vault behind the star lock.

The cave has three dark floors, each from a different maze engine:
- B1 is the BSP dungeon. Rooms are filled in, so they read as rooms rather than as corridors.
- B2 is a braided recursive-backtracker maze. The silver key is placed here.
- B3 is a perfect maze. The star key sits in its farthest dead end, and the shard tyrant stands in the only passage
  to it.

Chests:
- Every chest is rolled from the loot table for its depth. Mimics are included at depths 2 and 3.
- The keys the story needs are placed, never rolled.
- Chests go into dead ends first. A chest is never placed where it would cut a floor in two; each one is checked by
  re-walking the floor.

Proof: `RetroProgress` walks each realm the way a party would.
- It goes through every gate, stair and edge.
- It opens what its keys allow and spends each key it uses.
- It buys bronze keys once it has reached a keymaker.
- It also checks that every chest, lock, link, shopkeeper and zone line agrees with the maps.
- **200 of 200 seeds can be finished.**
- A realm with the silver key swapped out is caught: the treasury lock and its chests are reported.

`RetroCodec` writes the realm as the **DRR 1** spec, plain text with one fact per line. A C++ core with no JSON
library can read it, and so can a person. The server serves it at `GET /api/v1/retro/{seed}` and
`GET /api/v1/retro/{seed}/check`. Both are public and read-only, use the maze generators' budget, and keep the last
16 realms.

**The C++ core plays it.** `DaedalusRealmDraw.h`, `DaedalusRealmSpec.h` and `DaedalusRealmCore.h` are standard
C++17 with no engine in them.

The screen:
- A 256x240 frame of 16-pixel tiles.
- Everything is drawn from shapes and tiny bitmaps: tiles, people, eight monster drawings, and an original 5x7 font.
- Monsters come in palette-swapped families, as the classics did.

The field game:
- The party walks in a line. Townsfolk wander, face you, talk, sell, and give the news of the day.
- There is a shared 12-slot bag, a STATUS screen and EQUIP.
- Shops buy, and sell at half price. The inn heals, cures and revives.
- The queen's blessing heals the party and becomes the place you wake after a defeat.

Keys and chests:
- Keys open locks of their own tier and are spent.
- Chests hold gold, gear or keys, or they bite.

Ambushes:
- Each step counts down to the next ambush. Forests, hills and swamps count for more.
- The group is a leader, its kin, and one time in three a stranger from the same table.

Battles:
- Commands are FIGHT, SPELL, ITEM, DEFEND and RUN.
- HEAL, ZAP, CURE and BLAZE are learned by level, and each class learns at its own levels.
- A mighty blow lands one time in sixteen.
- What monsters can do:
  - Poison bites each step but never kills.
  - Spores put a member to sleep.
  - Bolts ignore armour.
  - Some monsters heal each other, call for help or run away.
  - Hard foes shrug off everything except a mighty blow.
  - Guardians act twice and cannot be run from.
- Defeated monsters can drop items, and the party levels up.
- Lines play one at a time, and the HP shown falls with each line.

Caves:
- A cave is dark until a torch lights it. The torch lasts until you leave the cave.

Saving:
- `Save()` and `Restore()` mean the team keeps its levels, gear, bag and gold between trips.
- The same realm also keeps its open chests, unlocked locks and beaten guardians.

The jukebox:
- Music cues: FIELD, TOWN, CASTLE, CAVE, BATTLE, BOSS, VICTORY, DEFEAT and INN.
- About twenty sound events: CHEST, DOOR, LOCKED, HIT, CRIT, SPELL, LEVEL and others.

**In Unreal:**
- `SDaedalusRealm` copies the frame into a transient texture with nearest filtering, scaled to fit with black bars.
  It takes keys, the d-pad and the stick.
- It POSTs `{cue, changed, sfx}` to the `daedalus.Jukebox` URL when one is set; with no URL it only logs the cue.
- `ADaedalusHero::Interact` on a PORTAL cube enters the realm. The seed comes from the cube, so each portal has its
  own realm.
- So does `EnterRealm(seed)`. It fetches the spec from the server, falls back to the shipped
  `Content/Realm/realm-7.drr`, and restores `Saved/Config/DaedalusRealm.sav`. Leaving through the portal saves the
  party.
- Harness hooks:
  - `RealmInput` taps, holds, ticks, places, gives, forces battles, autofights and stands the party at the portal.
  - `RealmState` returns a key=value line.
  - `RealmCapture` writes a PNG straight from the framebuffer, so no viewport capture is needed.
- Bridge commands: `daedalus.realm` and `daedalus.realm_capture`. Play scenario: `realm`.

## Proven

- `RetroRealmTest`, 14 tests:
  - determinism;
  - 200 finishable seeds;
  - placed keys, and the tyrant blocking the star key;
  - zones and rings;
  - the codec round trip and its refusals;
  - the walk catching broken realms;
  - loot and encounter weights checked against the tables;
  - the shipped spec matching the generator.
- `RetroRealmControllerTest` (3) and the posture test.
- `realm_core_test.cpp`, 87/87, clean under ASan and UBSan. It plays the shipped realm with buttons only:
  - the bag and herbs;
  - poison;
  - the inn, buying and selling;
  - the elder's news;
  - the bronze lock and the storeroom chests, matched against the Java rolls;
  - the queen's revive;
  - silver refusing bronze;
  - the dark cave, the torch and three floors of stairs;
  - the guardian (no running), the star key, and the vault's STAR BLADE equipped;
  - a mimic;
  - field ambushes, all from the zone tables;
  - level 2 and ZAP's cost;
  - the lucky drip's hide;
  - defeat (waking at the castle with half the gold, to the defeat cue);
  - save and restore, in this realm and in another;
  - the portal home;
  - sound events;
  - all 15 monsters drawn differently.
- It writes 13 PNGs along the way.

## Held

- **Sprite art from the Blender team.** The realm draws itself today. Next comes an 8-bit sprite sheet path through
  the art queue (`Spr_` rows), on a named trigger: the first sprite row marked READY.
- **The jukebox's real API.** The cue names are fixed here. The URL is set by `daedalus.Jukebox` once the dev team
  names the endpoint.
- **News from the server.** `SetNews` exists, and the town board will feed it when the news-of-the-day service lands.
- **Party names from the player's team.** `SetPartyNames` exists; it waits on multiplayer presence.
