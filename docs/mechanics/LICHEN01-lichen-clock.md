# LICHEN01 — Lichen Clock (contest G91)

Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/LichenClock.java`
Tests: `daedalus-core/src/test/java/com/daedalus/world/battlefield/LichenClockTest.java` (10)
Links: shattered-planet canon (the aftershocks), ASH01 / CASCADE01 (the same fragment's ecology grid).

## Story

The planet did not shatter in one day. For two centuries after the first break, aftershocks kept dropping boulder
fields onto the fragments, and nobody wrote down when. The rocks keep their own record. Map lichen colonizes fresh
stone after a few years, grows quickly at first, then slowly for centuries. The largest lichen on a boulder field is
the oldest colonist, and its size dates the fall.

Surveyor Tamsin Coire has a pair of calipers and too little daylight. "Measure many and keep the biggest. A lichen
can be younger than its rock, but never older."

## Quest `q_lichen_clock` — "The Order of the Falls"

1. **Walk the fields.** There are 4 rockfalls with 2 boulders each, every boulder carrying 30 lichens. Each fall happened between 30 and 220 years ago (seeded).
2. **Measure.** You have 120 lichen measurements. Measuring n lichens on a boulder costs n and gives the largest.
3. **Date the falls.** Read each event's age from the growth curve (`age(diameter)`), then hand in a date for every event.
4. Outcome:
   - **DATED**: every date is within ±10 years and the order is right. Reward: the fragment's aftershock timeline joins the canon log.
   - **ORDERED**: the order is right but some date is off.
   - **MUDDLED**: the order is wrong.

NPC lines (Tamsin Coire):
- Start: "Biggest lichen, not the prettiest."
- Hasty: "One lichen a boulder? You've dated when it landed, not when the rock fell."
- Dated: "Four falls, in order. Now we know which shocks came after the arks left."

## Rules (deterministic from the seed)

- Each lichen colonizes 8 years after the fall plus a seeded exponential delay (mean 25 years).
- Growth: 0.6 mm/yr for the first 50 years, then 0.3 mm/yr, ±1 mm noise.
- `age(d)` inverts the curve and adds the 8-year lag. Bare rock reads as 8 years.
- The largest of n measured lichens can only grow with n. A small sample biases every date young.
- `ground(age)` paints the boulder field: BARE before the lag, MEADOW pioneer cover through the fast phase, SCRUB after.

## What the tests pin

- The two-phase curve and its exact inverse.
- Spreading the full budget dates every fall on seeds 1–6. One lichen per boulder is more than 3× worse and biased young.
- The largest lichen grows with the sample size.
- The budget runs out.
- DATED / ORDERED / MUDDLED judging.
- Events fall inside the age window.
- Ground bands, determinism, and bad input.

## Host seam

- `LichenClock.field(Settings, seed)`, then `measure(event, boulder, n)` for the calipers interaction, `age(d)` for the field notebook UI, and `judge(guesses)` once at the end.
- `ground(age)` paints the boulder field cells.
- Assets: boulder field (reuse rock kits), lichen decal (3 sizes), calipers prop (see UNREAL-QUEUE / BLENDER-ASKS).
