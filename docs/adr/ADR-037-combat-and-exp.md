# ADR-037: Combat and EXP — the Zelda II feel

**Status:** Accepted
**Date:** 2026-10-11
**Deciders:** RicheyWorks
**Charter:** ADR-036, pillar 1
**Prompted by:** "Zelda 2 is my favorite game of all time. I love how it feels, how the fights feel, beating
the enemies and how you gain exp." · "Some people will want to grind experience. We have no max level." · "You
also get randomly attacked … not on your home island though, unless it's night time or if you equip something
that turns that on."

## Question

What makes a Zelda II fight feel like Zelda II, and how much of that can a 3D realm keep?

## What Zelda II's fight is

- **High and low.** Standing, Link thrusts high and his shield covers high. Crouching, he thrusts low
  and his shield covers low, and he cannot walk while crouched.
- **Every enemy is a lesson in high and low.** Some guard one height. Some are only reachable at one.
  The Iron Knuckle moves its shield between the two and strikes at the other height, so you read its
  shield and answer it.
- **A hit hurts.** You are knocked back and blink, briefly untouchable.
- **EXP is the reward, and spending it is a choice.** Every enemy pays EXP. When the EXP covers the
  next level of Attack, Magic or Life, you choose which to raise, and the EXP goes back to zero. Life
  is cheapest and Attack dearest.
- **Losing costs EXP, not levels.**

## Decision

**1. The rules live in core, and the server serves them** (`/api/v1/hero/rules`):
- **`Height`:** HIGH or LOW.
- **`FoeKind`:** four foes. They are animals blighted by the meteor's dust (ADR-036's story), each one
  an echo of a Zelda II enemy:

| Foe | Echo of | Life | Power | EXP | The lesson |
|---|---|---|---|---|---|
| Blight slime | Bot | 1 | 1 | 2 | No guard; it strikes **low** at your shins, under a standing shield |
| Shardback | Lowder | 2 | 2 | 5 | Its crystal shell **guards high**: crouch and thrust low. It bites high, so a standing shield stops it |
| Dust wisp | Ache | 1 | 1 | 3 | It floats at head height: **only a standing thrust reaches it** |
| Stone knight | Iron Knuckle | 6 | 2 | 50 | Its **shield moves** between high and low, and it strikes at the other height. Thrust where the shield isn't, and your own shield is then already where its sword is going |

- **`Duel`:** who wins an exchange. A thrust is HIT, GUARDED or OUT_OF_REACH; a shield blocks a strike
  at its own height.
- **`HeroRules`:** Zelda II's level costs for the first seven levels: Life 50/150/400/800/1500/2500/4000;
  Magic 100/300/700/…/6000; Attack 200/500/1000/…/8000. **There is no max level.** Past the table, each
  level costs half again the last (Attack 8 → 9 is 12,000), capped at 10⁹ so the experience counter can
  always reach it. Grinding always pays. Damage grows with Attack, hearts with Life (three hearts, plus one per
  level, and a Life level also blunts blows), and the magic meter with Magic. Heal costs 4 magic and
  restores 3 hearts.
- **`Hero`:** an immutable record of EXP and the three levels. *Beat* adds the foe's EXP. *Raise*
  spends it and resets it to zero. *Fall* loses unspent EXP and keeps levels.

**2. The server keeps the score** (`HeroService`, `heroes.daeh`).
- **One hero per person, across every world**: the same hero crosses every gate.
- **The client reports which foe it beat; the server adds that foe's EXP from its own table.** A
  client cannot say how much EXP it earned.
- **Foes cannot fall faster than a sword swings:** at most one every 350 ms, otherwise `TOO_FAST`.
- **Routes:** `GET /hero`, `POST /hero/defeat`, `POST /hero/raise` (NOT_ENOUGH when short),
  `POST /hero/fall`.

**3. The fight in the realm** (Play mode, every world).
- **Controls.** **J** thrusts, **hold C** crouches, **H** heals. On a tablet: ⚔, ▼ (hold) and ✚,
  beside Jump and the stick.
- **The hero's kit.** A sword in the right hand and a shield on the left arm, both at stance height.
- **A thrust.** It lasts 0.24 s, can land in its first 0.14 s, and you recover for 0.36 s. It finds
  the foe in front of you, within reach.
  - **HIT:** damage, the foe is knocked back and blinks.
  - **GUARDED:** a clank, and you are pushed back.
  - **OUT_OF_REACH:** a whiff.
- **Foes come to you, as random attacks.** A few at a time, 9–14 cubes away, never near a spawn pad, a
  plaza or the obby. **Never on your home by day:** on an island, plot or parcel you hold, nothing comes
  for you until 8 pm by your own clock (the Animal Crossing way), and from then until 6 am they do.
  They close in, wind up where you can see it (they swell and raise a weapon), then strike at their
  height.
- **The hero is struck.** A shield at that height stops the blow, unless you are mid-thrust. Otherwise
  you lose hearts, are knocked back and up, and blink for a second.
- **The stone knight is drawn** with its shield and sword at their heights, so the duel can be read
  by eye.
- **HUD.** Hearts (with half-hearts), the magic bar, the three levels and EXP toward the cheapest next
  level.
- **Level-up.** When EXP covers a level, **LEVEL UP** offers Attack, Magic and Life with their costs,
  only the affordable ones enabled, and a Later button.
- **A fall.** Hearts run out: you lose your unspent EXP, keep your levels, and start again at the
  spawn.
- **Drops.** Beaten foes sometimes leave a heart or a magic jar.

## What it found

- **The test that reused a hero.** `restart.sh` reset the worlds but not `heroes.daeh`, so the second
  harness run met a "link" with 5 EXP left over from the first. The server was right; the test's
  expectation (5) was wrong for that hero. Each run now fights as a new hero, and the reset clears heroes
  too.
- **A count of stale results.** The first duel check recorded `lastThrust` after every thrust. A thrust
  that met only air left the previous result in place, which was then counted again as a hit. Thrusts
  are now numbered, and a duel step counts only a thrust that actually met the knight. A thrust into a
  foe still blinking from the last hit is now its own outcome (BLINKING), not a silent HIT.
- **Real time against a starved frame.** In the full run, at about 5 frames a second in software
  WebGL with six pages open, two existing checks broke: a running jump held for a fixed 1.3 s of real
  time, and a knockback measured 300 ms after the blow. Physics advances in fixed 1/120 s steps but only
  when a frame arrives, so a late frame meant too little simulated time inside the window. The harness
  now holds keys, and waits, until something happens (landing, falling, the knockback settling), as a
  player does, instead of for a fixed time. The obby run, alone, passed throughout.

## Numbers

- **Java tests:**
  - `HeroRulesTest`: 3 (high and low across every foe and both shield positions; EXP spent and reset;
    a fall; Zelda II's costs; every level does more than the one before)
  - `HeroControllerTest`: 4 (a fresh hero and the rules; a knight then Life; TOO_FAST; a fall;
    surviving a restart)
  - The posture test now covers 5 more routes.
- **Browser harness: a new "fight" section.**
  - Play arms the hero.
  - A standing thrust clanks off a shardback, and a crouching thrust beats it: +5 EXP on the server.
  - Reading the stone knight's shield wins the duel. 55 EXP opens LEVEL UP with only Life affordable.
    Choosing Life gives a fourth heart and resets EXP to 0.
  - Standing, the shield stops a shardback's bite. A slime's low blow gets under it and knocks the hero
    back.
  - A crouching thrust passes under a wisp; a standing one beats it (+3).
  - A fall loses those 3 EXP but keeps Life 2.
  - On an island the hero holds, attacks are off at 2 pm, on at 11 pm, and on anywhere else.

## Held

- **Server-simulated combat.** The server trusts which foe a client says it beat, though not the EXP or
  the pace. Proper checks wait for presence (ADR-042), when fights can be shared and witnessed.
- **An item that turns attacks on at home**, as RicheyWorks asked. It needs an inventory; it arrives
  with the shops (ADR-040).
- **The team assembling for a fight** (Dragon Warrior / Final Fantasy). Companions, ADR-038, next: when
  foes come, your befriended creatures appear beside you.
- **Spells beyond Heal** (Shield, Jump, Fire), **sword techniques taught in towns** (down-thrust,
  up-thrust), and the towns themselves. These belong to the map and story (ADR-040).
- **A side-view battle camera** (ADR-036). To be tried in the dungeons (ADR-039).
- **Companions in the fight.** These come in ADR-038, next.
