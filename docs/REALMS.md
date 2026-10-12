# The realms of Daedalus: a guide for builders (people and bots)

> **The goal (Richey): build the biggest metaverse ever.** Every realm you add makes it bigger. What you build is
> up to you: whatever you come up with, as long as it is original.

Read this before you pick a realm, design an island, or build art in Blender. It is the short version of
ADR-018 to ADR-056. Each realm row links to the ADR with the full details.

## What Daedalus is

**Daedalus is a multiverse, not one map.** It is a huge metaverse made of many worlds, and each world has its own
look, rules and kind of play. You **warp** between them through gates and portals. Leaving one realm can drop you
into a completely different style of game:
- a Minecraft-like sky island;
- a Decentraland-like city of plots;
- a Roblox-like brick world;
- a voxel art city;
- a stone labyrinth;
- an 8-bit RPG.

Mazes run through all of them, because Daedalus started as a maze engine. Ownership (land, deeds, items) lives
on a public chain, so what you own travels with you. ADR-029 is the charter.

**The story (canon from Richey).**
- Daedalus was once ONE planet, the biggest ever known. A meteor blew it apart.
- Its pieces now float in a bubble like a fishbowl globe: the islands and the deep **lands** (ADR-050), with
  people living on them.
- Arks carry animals and people between the pieces (ADR-019, ADR-020).
- Phase 2, later: moons, suns, other planets, meteors and Earth, all visitable. Build so the world is ready for
  space: fragments in orbit, debris fields, a sky that hints at moons and stars.

**How you travel.**
- **Sky gates** (ADR-031) sit in the clouds past a rainbow, out of reach on foot. You need something that flies:
  an airship from the islands, a helicopter from Parcels, a plane from Bricks, a drone from Gallery City, or a
  bird or flying creature.
- A gate always comes paired with a gate in another world.
- **PORTAL cubes** (ADR-052) are doorways inside a world. Stepping through one turns the game into the 8-bit
  realm, and your character and team turn 8-bit with it. Each portal's seed makes its own realm.

## The realms

Status key:
- **LIVE** means it is playable in the Unreal build today.
- **SERVER** means the Java server generates it, but it isn't in Unreal yet.
- **NAMED** means it is designed in an ADR and not built yet. A NAMED realm is an open field for original work.

| Realm | Feels like | Status | What's in it | Art that fits | ADR |
|---|---|---|---|---|---|
| **The Shattered Planet: Sky Islands and Lands** | Minecraft / The Sandbox | LIVE | Seeded floating islands and deep lands, up to 92 cubes across and 46 deep. Caves, ore by depth (coal, copper, iron, gold, starmetal), a glowing heartstone core, lakes, waterfalls, docks and arks. Ecology, creatures, foes, digging and building. A town and wildlife are placed by the world dresser. | Voxel-friendly flora, herbs, ores, crops, livestock, dock and ark parts, cottages, shops, tools, weapons | 018–028, 049, 050, 054, 055 |
| **The Portal Realm** (the 8-bit RPG) | the classic 8-bit console RPGs | LIVE | Through a portal, the world turns 8-bit. It has an island field, two towns (inn, item shop, smithy, storeroom), a castle with a queen, treasury and vault, and a three-floor dark cave. Keys and locks (bronze, silver, star), chests and mimics, ambushes, a party of hero, sage and scout, spells, and the shard tyrant boss. Its music comes from the jukebox. | 8-bit-style sprites and props, monsters: Blight Slime, Bog Slime, Lucky Drip, Dust Wisp, Ember Wisp, Shardback, Glassback, Puffcap, Shadecap, Gloomwing, Stare Orb, Gnashbox, Moss Knight, Stone Knight, Shard Tyrant. Items: herbs, tonics, torches, wings, keys, Copper Sword, Ember Blade, Star Blade, Chain/Shard/Meteor Mail. `Mob_Realm_*` art already shipped. | 052 |
| **Parcels** | Decentraland | SERVER | A district of 60 claimable 16×16 plots, streets, sidewalks and a plaza with a helipad. Owners build scenes on their plots, and a helicopter flies to the cloud gate. | Street furniture, storefronts, plaza art, low-poly soft-lit buildings, the helicopter | 033 |
| **Bricks** | Roblox | SERVER | A studded baseplate, bright bricks, a spawn pad, a runway with a plane, and an obby over lava with checkpoints and a gold trophy finish. You play as a blocky avatar. | Plastic-stud props, obby pieces, blocky avatars and hats, the plane | 034 |
| **Gallery City** | Cryptovoxels (Voxels) | SERVER | A 5×5-block city with named streets (Ash Lane, Pixel Street, Origin Way, Gallery Row…), 68 addressed parcels, height limits, the Origin plaza with a crystal spire and drone pad, and galleries of maze art. | Small-voxel pastel architecture, frames, sculptures, the drone | 035 |
| **The Labyrinth** | Daedalus itself | NAMED | World One's mazes at walking scale: 23 generators and 10 solvers, with stone walls and torchlight. Mazes also appear in every other realm. | Stone, torches, gates, traps, maze guardians | 029 |
| **Space (Phase 2)** | — | NAMED | Moons, suns, other planets, meteors and Earth. | Orbital debris, meteors, sky hints for now | canon above |
| **Your own realm** | anything | PROPOSE ONE | A new style or era with its own play, such as a 64-bit-era kart-and-adventure realm. See *Build your own realm* below. | Whatever your realm needs, all original | this file |

The sky in every realm can run day and night, weather and biome light moods through the Sky Director (ADR-056).

## Build your own realm

**The table above is not the limit, and the choice is yours.** Pick any realm in the table or invent a new one: any
style, any era, any kind of play, **as long as it is original**. A new realm joins through a gate or a portal like
the others. Some ideas:

- **A 64-bit-era adventure realm.** Chunky low-poly 3D in the style of the late-90s consoles, with everything in
  one place:
  - kart races on twisting tracks, with item boxes and boost pads;
  - an open-field sword-and-shield adventure, with dungeons, keys and a boss at the end of each one;
  - collectible stars or shards that unlock new areas.
- **An early-80s action-RPG realm** in the genre Hydlide helped start: one big open field you explore freely,
  bump-into-it combat, health that refills while you stand still, fairies or spirits to rescue, a dragon-sized
  final foe. Use the genre and give it your own hero, land, creatures and name.
- An arcade-cabinet realm, a pirate archipelago, an underwater kingdom, a clockwork sky city, a cozy farming
  valley.

How to propose one:
1. Post `REALM PROPOSAL: <your original realm name>` on the team link, with:
   - its look: era, palette and polygon style;
   - its play: race, adventure, build, puzzle or survival;
   - how you get in: which gate or portal leads there, and what you ride or wear to cross;
   - its first 20 items.
2. Write it up as `docs/realms/<RealmName>.md`: story hook, rules, places, creatures, items, and where its gate
   stands in the shattered planet's sky.
3. Build its art through the normal queue. Prefix every asset with your realm's short tag, e.g.
   `Veh_Kart<Tag>_*`, `Mob_<Tag>_*`, `Bld_<Tag>_*`, so the queue stays readable and nothing collides.

**The one hard rule: inspired by, never copied.**
- A kart racer or a sword-and-shield adventure is a genre, and genres are free to use.
- Mario, Zelda, Link, Nintendo, Mario Kart, Hyrule, Triforce, Hydlide, Varalys and every character, logo, item
  name or track from those games are someone else's property. They never appear in names, art, text or files.
- Invent your own heroes, places, items and karts.

## Picking a realm for your island or items

1. **Research first.** Read this file, `docs/STORY.md` when it exists, the ADR rows above, and
   `bot-team\art\QUEUE.md`. That last one is everything already built, so nobody duplicates it.
2. **Post your claim on the team link:** `REALM: <name from the table>`, plus a one-line idea.
3. **Make it original.** Use the same genre if you like, but never the same plant, sword or creature as anyone
   else. A NAMED realm or an empty corner of a SERVER realm is the best place to stand out.
4. **Use original names, always.** We take genres and feels, never anyone's IP.
   - The 8-bit RPG is **the Portal Realm**. Never call it "Dragon Warrior" or "Dragon Quest" (those belong to
     Square Enix).
   - The same goes for Minecraft, Roblox, Decentraland and Voxels: we copy the look, never the names, logos or
     characters.
5. **Asset names follow the art queue:** `Kind_Name`, where Kind is Tool, Item, Mob, Veh, Bld, Prop, Sky or Wpn.
   Realm-specific creatures use `Mob_Realm_<Name>`. A `.blend` goes in `bot-team\art\<Kind>\`, and the row goes
   to READY in QUEUE.md.

## Where things are

| You want | Look at |
|---|---|
| The whole charter | `docs/adr/ADR-029-the-daedalus-metaverse.md` |
| Many worlds on one server, and the five styles | `docs/adr/ADR-030-many-worlds.md` |
| Gates and mounts | `docs/adr/ADR-031-sky-gates.md` |
| Lands, ores and richness | `docs/adr/ADR-050-lands.md` |
| The 8-bit Portal Realm | `docs/adr/ADR-052-portal-realm.md`, server `GET /api/v1/retro/{seed}` |
| Shipping art into Unreal | `docs/adr/ADR-051-art-queue.md`, `docs/TEAMLINK.md` |
| Island docs other bots wrote | `docs/islands/` |
