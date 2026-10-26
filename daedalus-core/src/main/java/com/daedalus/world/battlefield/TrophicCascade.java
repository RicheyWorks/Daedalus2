// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Trophic Cascade (contest G58): bring the ark's wolves home and let the river valley heal.
 *
 * <p>A valley of {@code reaches} river reaches holds elk, maybe wolves, riverside willow and maybe beaver colonies.
 * Each year runs in this order:
 * <ul>
 *   <li>Elk grow logistically (rate {@code elkRate}, carrying capacity {@code elkCap}). A seeded winter changes the rate by
 *       up to ±{@code winterNoise}.</li>
 *   <li>Wolves kill elk with a Holling type II response, a·E / (1 + a·h·E) kills per wolf. They grow by
 *       {@code conversion} wolves per elk killed and lose {@code wolfMortality} of the pack each year, up to
 *       {@code wolfCap} by territory. A pack below 1 wolf is gone.</li>
 *   <li>Hunters remove up to {@code cull} elk a year.</li>
 *   <li>Elk browse riverside willow. The pressure on each reach is E·{@code browse}/reaches, divided by
 *       (1 + {@code fear}·W): elk that fear wolves do not linger on the open banks (the landscape of fear). A fenced
 *       reach is not browsed.</li>
 *   <li>Willow grows logistically ({@code willowGrowth}), plus {@code sprout} a year from seed, plus
 *       {@code beaverWater} where a colony keeps the water up. A colony eats {@code beaverEat} a year and leaves a reach
 *       whose willow falls below {@code beaverLeave}. Each year one new colony settles on the first reach at or above
 *       {@code beaverSettle}, up to {@code maxColonies}.</li>
 * </ul>
 *
 * <p>Outcomes are checked in this order:
 * <ul>
 *   <li>CRASHED: the elk fall below {@code elkFloor}, or released wolves die out.</li>
 *   <li>CASCADE: mean willow is at least {@code cascadeWillow} and at least one beaver colony lives.</li>
 *   <li>PARTIAL: some reach is at least {@code beaverSettle}.</li>
 *   <li>BROWSED: anything else.</li>
 * </ul>
 * The numbers show that culling elk to the same head count as the wolves leave does not save the willow. The
 * fear is what does.
 */
public final class TrophicCascade {

    /** What the valley became. */
    public enum Outcome { CASCADE, PARTIAL, BROWSED, CRASHED }

    /**
     * Valley tuning.
     *
     * @param years         seasons to run
     * @param reaches       river reaches
     * @param elkStart      elk at the start
     * @param elkCap        elk carrying capacity
     * @param elkRate       elk logistic growth rate
     * @param winterNoise   ± fraction of {@code elkRate} a seeded winter adds or removes
     * @param attack        wolf attack rate a
     * @param handling      wolf handling time h (years per elk)
     * @param conversion    wolves gained per elk killed
     * @param wolfMortality yearly fraction of wolves lost
     * @param wolfCap       most wolves the valley's territory holds
     * @param browse        willow browse per elk (spread over all reaches)
     * @param fear          how much each wolf scares elk off the banks
     * @param willowStart   willow cover at the start (0..1)
     * @param willowGrowth  willow logistic growth rate
     * @param sprout        willow cover a year from seed
     * @param beaverWater   extra willow growth on a reach with a colony
     * @param beaverEat     willow a colony eats a year
     * @param beaverSettle  willow cover a reach needs before beavers settle
     * @param beaverLeave   willow cover below which a colony leaves
     * @param maxColonies   most beaver colonies
     * @param elkFloor      fewer elk than this at the end is a crash
     * @param cascadeWillow mean willow needed for a cascade
     * @param packs         wolves the ark can release in total
     * @param fences        reaches the player can fence
     */
    public record Settings(int years, int reaches, double elkStart, double elkCap, double elkRate, double winterNoise,
            double attack, double handling, double conversion, double wolfMortality, double wolfCap, double browse,
            double fear, double willowStart, double willowGrowth, double sprout, double beaverWater, double beaverEat,
            double beaverSettle, double beaverLeave, int maxColonies, double elkFloor, double cascadeWillow,
            int packs, int fences) {

        /** The default valley. */
        public static final Settings DEFAULT = new Settings(30, 10, 700, 800, 0.3, 0.3, 0.02, 0.05, 0.05, 0.35, 30,
                0.0015, 0.3, 0.15, 0.35, 0.02, 0.05, 0.03, 0.6, 0.2, 4, 50, 0.6, 12, 3);

        /** Rejects a valley that cannot run. */
        public Settings {
            if (years < 1 || reaches < 1 || !(elkStart >= 0) || !(elkCap > 0) || !(elkRate >= 0)
                    || !(winterNoise >= 0 && winterNoise <= 1) || !(attack >= 0) || !(handling >= 0)
                    || !(conversion >= 0) || !(wolfMortality >= 0 && wolfMortality <= 1) || !(wolfCap >= 0)
                    || !(browse >= 0) || !(fear >= 0) || !(willowStart >= 0 && willowStart <= 1)
                    || !(willowGrowth >= 0) || !(sprout >= 0) || !(beaverWater >= 0) || !(beaverEat >= 0)
                    || !(beaverSettle >= 0 && beaverSettle <= 1) || !(beaverLeave >= 0 && beaverLeave <= beaverSettle)
                    || maxColonies < 0 || !(elkFloor >= 0) || !(cascadeWillow >= 0 && cascadeWillow <= 1)
                    || packs < 0 || fences < 0 || fences > reaches) {
                throw new IllegalArgumentException("bad trophic cascade settings");
            }
        }
    }

    /** One year's end state. */
    public record Year(int index, double elk, double wolves, double kills, double culled, double meanWillow,
            int colonies) {}

    /**
     * The run's result.
     *
     * @param outcome  what the valley became
     * @param elk      elk at the end
     * @param wolves   wolves at the end
     * @param willow   willow cover per reach at the end
     * @param beaver   whether each reach holds a colony at the end
     * @param years    one row per year
     */
    public record Report(Outcome outcome, double elk, double wolves, List<Double> willow, List<Boolean> beaver,
            List<Year> years) {

        /** Defensive copies. */
        public Report {
            willow = List.copyOf(willow);
            beaver = List.copyOf(beaver);
            years = List.copyOf(years);
        }

        /** Mean willow cover at the end. */
        public double meanWillow() {
            return willow.stream().mapToDouble(Double::doubleValue).average().orElse(0);
        }

        /** Beaver colonies at the end. */
        public int colonies() {
            return (int) beaver.stream().filter(Boolean::booleanValue).count();
        }

        /**
         * The reach as a BattlefieldEcology band: WETLAND under a colony, SCRUB for willow thicket at or above 0.5,
         * MEADOW for some cover, BARE for browsed-out banks.
         */
        public Vegetation band(int reach) {
            if (beaver.get(reach)) {
                return Vegetation.WETLAND;
            }
            double w = willow.get(reach);
            return w >= 0.5 ? Vegetation.SCRUB : w >= 0.2 ? Vegetation.MEADOW : Vegetation.BARE;
        }
    }

    private final Settings s;
    private final long seed;
    private final int[] release;
    private final boolean[] fenced;
    private int released;
    private int fencesUsed;
    private double cull;

    private TrophicCascade(Settings s, long seed) {
        this.s = s;
        this.seed = seed;
        this.release = new int[s.years()];
        this.fenced = new boolean[s.reaches()];
    }

    /** A valley with these settings and this seed for the winters. */
    public static TrophicCascade valley(Settings settings, long seed) {
        if (settings == null) {
            throw new IllegalArgumentException("settings");
        }
        return new TrophicCascade(settings, seed);
    }

    /** Release {@code n} ark wolves at the start of {@code year}. Returns false if the year or the budget is wrong. */
    public boolean release(int year, int n) {
        if (year < 0 || year >= s.years() || n < 1 || released + n > s.packs()) {
            return false;
        }
        release[year] += n;
        released += n;
        return true;
    }

    /** Fence one reach against browsing. Returns false if it is out of range, already fenced or over budget. */
    public boolean fence(int reach) {
        if (reach < 0 || reach >= s.reaches() || fenced[reach] || fencesUsed >= s.fences()) {
            return false;
        }
        fenced[reach] = true;
        fencesUsed++;
        return true;
    }

    /** Hunters take up to {@code elkPerYear} elk every year. Returns false for a negative or non-finite cull. */
    public boolean cull(double elkPerYear) {
        if (!(elkPerYear >= 0) || Double.isInfinite(elkPerYear)) {
            return false;
        }
        cull = elkPerYear;
        return true;
    }

    /** Wolves still in the ark. */
    public int wolvesLeft() {
        return s.packs() - released;
    }

    /** Fences still unbuilt. */
    public int fencesLeft() {
        return s.fences() - fencesUsed;
    }

    /** Runs the valley. Deterministic in the settings, the seed and the plan. */
    public Report run() {
        SplittableRandom rng = new SplittableRandom(seed);
        int n = s.reaches();
        double elk = s.elkStart();
        double wolves = 0;
        double[] willow = new double[n];
        Arrays.fill(willow, s.willowStart());
        boolean[] beaver = new boolean[n];
        List<Year> log = new ArrayList<>();
        for (int y = 0; y < s.years(); y++) {
            wolves += release[y];
            double rate = s.elkRate() * (1 + s.winterNoise() * (2 * rng.nextDouble() - 1));
            double perWolf = s.attack() * elk / (1 + s.attack() * s.handling() * elk);
            double kills = Math.min(elk, wolves * perWolf);
            double grown = elk + rate * elk * (1 - elk / s.elkCap()) - kills;
            double culled = Math.min(cull, Math.max(0, grown));
            elk = Math.max(0, grown - culled);
            wolves = Math.min(s.wolfCap(), Math.max(0, wolves + s.conversion() * kills - s.wolfMortality() * wolves));
            if (wolves < 1) {
                wolves = 0;
            }
            double pressure = elk * s.browse() / n / (1 + s.fear() * wolves);
            for (int i = 0; i < n; i++) {
                double w = willow[i];
                double grow = s.willowGrowth() * w * (1 - w) + s.sprout() + (beaver[i] ? s.beaverWater() : 0);
                double eaten = (fenced[i] ? 0 : pressure) + (beaver[i] ? s.beaverEat() : 0);
                willow[i] = Math.min(1, Math.max(0, w + grow - eaten));
                if (beaver[i] && willow[i] < s.beaverLeave()) {
                    beaver[i] = false;
                }
            }
            int colonies = count(beaver);
            if (colonies < s.maxColonies()) {
                for (int i = 0; i < n; i++) {
                    if (!beaver[i] && willow[i] >= s.beaverSettle()) {
                        beaver[i] = true;
                        colonies++;
                        break;
                    }
                }
            }
            log.add(new Year(y, elk, wolves, kills, culled, mean(willow), colonies));
        }
        List<Double> w = new ArrayList<>();
        List<Boolean> b = new ArrayList<>();
        boolean anyThicket = false;
        for (int i = 0; i < n; i++) {
            w.add(willow[i]);
            b.add(beaver[i]);
            anyThicket |= willow[i] >= s.beaverSettle();
        }
        Outcome outcome;
        if (elk < s.elkFloor() || (released > 0 && wolves == 0)) {
            outcome = Outcome.CRASHED;
        } else if (mean(willow) >= s.cascadeWillow() && count(beaver) > 0) {
            outcome = Outcome.CASCADE;
        } else if (anyThicket) {
            outcome = Outcome.PARTIAL;
        } else {
            outcome = Outcome.BROWSED;
        }
        return new Report(outcome, elk, wolves, w, b, log);
    }

    private static int count(boolean[] a) {
        int c = 0;
        for (boolean x : a) {
            if (x) {
                c++;
            }
        }
        return c;
    }

    private static double mean(double[] a) {
        double t = 0;
        for (double x : a) {
            t += x;
        }
        return t / a.length;
    }
}
