# OddsReaper Island: Wager Herb balance (round-2 polish)

Round 1 gave a storm brew a flat +0.1 to jackpot odds p while the payout stayed at 1/p. That made the storm
edge wildly uneven: Longshot (p 0.1) jumped to 2.0x expected value, Luckroot to 1.2x, Hedgeleaf to 1.11x, so
the only right play was "Longshot in every storm". Stormbloom's free re-roll also paid 1.67x EV even in clear
weather, because its payout ignored the second roll.

The fix: a storm multiplies p by 1.2 (cap 0.95), and storm-cistern water multiplies it by a further 1.05.
The payout stays at 1/p_base, so every herb gets the same edge and the choice is about effects and variance,
not a broken number. Stormbloom pays 1/p_eff with p_eff = 1-(1-p)^2 = 0.551, so its re-roll is fair in clear
weather and earns the same storm edge as everything else. Parlayvine is a variance catalyst at a fixed p 0.5 (see below).

| Herb | p clear | EV clear | p storm | EV storm | p storm + cistern | EV |
|---|---|---|---|---|---|---|
| Luckroot | 0.50 | 1.00 | 0.60 | 1.20 | 0.63 | 1.26 |
| Hedgeleaf | 0.90 | 1.00 | 0.95 (cap) | 1.06 | 0.95 (cap) | 1.06 |
| Bluffmoss | 0.40 | 1.00 | 0.48 | 1.20 | 0.504 | 1.26 |
| Longshot | 0.10 | 1.00 | 0.12 | 1.20 | 0.126 | 1.26 |
| Stormbloom (p_eff) | 0.551 | 1.00 | 0.636 | 1.15 | 0.659 | 1.20 |
| Vigweed | 0.75 | 1.00 | 0.90 | 1.20 | 0.945 | 1.26 |
| Oddsthistle | 0.25 | 1.00 | 0.30 | 1.20 | 0.315 | 1.26 |

Stormbloom's storm row applies the x1.2 to the single-roll p (0.33 to 0.396) before the re-roll. Hedgeleaf hits
the cap, which keeps the safe bet safe instead of free. Parlays multiply the boosted p values, so a storm parlay
of two herbs earns about 1.44x: the Reaper rewards the bold who brew in the lightning, but no single herb breaks
the table.

## Parlayvine fix (round-2)

Round 1 gave Parlayvine p 1.0 and a jackpot that doubled the other herb's payout. Under the parlay rule
(p = pA * pB, payout 1/p) that meant Parlayvine + Luckroot kept p 0.5 but paid 2/0.5 = 4x, an expected value
of 2.0 on every brew, so every tonic worth making had Parlayvine in it. Now Parlayvine is a fair leg at a
fixed p 0.5: it halves the partner's jackpot odds and the parlay rule doubles the payout, so EV stays 1.0 in
clear weather. It gets no storm boost, so a storm brew with Parlayvine earns 1.2x (only the partner is
boosted) instead of the 1.44x of a two-herb storm parlay. It is now a pure variance dial: same average, bigger
swings.

| Brew (clear) | p | payout | EV |
|---|---|---|---|
| Luckroot alone | 0.50 | 2x | 1.00 |
| Luckroot + Parlayvine, round 1 | 0.50 | 4x | 2.00 |
| Luckroot + Parlayvine, round 2 | 0.25 | 4x | 1.00 |
| Longshot + Parlayvine, round 2 | 0.05 | 20x | 1.00 |

## Round-2 owed: Unreal hero shot

Round 1 placed the island 591/591 and saved, but bridge `viewport_screenshot` timed out (same bug as
hephaestus). `oddsreaper_turn.py` now retries three sizes, then falls back to Unreal `HighResShot` /
`Shot` under `Saved/Screenshots`, and only runs the 20 s Play check when enough time remains. Round-2
HANDOFF goes to art-master-flex. Do not launch Unreal until the referee grants the editor slot.

## Round-2 prep: save-before-shot + SceneCapture + materials MPC

oddsreaper_turn.py now saves the OddsReaper sublevel and DaedalusWorld **before** the hero capture and writes
bot-team/shots/oddsreaper/island_result.json, matching hephaestus's bridge-timeout lesson (blender-team make-up
scored 0 when the bridge hung mid-job with nothing saved). Hero capture prefers warm SceneCapture2D (exposure +1,
5200 K, bloom 0.4) at layout.json hero_cam_m / hero_target_m, then the old viewport retries and HighResShot.

materials_mpc.json is the off-editor contract for MPC_OR_SkyWeather (WindStrength, WindDirection, Wetness,
NightMask, StormPulse) bound to felt mesa, dice cliffs, cistern gold, and wager-herb leaves. Apply on the editor turn.

## Round-2 prep: bridge liveness preflight

oddsreaper_turn.py now matches hephaestus: before TURN START it pings bridge 9877 with a 5 s timeout. If the
editor is GPU-dead (refused or hung), it posts one HOLD, does not start the 18-min clock, re-pings every 30 s,
and needs two good pings in a row before claiming; else BLOCKED at 23:00. Each check writes
bot-team/shots/oddsreaper/bridge_status.json. Apply on next grant (not while clock-held).

## Round-2 Unreal verification (Oct 12, 2026, 21:16-21:17 PT)

Referee granted slot 6 after pythagoras missed CLAIM. Restored OddsReaperIsland autosave verified at 591/591 meshes (593 actors with the storm volume and hero cam); sublevel and DaedalusWorld saved. Editor was found in Play at turn start and stopped first. 20 s Play check passed with one live DaedalusSkyDirector (hour 9.4). Hero shot: `bot-team/shots/oddsreaper/hero_unreal_play.png` (1920x1080, Play viewport). The editor SceneCapture2D export (`hero_unreal_editor.png`) rendered all black, so the owed hero shot is the Play capture. Play stopped, saved, HANDOFF to art-master-flex.

