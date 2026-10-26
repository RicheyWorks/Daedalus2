# ADR-036: The game — what each inspiration brings, and how Daedalus builds it

**Status:** Accepted (design direction; each pillar is built in its own ADR)
**Date:** 2026-10-11
**Deciders:** RicheyWorks
**Charter:** ADR-029 (amends the slice order)
**Prompted by:** RicheyWorks, 2026-10-11, in his own words:

- "I'm looking for a Final Fantasy type vibe and movement and adventure like a Zelda 2 / Link to the Past
  … with a twist of Animal Crossing and Adopt Me … and Pokémon."
- "I like the aspect in Zelda how you can explore a world and have those type of bosses and objectives and
  story line."
- "Zelda 2 is my favorite game of all time. I love how it feels, how the fights feel, beating the enemies
  and how you gain exp."
- "A Dragon Warrior / Final Fantasy 1 feel for world map exploration and gaining levels, and evolving like
  in Pokémon."
- "The Pokémon part: I like capturing or friending animals that can help you on the journey, that can
  evolve."
- "There will be races, adventures …"
- "The goal is to save the planet that got hit by a meteor and got blown apart into the galaxy, and we are
  learning to travel between the pieces."
- "Each culture over time evolved and looks different because of natural ecological reasons."
- "They use this [the maze art] to help them make it through the 3D mazes we make in each world … we will
  of course put everything in a maze that Daedalus would approve of."

## Question

Until now Daedalus has been a metaverse: worlds, land, gates and building. RicheyWorks wants a game in
it, an adventure with a feel he can name. What exactly does he like in each game he named, what does
Daedalus already have that matches, and in what order do we build the rest?

## The story everything hangs on

**The Shattering.** A meteor struck the planet and blew it apart. Its pieces drift through the galaxy:
the sky islands, the districts and every other world. The arks carried the animals that survived
(ADR-019..023). The sky gates past the rainbow are how people are learning to cross between the pieces
again (ADR-031).

**Why every world looks different.** Cut off from one another, the people on each piece adapted to
the ground and life they were left with, and over generations their cultures diverged. That is why one
piece is floating islands, one a district of plots, one a baseplate of bricks, one a city of
galleries, and one a labyrinth. The world styles (ADR-030..035) are those cultures, not themes. Each
culture's look, its mount and the animals that live there all follow from its ecology.

**The goal.** Save the planet. The player travels from piece to piece, learns each culture, makes
friends of its animals, descends into its maze-dungeon and defeats what guards its heart. Each piece's
heart, brought home, draws the pieces back together.

## What he likes in each game, and what Daedalus builds from it

| Game | What he named | What that means in play | Daedalus builds |
|---|---|---|---|
| **Zelda II: The Adventure of Link** (his favourite) | "how the fights feel, beating the enemies, how you gain exp" | Up-close sword fights where timing matters. You thrust high or low; enemies guard high or low, so you have to read them. Hits knock you back. Every kill pays EXP, and at a level-up **you choose** Attack, Magic or Life. Towns teach you new moves. | **Combat and EXP (ADR-037).** In Play mode: a sword with a high and a low thrust, a shield, knockback and a moment of invulnerability after a hit. Enemies guard high or low. EXP from every defeat, and at each level you pick Attack, Magic or Life. |
| **Zelda: A Link to the Past** | "explore a world, those bosses, objectives, story line" | A world you can roam freely. Each dungeon gives a map, a compass, a big key and a new item, and ends at a boss. A heart container after each boss. A clear chain of objectives (three pendants, then seven maidens). Two versions of the same land. | **Maze dungeons and bosses (ADR-039).** Daedalus' own generators build the dungeons, with keys, locked doors and a boss room. A dungeon's map is its maze art, a rainbow line through the maze. A heart after each boss. The story chain: one Heartstone per world. |
| **Dragon Warrior / Final Fantasy 1** | "world map exploration, gaining levels" | A world map you walk between towns, caves and castles. The land you're on decides which enemies you meet. Levels, gold, inns, shops. Vehicles (ship, canoe, airship) open up the map. | **The Shattered map (ADR-040).** A map of the pieces, with the vehicles we already have: arks, the helicopter, the plane, the drone. The terrain sets the encounters (the guilds: meadow, canopy, pond, …). An inn and a shop in each culture. |
| **Pokémon** | "capturing or friending animals that can help you on the journey, that can evolve" | Befriend or catch creatures. They fight and travel with you, gain levels and evolve. Their types matter. A Pokédex to fill. | **Companions (ADR-038).** The 260-kind creature canon (ADR-021) becomes befriendable: calm a wild creature, or win it over after a fight. Up to three follow you, fight beside you, level up and evolve. Their guild is their type. The Bestiary becomes your Pokédex. |
| **Animal Crossing** | "a twist of" | A cozy home you make your own, collecting and decorating, real-time days and seasons, neighbours. A museum. | **Home (ADR-041).** Your claimed plot, parcel or island is home: furnish it, display what you collect (Gallery City already hangs art), and let real days pass. The ecology already runs on a day clock (ADR-024). |
| **Adopt Me** | "a twist of" | Adopt a pet, raise it from a baby with care tasks, watch it grow. | **Pets (ADR-041).** Adopt a baby creature at home, care for it, and it grows. A grown pet can join you as a companion. |
| **Races** | "there will be races" | Timed runs, against the clock and against each other. | **Races through the mazes (ADR-039).** The obby clock (ADR-034) is the first one. Maze races follow, with best times on the server once presence exists (ADR-042). |

## What is already in place

- **Play mode (ADR-034).** A walking, jumping avatar with collision, checkpoints, a finish and a clock.
  This becomes the Zelda II body.
- **The creature canon, ecology and Bestiary (ADR-021..025).** Kinds, guilds, rarities, habitats and live
  populations. These become companions, encounters and the Pokédex.
- **Mounts and gates (ADR-031..035).** The arks, helicopter, plane and drone, and gates past the rainbow.
  These are the Final Fantasy 1 vehicles that open the map.
- **Maze art (ADR-035).** Every frame shows a maze and its solution. This becomes the dungeon map.
- **Mazes.** 27 generators and the solvers, which is where Daedalus started. These build the dungeons.

## Decision: the build order

What remains of the current ten slices follows the game, in the order that makes each step playable:

1. **ADR-037 Combat and EXP** (the Zelda II feel). Enemies, the sword and shield, high and low thrusts,
   knockback, life, EXP, and the level-up choice. The first fight you can win.
2. **ADR-038 Companions** (Pokémon). Befriend creatures, which then follow you, fight, level up and
   evolve.
3. **ADR-039 Maze dungeons, bosses and races** (A Link to the Past; Daedalus approves). A dungeon in
   every world, a boss, a Heartstone, the maze art as its map, and races through the maze.
4. **ADR-040 The Shattered map and the story** (Dragon Warrior / Final Fantasy 1). The map of the
   pieces, the quest chain to gather the Heartstones, and an inn and a shop for each culture.
5. **ADR-041 Home and pets** (Animal Crossing / Adopt Me).

After those: ADR-042 Presence (other players, shared races), ADR-043 VR, ADR-044 the realm follows the
chain, ADR-045 items and creatures on chain.

## Portability: how the game is built

RicheyWorks: "Don't forget our design philosophy of portability. That's how this project came together,
and that's how it will push forward. It's how the overall ecosystem of the portfolio grows."

Daedalus began as mazes that could be ported, and it grew into a 3D realm, Blender and Unreal because each
piece was carried rather than rewritten. The game follows the same rule:

- **The rules live in `daedalus-core`, in plain Java with only the JDK.** That covers combat, EXP,
  companions, dungeons and the story's state. The same core runs in the server, the desktop app and the
  plugin runtime, and can be lifted into any other project in the portfolio. `PortabilityTest` fails the
  build if core ever imports a framework.
- **The server publishes the rules as data.** For example, `/api/v1/hero/rules` serves the foes, the level
  costs and the damage. Any client can play by the published rules: the realm, Unreal, Blender, VR or
  another project.
- **Engines are renderers, not owners.** The realm (three.js), Unreal (DaedalusLink, the C++ core with
  parity tests) and Blender all read the same World Package and the same rules. A rule that only one engine
  knows is a bug.
- **Formats are open:** glTF, PNG, JSON, zip, and later on-chain records. None of them belongs to one
  engine.

## Feel targets (how we'll know)

- **A fight feels like Zelda II.** You can lose a fight by thrusting into a guard and win it by reading
  that guard, and a hit visibly knocks you back. The harness fights an enemy that guards high and checks
  that a high thrust does nothing while a low one lands.
- **Levelling is a choice.** At every level the player picks Attack, Magic or Life, and the choice
  changes the numbers that follow.
- **A companion matters.** A befriended creature lands hits in fights, levels up and evolves into a named
  next form.
- **A dungeon is a Daedalus maze.** It is generated, always solvable, and has a boss at its end. Its art
  is its map.
- **The story is a line the player can follow.** At any moment the game can say which Heartstone comes
  next, and where.

## Held

- **Turn-based battles** (Dragon Warrior / Final Fantasy 1 style). Fights stay real-time, Zelda II style,
  since that is "the feel". A turn-based mode can be a choice later.
- **A side-view battle screen** (Zelda II). The realm stays 3D; the high/low guard game carries the feel.
  A side-view camera in dungeons can be tried after ADR-039.
- **Unreal as the main renderer.** It comes when `setup-unreal.ps1` builds on RicheyWorks' PC
  (ADR-032). The game rules live on the server and in the shared C++ core, so both renderers play the
  same game.
