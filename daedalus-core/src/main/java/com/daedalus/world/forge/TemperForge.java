// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ForgeGrades.Material;
import com.daedalus.world.forge.ForgeGrades.Weapon;
import com.daedalus.world.forge.ForgeGrades.WeaponGrade;

import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Anvil and Quench (contest gap G19): the smithing timing minigame of Hephaestus Island's Great Forge.
 * It turns a smith's play into the temper score (0..100) that {@link ForgeGrades} reads.
 *
 * <p>One blank, three moments, all on one clock (milliseconds since the blank went into the forge):
 * <ol>
 *   <li><b>Heat.</b> The blank warms at its material's rate. Pull it when it glows in the target band.</li>
 *   <li><b>Hammer.</b> The anvil beat starts {@link #FIRST_BEAT_MS} after the pull. Strike on each beat:
 *       PERFECT and GOOD windows narrow for harder metals. The blank cools while worked; a strike below the
 *       workable heat cracks it, and strikes after the quench are wasted.</li>
 *   <li><b>Quench.</b> Dip at the quench heat, which falls about one beat after the last strike, into
 *       MAGMA (strength), SPRING (duration) or DUAL (both, with half the window), the island's Forge
 *       Temper paths.</li>
 * </ol>
 * The island rule: "Heat alone breaks. Water alone softens. Temper both." Temper weights heat 30 %,
 * hammer 45 % and quench 25 %. A cracked blank tops out at {@link #CRACKED_CAP}. A DUAL quench at
 * temper {@link #ARK_PLATE_TEMPER}+ stamps an ark plate (quest q_forge_temper).
 *
 * <p>{@link #judge} is a pure function of the blank and the run, so the host can replay any submitted
 * run exactly. All scores are integer per-mille.
 */
public final class TemperForge {

    public static final int AMBIENT_C = 20;
    public static final int FIRST_BEAT_MS = 1000;
    /** Cooling while the blank is out of the forge, degrees C per second. */
    public static final int COOL_C_PER_S = 25;
    public static final int CRACKED_CAP = 30;
    public static final int ARK_PLATE_TEMPER = 60;
    /** Each strike past the beat count costs this much of the hammer score (overworking). */
    public static final int OVERWORK_PM = 100;

    /** The quench paths of Forge Temper. */
    public enum Quench {
        MAGMA, SPRING, DUAL;

        int band(int base) {
            return this == DUAL ? base / 2 : base;
        }
    }

    /** How one strike landed. */
    public enum Strike { PERFECT, GOOD, MISS, CRACK, WASTED }

    /** A metal's forging numbers. */
    public record Metal(Material material, int targetC, int bandC, int heatRateCPerS, int perfectMs, int goodMs) {
    }

    /** One blank on the anvil: its metal and the seeded beat. */
    public record Blank(Metal metal, int strikes, int beatMs) {

        /** Heat in the forge after {@code ms}, capped at burning point (target + 300). */
        public int heatAt(int ms) {
            return Math.min(metal.targetC() + 300, AMBIENT_C + (int) ((long) metal.heatRateCPerS() * ms / 1000));
        }

        /** When the {@code i}-th beat falls, counted from the pull. */
        public int beatOffset(int i) {
            return FIRST_BEAT_MS + i * beatMs;
        }

        /** The heat to quench at: what the ideal pull has cooled to one beat after the last strike. */
        public int quenchTargetC() {
            return metal.targetC() - (int) ((long) COOL_C_PER_S * beatOffset(strikes) / 1000);
        }

        /** Below this a strike cracks the blank. */
        public int workableC() {
            return metal.targetC() - 250;
        }

        /** The earliest pull in the target band's centre. */
        public int idealPullMs() {
            return (int) Math.ceilDiv((long) (metal.targetC() - AMBIENT_C) * 1000, metal.heatRateCPerS());
        }
    }

    /** What the smith did: when the blank came out, each strike, when and where it was quenched. */
    public record Run(int pullMs, List<Integer> strikesMs, int quenchMs, Quench quench) {

        public Run {
            strikesMs = List.copyOf(strikesMs);
        }
    }

    /** The judged run. */
    public record Result(int heatPm, int hammerPm, int quenchPm, List<Strike> strikes, boolean cracked, int temper,
                         String tier, Quench quench, boolean arkPlate) {

        public Result {
            strikes = List.copyOf(strikes);
        }

        /** TFG 1 single-line encoding, stable for the C++ parity test and the link. */
        public String encode() {
            StringBuilder s = new StringBuilder();
            for (Strike k : strikes) {
                s.append("PGMCW".charAt(k.ordinal()));
            }
            return String.format(java.util.Locale.ROOT, "TFG 1 %s heat=%d hammer=%d quench=%d t=%d tier=%s cracked=%d ark=%d strikes=%s",
                    quench, heatPm, hammerPm, quenchPm, temper, tier, cracked ? 1 : 0, arkPlate ? 1 : 0,
                    s.length() == 0 ? "-" : s);
        }

        /** The weapon sheet this temper gives, through Forge Weapon Grades. */
        public WeaponGrade grade(Weapon weapon, Material material) {
            return ForgeGrades.grade(weapon, material, temper);
        }
    }

    private TemperForge() {
    }

    /** True for the metals the Great Forge works (wood, stone and obsidian are shaped, not tempered). */
    public static boolean forgeable(Material m) {
        return switch (m) {
            case COPPER, BRONZE, IRON, STEEL, STARMETAL -> true;
            default -> false;
        };
    }

    /** The forging numbers of {@code m}: harder metals run hotter, heat slower and judge tighter. */
    public static Metal metal(Material m) {
        return switch (m) {
            case COPPER -> new Metal(m, 700, 45, 140, 80, 170);
            case BRONZE -> new Metal(m, 760, 40, 130, 75, 160);
            case IRON -> new Metal(m, 850, 40, 120, 70, 150);
            case STEEL -> new Metal(m, 900, 35, 110, 60, 135);
            case STARMETAL -> new Metal(m, 1100, 25, 100, 45, 110);
            default -> throw new IllegalArgumentException(m + " is not tempered at the Great Forge");
        };
    }

    /** The blank the forge hands out for {@code material} and {@code seed}: 5..8 strikes at 520..780 ms. */
    public static Blank blank(Material material, long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xF0E6EL);
        return new Blank(metal(material), 5 + rng.nextInt(4), 520 + 20 * rng.nextInt(14));
    }

    /** Heat score: full marks in band, ten per-mille lost per degree outside it. */
    static int heatScore(Blank b, int heatC) {
        int off = Math.abs(heatC - b.metal().targetC()) - b.metal().bandC();
        return Math.max(0, 1000 - 10 * Math.max(0, off));
    }

    /** Judge a run. Pure: the same blank and run always give the same result. */
    public static Result judge(Blank b, Run run) {
        if (run.pullMs() < 0 || run.quenchMs() < run.pullMs()) {
            throw new IllegalArgumentException("pull must come first, then the quench");
        }
        int pulledC = b.heatAt(run.pullMs());
        int heat = heatScore(b, pulledC);

        List<Strike> strikes = new ArrayList<>();
        boolean cracked = false;
        long hammer = 0;
        int last = run.pullMs();
        for (int i = 0; i < run.strikesMs().size(); i++) {
            int at = run.strikesMs().get(i);
            if (at < last) {
                throw new IllegalArgumentException("strikes must be in time order");
            }
            last = at;
            Strike s;
            if (at > run.quenchMs()) {
                s = Strike.WASTED;
            } else if (i >= b.strikes()) {
                s = Strike.MISS;
                hammer -= OVERWORK_PM;
            } else if (cooled(pulledC, run.pullMs(), at) < b.workableC()) {
                s = Strike.CRACK;
                cracked = true;
            } else {
                int dt = Math.abs(at - (run.pullMs() + b.beatOffset(i)));
                s = dt <= b.metal().perfectMs() ? Strike.PERFECT : dt <= b.metal().goodMs() ? Strike.GOOD : Strike.MISS;
                hammer += s == Strike.PERFECT ? 1000 : s == Strike.GOOD ? 600 : 0;
            }
            strikes.add(s);
        }
        int hammerPm = (int) Math.max(0, Math.min(1000, hammer / b.strikes()));

        int quenchedC = cooled(pulledC, run.pullMs(), run.quenchMs());
        int qoff = Math.abs(quenchedC - b.quenchTargetC()) - run.quench().band(30);
        int quench = Math.max(0, 1000 - 8 * Math.max(0, qoff));

        long total = 300L * heat + 450L * hammerPm + 250L * quench;     // per-mille x 1000
        int temper = (int) (total / 10_000);
        if (cracked) {
            temper = Math.min(temper, CRACKED_CAP);
        }
        boolean ark = run.quench() == Quench.DUAL && !cracked && temper >= ARK_PLATE_TEMPER;
        return new Result(heat, hammerPm, quench, strikes, cracked, temper, ForgeGrades.tier(temper), run.quench(), ark);
    }

    /** Heat of a blank pulled at {@code pulledC} at {@code pullMs}, by {@code ms}. */
    static int cooled(int pulledC, int pullMs, int ms) {
        return pulledC - (int) ((long) COOL_C_PER_S * (ms - pullMs) / 1000);
    }

    /** The master smith's run: pull at the ideal, strike every beat dead on, quench on target. */
    public static Run idealRun(Blank b, Quench q) {
        int pull = b.idealPullMs();
        List<Integer> strikes = new ArrayList<>();
        for (int i = 0; i < b.strikes(); i++) {
            strikes.add(pull + b.beatOffset(i));
        }
        int pulledC = b.heatAt(pull);
        // Quench where the cooled heat meets the quench target, never before the last strike.
        int quench = pull + Math.max(b.beatOffset(b.strikes() - 1),
                (pulledC - b.quenchTargetC()) * 1000 / COOL_C_PER_S);
        return new Run(pull, strikes, quench, q);
    }
}
