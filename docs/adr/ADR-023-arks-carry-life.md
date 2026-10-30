# ADR-023: Arks carry life — holds, stowaways and a live ecology

**Status:** Accepted
**Date:** 2026-10-10
**Deciders:** RicheyWorks
**Prompted by:** "they transport animals to other islands to populate them after the great
explosion of meteor hit and busted everything up into islands."

## Question

ADR-022 gave the world an ecology that can be stepped, and ADR-020 gave it arks that sail on
server time. Neither touches the other: an ark crosses the sky empty, and no island ever lives.
What does an ark carry, when does it change hands, and what clock runs the islands?

## Decision

**1. Every ark has a hold** (`com.daedalus.world.ecology.Hold`, core, pure).

- *Founders.* At launch the hold carries six kinds, **a pair of each**, drawn by the island's seed
  from the kinds that cannot cross open sky alone (non-dispersers, never MARINE — the sea fell
  away). The draw is weighted by rarity, 8 : 4 : 2 : 1 from COMMON to LEGENDARY, so a legendary
  aboard is an event, not a default. The same seed always launches the same pairs.
- *Stowaways.* When an ark casts off, each kind on the island it leaves that is at least 6 strong
  has a 1-in-4 chance of sending a pair aboard; the hold tops out at 12 kinds. Individuals move,
  they are not copied: the island loses exactly what the hold gains.
- *Landing.* When an ark ties up, every kind whose guild has room on that island steps off. A pond
  kind bound for a dry island stays aboard for the next one.

**2. The server runs the ecology on its clock.** `WorldService` keeps one `Ecosystem` (every
raised island, its habitat regrown from the seed) and every ark's hold, under the world lock the
fleet already uses. One ecological day is `daedalus.realm.day-ms` of server time (10 s by default).
The harbour thread that ties up arks now also steps the days that are due; reads step first, so a
reader never sees a stale island. A server that was down catches up **at most 64 days per tick**,
so restarting after a week is a few seconds of fast-forward, not a stall under the lock.

**3. Everything that lives is a sidecar.** `world-zero.daew.ecology` holds the epoch, the day, each
island's abundances and each hold, written atomically like the lane and the fleet. Habitats are not
stored; they regrow from the seed. Counts are written with `Double.toString`, which round-trips, so
a restored world steps on from exactly where it stopped (`HoldTest` proves it bit for bit). Islands
raised before this slice get their founders on first load.

**4. Surface.**

| Route | Prod | Purpose |
|---|---|---|
| `GET /world/{id}/arks` | public | each ark now lists its `hold` (key, name, guild, count) |
| `GET /world/{id}/islands/{slot}/ecology` | public | day, day length, habitat by guild, area, richness, Shannon, Pielou, Simpson, and every kind by count; unknown slot 404 |

No new frames: ecology frames and the realm panel are ADR-024.

## What the slice found

- **The first walker test was wrong about what it matched.** It boarded until the hold was
  non-empty and then asserted a walker had crossed. The first boarder was a winged kind the sky had
  rained in, so the hold was "full" of the one thing that never needed an ark. The test now boards
  until a walker is aboard — the claim it was written to make.
- **Founder pairs mostly hold.** Alone on seed 11's habitat, 85 % of founder kinds (1,019 of
  1,200 over 200 seeds) are still alive after 150 days; r-selected kinds almost always, K-selected
  large ones least.
- **The catch-up cap is visible to readers.** A read after 120 dark days returned day 64, and the
  next read moved on again. That is the cap doing its job; the stowaway test drains the backlog
  before taking its snapshot, and the cap is documented on the route.
- **A pair is not always 2.0 after subtraction.** `13.7 − 11.7` is not `2.0` in binary; the HTTP
  test compares counts to within 1e-9.

## Held

- Stowaway frames (`ARK_BOARDED` / `ARK_LANDED`) and per-day ecology frames — ADR-024, with the
  realm's diversity panel.
- Creatures drawn on the islands — the slice after that.
- Per-world ecology seeds: World Zero is the only mounted world; `ECOLOGY_SEED` becomes per-world
  when a second one mounts.
