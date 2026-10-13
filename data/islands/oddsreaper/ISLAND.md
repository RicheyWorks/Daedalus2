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


## Round-3 storm fix follow-up (Oct 12, 2026, 22:00 PT)

The storm volume is no longer forced at BeginPlay. DaedalusWorld is shared, so a forced volume would put every island's Play session in storm at dusk with the clock held, and Restore() never runs for a forced volume. Players get the storm through the view trigger; the editor turn forces it only in the PIE world (`force_storm_in_pie` in `oddsreaper_turn.py`, volume `apply_now` or a director fallback) right before the Play hero shot, and Stop discards it.


- 22:1x PT Oct 12: PIE storm pin. The MoodVolume view Tick (0.5 s) reads the PLAYER camera, which in Play sits on the main island, so right after apply_now it called Restore() and blended back to Clear daylight (8 s) under the SceneCapture hero shot. oddsreaper_turn.py now turns off trigger_on_view + restore_on_exit on the PIE copy only before apply_now, reads the director back after 1.5 s of ticks (held=true/false in the turn log), and re-forces via the director (clock held) once if it slipped. Headless check: tools/islands/oddsreaper/test_storm_pin.py.

## Round-3 off-editor: Storm Parlay Cookbook (Oct 12, 2026, 22:25 PT)

herbs.json now carries storm_parlay_cookbook — 8 signature two-herb brews (ReapersFavor, LightningLedger, LongOdds, HouseHedge, GhostBluff, CoinFlipDouble, ThunderSprint, OddsWhisper) with clear / storm / storm+cistern EV. Clear EV is always 1.0; storm multiplies boostable legs by 1.2 (cap 0.95; Parlayvine fixed); cistern adds x1.05. Headless auditor: tools/islands/oddsreaper/or_wager_ev.py (also re-checks every herb storm_ev against the formula). No Unreal touched.


## Round-3 turn runner: give-up + OR_NEXT (Oct 12, 2026, 22:17 PT)

oddsreaper_turn.py no longer aborts preflight at a fixed 23:00. Give-up defaults to turn start + 60 min (OR_GIVE_UP_MIN); an explicit OR_GIVE_UP=HH:MM that has already passed rolls to tomorrow. HANDOFF target is OR_NEXT (whoever the referee names; default art-master-flex only as a fallback). Headless: tools/islands/oddsreaper/test_give_up.py.

## Round-3 nft card (Oct 12, 2026, 22:30 PT)

nft.json hero_image now points at bot-team/shots/oddsreaper/hero_unreal_play.png (the real 1920x1080 Play shot from the round-2 turn). The editor SceneCapture2D export was all black and must not be used as the island card. Items stays 591. Headless: tools/islands/oddsreaper/test_nft_card.py.

## Storm Parlay Cookbook EV (from herbs.json)

| Brew | Herbs | EV clear | EV storm | EV storm+cistern |
|---|---|---|---|---|
| ReapersFavor | Luckroot+Vigweed | 1.00 | 1.44 | 1.588 |
| LightningLedger | Stormbloom+Oddsthistle | 1.00 | 1.383 | 1.506 |
| LongOdds | Longshot+Parlayvine | 1.00 | 1.20 | 1.26 |
| HouseHedge | Hedgeleaf+Luckroot | 1.00 | 1.267 | 1.33 |
| GhostBluff | Bluffmoss+Stormbloom | 1.00 | 1.383 | 1.506 |
| CoinFlipDouble | Luckroot+Parlayvine | 1.00 | 1.20 | 1.26 |
| ThunderSprint | Longshot+Vigweed | 1.00 | 1.44 | 1.588 |
| OddsWhisper | Oddsthistle+Hedgeleaf | 1.00 | 1.267 | 1.33 |


## Round-3 storm polish: stream + MPC + settle order (Oct 12, 2026, 22:42 PT)

oddsreaper_turn.py PIE storm path now (1) forces OddsReaperIsland streaming levels loaded+visible before MoodVolume search (sublevel streaming diagnosis — unloaded island meant volumes=0), (2) pushes materials_mpc.json storm scalars onto MPC_OR_SkyWeather when the asset exists (Wetness 1 / StormPulse 1 / WindStrength 0.95 / NightMask 0.25), (3) forces storm at Play start then settles 20s under storm before the hero shot (round-2 waited 20s in Clear then flipped late). Off-editor mood.json mirrors the oddsreaper_storm CSV row; headless test_mood_row.py + test_storm_pin.py cover it. No Unreal touched.

## Round-3 storm polish: post-settle re-pin + RGB daylight gate (Oct 12, 2026, 22:51 PT)

Diagnosed on-disk hero_unreal_play.png as still daylightish (mean RGB ~142/148/130, lum ~145, R>B) — the round-2 Play frame before storm fixes land in-editor. oddsreaper_turn.py now (1) re-checks storm_held after the 20s settle and re-forces if slipped, (2) runs hero_storm_rgb on the Play PNG and if daylightish does one storm+5s+reshoot pass. Headless: test_hero_storm_rgb.py + updated test_storm_pin.py. No Unreal touched; storm Play reshoot still owed on next editor grant.

## Round-3 editor turn: storm Play hero (Oct 12, 2026, 23:01 PT)

CLAIM after pythagoras HANDOFF. Bridge died once mid-Play (washed lum~220 false OK); retried as 3c: editor director seeded oddsreaper_storm @ 18.75, PIE force held STORM, Play viewport hero_unreal_play.png mean RGB ~76/65/47 lum~66 stormish. MoodVolume count was 0 (director path). Play stopped; OddsReaperIsland + DaedalusWorld saved; HANDOFF art-master-flex. daylightish_rgb now also rejects lum>140 washed sky.

## Round-3 follow-up: MoodVolume count 0 (Oct 12, 2026, 23:10 PT)

The 23:01 turn held storm only via the director path (volumes=0). Off-editor diagnosis: the PIE streaming flip (should_be_loaded/visible) only lands on a later streaming update, so the same-tick volume search saw nothing; PIE copies may also miss the editor actor label. STORM_CODE now calls GameplayStatics.flush_level_streaming before the search and falls back to matching any DaedalusMoodVolume whose mood row is oddsreaper_storm; result logs volumes_all / vmatch / flushed. test_storm_pin.py extended, ALL PASS. No Unreal touched.

## OR_NEXT (next editor grant)

Storm MoodVolume path is fixed off-editor (flush_level_streaming + mood=oddsreaper_storm fallback; commit ef0d9c69). On the next OddsReaper editor turn:

1. Verify Play hero still gates green: bot-team/shots/oddsreaper/hero_unreal_play.png must stay stormish (round-3c was mean RGB ~76/65/47 lum~66). If daylightish_rgb / lum>140, re-force storm in PIE, settle, re-shot.
2. Confirm MoodVolume path now finds volumes after flush (log volumes_all / vmatch / flushed); director fallback is fine but volume pin is preferred.
3. Do not force storm at BeginPlay on the shared DaedalusWorld. HANDOFF via OR_NEXT when done.

## Round-4 off-editor: full mood CSV sync gate (Oct 12, 2026, 23:40 PT)

mood.json now mirrors every column of the wild_biomes_moods.csv oddsreaper_storm row (added FogHeightFalloff 0.4 + FogStartDistance 0). test_mood_row.py parses SunColor/SkyColor/FogColor and asserts all scalars + mpc_storm + pie_hour 18.75 — the data-table half of the daylight-hero diagnosis. No Unreal touched.
