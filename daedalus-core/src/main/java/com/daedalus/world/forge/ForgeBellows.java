// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ForgeGrades.Material;
import com.daedalus.world.forge.TemperForge.Metal;

import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Bellows Shift (contest gap G57): keep the Great Forge's firebed in a metal's working band for one bellows shift.
 * This is the bellows of ISLAND.md's Caldera Forge ("Great Forge, anvil ring, bellows (forgeox), quench tub").
 *
 * <p>A shift is {@value #TICKS} ticks of {@value #TICK_MS} ms. Every tick the firebed loses {@code (heat - 20) / 40}
 * degrees (never below the 20-degree ambient). A seeded caldera draught gusts on about one tick in twelve and takes another {@value #GUST_C}. A pump on
 * a tick adds {@value #PUMP_C} degrees, plus 15% for each working forgeox (livestock.json {@code forgeox_bellows}:
 * two head, +15% each, watered and fed at Prop_ForgeBellows_Basalt). The band is the G19 metal's own
 * {@code targetC ± bandC}. If you spam the bellows past {@code targetC + 3 × bandC}, the bed throws a cinder: you
 * lose one of {@value #COAL} coal and 120 degrees. With the last coal gone, the fire is out for the rest of the shift.
 *
 * <p>Pure and deterministic: {@link #plan} gives the same draught for the same seed, and {@link #run} the same
 * {@link Result} for the same pumps. The host owns the plan and judges the pump inputs it receives.
 */
public final class ForgeBellows {

    public static final int TICKS = 120;
    public static final int TICK_MS = 250;
    public static final int START_C = 600;
    public static final int PUMP_C = 30;
    public static final int GUST_C = 30;
    public static final int COAL = 3;
    public static final int CINDER_DROP_C = 120;
    public static final int OX_BONUS_PCT = 15;
    public static final int MAX_OXEN = 2;
    /** Out of band by more than this many bands throws a cinder. */
    public static final int CINDER_BANDS = 3;

    /** How steady the bed was held. */
    public enum Tier { STEADY, WARM, FITFUL, COLD }

    /** One shift at the bellows: the metal, the working oxen and the seeded draught. */
    public record Plan(Metal metal, int oxen, List<Boolean> gusts) {

        public Plan {
            if (oxen < 0 || oxen > MAX_OXEN) {
                throw new IllegalArgumentException("the bellows take 0.." + MAX_OXEN + " forgeox, not " + oxen);
            }
            gusts = List.copyOf(gusts);
        }

        /** Degrees one pump adds with this many oxen on the bellows. */
        public int pumpC() {
            return PUMP_C * (100 + OX_BONUS_PCT * oxen) / 100;
        }
    }

    /** What the shift did. */
    public record Result(int inBandTicks, int inBandPm, int cinders, boolean doused, int peakC, int finalC, Tier tier,
                         boolean readyToPull, int forgeSpeedPm, String line) {

        /** One-line BLW 1 summary, the same text as Encode() in DaedalusForgeBellowsCore.h. */
        public String encode() {
            return "BLW 1 in=" + inBandTicks + " pm=" + inBandPm + " cinders=" + cinders + " doused=" + (doused ? 1 : 0)
                    + " peak=" + peakC + " final=" + finalC + " " + tier + " ready=" + (readyToPull ? 1 : 0) + " speed="
                    + forgeSpeedPm + " | " + line;
        }
    }

    private ForgeBellows() {
    }

    /** The shift for {@code material} with {@code oxen} working forgeox; the draught comes from {@code seed}. */
    public static Plan plan(Material material, int oxen, long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xBE11L);
        List<Boolean> gusts = new ArrayList<>(TICKS);
        for (int t = 0; t < TICKS; t++) {
            gusts.add(rng.nextInt(12) == 0);
        }
        return new Plan(TemperForge.metal(material), oxen, gusts);
    }

    /** Play {@code pumps} (one flag per tick; missing ticks are no pump) against the plan. */
    public static Result run(Plan p, List<Boolean> pumps) {
        int target = p.metal().targetC();
        int band = p.metal().bandC();
        int heat = START_C;
        int coal = COAL;
        int in = 0;
        int cinders = 0;
        int peak = heat;
        boolean out = false;
        for (int t = 0; t < TICKS; t++) {
            boolean pump = !out && t < pumps.size() && pumps.get(t);
            heat = step(p, t, heat, pump);
            if (out) {
                heat = Math.max(20, heat - 40);
            } else if (heat > target + CINDER_BANDS * band) {
                cinders++;
                coal--;
                heat -= CINDER_DROP_C;
                out = coal == 0;
            }
            peak = Math.max(peak, heat);
            if (Math.abs(heat - target) <= band) {
                in++;
            }
        }
        int pm = in * 1000 / TICKS;
        Tier tier = pm >= 850 ? Tier.STEADY : pm >= 600 ? Tier.WARM : pm >= 300 ? Tier.FITFUL : Tier.COLD;
        return new Result(in, pm, cinders, out, peak, heat, tier, !out && Math.abs(heat - target) <= band,
                1000 + 10 * OX_BONUS_PCT * p.oxen(), line(tier, out, p.oxen()));
    }

    /** One tick of the firebed: pump, draught, then the bed's own loss. */
    static int step(Plan p, int t, int heat, boolean pump) {
        int h = heat + (pump ? p.pumpC() : 0) - (p.gusts().get(t) ? GUST_C : 0);
        return Math.max(20, h - (h - 20) / 40);
    }

    /** The bellows master's shift: pump on a tick only when the bed would otherwise fall below target. */
    public static List<Boolean> steadyHand(Plan p) {
        List<Boolean> pumps = new ArrayList<>(TICKS);
        int heat = START_C;
        for (int t = 0; t < TICKS; t++) {
            boolean pump = step(p, t, heat, false) < p.metal().targetC();
            pumps.add(pump);
            heat = step(p, t, heat, pump);
        }
        return pumps;
    }

    /** What Drydock Master Brannoc Slagg says at the shift bell. */
    static String line(Tier tier, boolean doused, int oxen) {
        if (doused) {
            return "You choked her on cinders. Rake the bed, fetch coal, and pump like you mean it, not like you're angry.";
        }
        return switch (tier) {
            case STEADY -> "Steady as the caldera. Pull the blank, it's ready.";
            case WARM -> "Warm enough to work. Keep the rhythm and the blank will forgive you.";
            case FITFUL -> oxen == 0 ? "Forgeox on the bellows buys you time. Don't waste it." : "Fits and starts. Watch the colour, not your arm.";
            case COLD -> oxen == 0 ? "Forgeox on the bellows buys you time. Don't waste it." : "Cold bed, cold iron. Again.";
        };
    }
}
