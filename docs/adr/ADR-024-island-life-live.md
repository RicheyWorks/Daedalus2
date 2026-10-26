# ADR-024: Island life, live — ecology frames and the Life panel

**Status:** Accepted
**Date:** 2026-10-10
**Deciders:** RicheyWorks

## Question

ADR-023 made the islands live on the server, but only a REST reader could tell. How does a player
in the realm see an ark put its animals ashore, stowaways climb aboard and an island fill up day by
day, without polling?

## Decision

**1. One event, three kinds** (`IslandLifeEvent`, plugin-api, so plugins can listen too):

| Kind | When | Carries |
|---|---|---|
| `DAY` | the harbour tick stepped the ecology | latest day, kinds per island (slot → count) |
| `LANDED` | an ark tied up and something stepped off | ark, slot, the kinds that landed, richness |
| `BOARDED` | an ark cast off with stowaways | ark, slot, the kinds that boarded, richness |

`DAY` is one event per tick, however many days that tick caught up, so a server waking from a long
stop sends a handful of frames, not thousands. A tick with nothing due sends nothing. Events are
published after the sidecar is written, so a reader that reacts to a frame reads the state the frame
describes.

**2. Their own topic.** STOMP maps them to `/topic/world/{id}/ecology` as `EcologyFrame`, next to
`/events` (cube-shaped) and `/arks` (voyages). Slot keys are strings, because JSON keys are.

**3. The realm shows it.**

- Each island in the lane says how many kinds live there, or "barren — waiting for an ark".
- **Life** (a 44 px button beside Go) opens that island's panel: day, kinds, individuals, Shannon
  H′ and evenness, and every kind with its count and a log-scaled bar coloured by guild. The open
  panel follows `DAY` frames.
- Each ark says what it carries ("carrying 6 kinds"; long-press or hover shows the list).
- `LANDED` and `BOARDED` toast in plain words: "Cobalt Lark put Red Panda, Ferret, Toad and 3 more
  ashore on Isle 1".

## What the slice found

- **The harness tapped the wrong button.** It pressed "the first button in the island row" to fly
  home. Once Life sat before Go, that opened a panel and left the camera riding the ark, so the next
  build tap hit sky and no PUT ever came. Go now has its own class and the harness names it.
- **Overlapping fetches rendered out of order.** A `DAY` frame and the read it triggers can each
  start a fetch; the older answer sometimes painted last. The panel now renders only its newest
  request.
- **The harness misread its own page.** `"day 34" + "10 kinds"` across a `<br>` reads as
  "day 3410" in `textContent`. The day now lives in `data-day`, which is what the check reads.
- **A barren island does not stay barren.** By day 13 seed 11 had a beetle, a mallard and a haze
  dragon, all fliers rained in from the wild sky. The harness now asserts what is actually true:
  *no ark-bound kind* reaches an island without an ark.

## Held

- Creatures drawn on the islands: ADR-025.
- Per-kind arrival and loss frames on `DAY`. The richness map is enough for the lane, and a panel
  re-reads the island. Add them when a client needs the diff.
