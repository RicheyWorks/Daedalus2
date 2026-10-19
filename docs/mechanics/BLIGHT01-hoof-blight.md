# BLIGHT01 — Hoof Blight (contest G172)

*Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/HerdOutbreak.java` (tests: `HerdOutbreakTest`, 10).*

## Story

The Hornbacks you calmed in LAB06 are a herd of **200** now, and a trader's ox has brought hoof blight to the next
valley. It will reach the plains within the month. Herd-warden Tamsin Reed has **150 vaccine doses** and a roll of
quarantine fence. She knows the rule her grandmother taught her: you don't have to dose every animal, only enough that
the blight can't find a new host faster than the old ones recover.

## Quest `q_hoof_blight`: "Sixty in a Hundred"

1. Choose how many Hornbacks to vaccinate before the blight arrives (`vaccinate(n)`, at most 150).
2. Optionally decide when the quarantine fence goes up (`fence(week, 0.3)`: from that week on, contact drops to 30%).
3. One sick animal walks in. Run the blight (`run()`).
   - **CONTAINED**: at most 10% of the herd falls sick. The herd keeps grazing and the pasture stays MEADOW.
   - **OUTBREAK**: up to half.
   - **EPIDEMIC**: more than half. The herd is laid up and the pasture scrubs over (`band()`).

Results with the defaults (200 head, r0 2.5) over 400 seeds:

| Plan | CONTAINED | OUTBREAK | EPIDEMIC | Share sick in a major outbreak |
|---|---|---|---|---|
| no doses, no fence | 43 | 0 | 357 | 0.896 (final size z = 0.893) |
| 40 doses (20%) | 84 | 2 | 314 | 0.637 |
| 80 doses (40%) | 181 | 219 | 0 | 0.341 (effective-R final size 0.350) |
| 100 doses (50%) | 269 | 131 | 0 | 0.219 |
| 120 doses (60%, the threshold) | 355 | 45 | 0 | 0.151 |
| 150 doses (75%) | 400 | 0 | 0 | none |
| fence in week 1 / 2 / 3 / 5 (no doses) | 361 / 233 / 108 / 50 | | | |

## Rules (seeded Reed-Frost chain)

1. Vaccinated animals are immune. One infected animal starts the blight.
2. Each week, each susceptible animal escapes each sick one with chance `1 − p`, `p = r0 / herd`, so it falls sick with
   chance `1 − (1 − p)^I`. With the fence up, p is multiplied by the fence factor.
3. The sick recover (immune) after one week. The blight ends when nobody is sick.
4. Herd-immunity threshold `1 − 1/r0` (`threshold()`, 0.6). Final size: `z = 1 − exp(−r0·z)` (`finalSize(r)`). With a
   share v vaccinated, a major outbreak takes about `finalSize(r0·(1 − v))·(1 − v)` of the herd.

Every roll is a splitmix hash of (seed, week, animal). `Settings.DEFAULT = (200, 2.5, 150, 60)`.

## What the tests pin

- `finalSize(2.5)` solves its equation (0.8926), and so do r = 1.01, 1.05 and 1.2 just above 1 (small z; the solver
  bisects, so it converges there too). There is no major outbreak below r = 1, and the threshold is 0.6.
- With no doses the blight is an EPIDEMIC in at least 320 of 400 seeds, and major outbreaks match z within 0.03.
- Vaccinating 75% (past the threshold) contains the blight in every seed; vaccinating 20% still leaves at least 250
  epidemics.
- At 40% vaccinated, major outbreaks match the effective-R final size within 0.05.
- More doses never mean more sick animals on average.
- A fence in week 1 contains at least 300 of 400 and beats a fence in week 3, which beats no fence.
- The fence runs on the ledger's own week clock: weeks before the fence match the unfenced run exactly, and the same
  seed and fence week replay the same blight.
- The weekly ledger adds up to the total, susceptibles only fall, and `band()` is MEADOW exactly when CONTAINED.
- The same seed and plan give the same blight, and bad plans and settings are refused.

## Host seam

- `HerdOutbreak.herd(Settings, seed)`, then `vaccinate(n)` from Tamsin's dosing UI and `fence(week, factor)` from the
  fence button, then `run()`.
- `Report.generations()` drives a weekly scrub (new cases, healthy left) over the herd. `Report.outcome()` and
  `band()` drive Tamsin's lines and the pasture cover.
- Ties: the herd is G03's Hornbacks (LAB06), and the pasture uses the battlefield `Vegetation` bands. The same
  threshold logic shows up in ISLES01 and CRANE01: a process that cannot replace itself dies out.
- Assets: `Prop_Vaccine_Kit` (herder's dosing satchel), `Prop_Quarantine_Fence` (hurdle fence section, tileable), a
  sick-Hornback material variant, and reuse of the staged `Mob_Lab_Hornback` + `Prop_Lab_HornbackTrough_Wood` (G03) (see UNREAL-QUEUE / BLENDER-ASKS).
