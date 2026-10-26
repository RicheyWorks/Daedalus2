// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Soot Moths (contest G103): the forge islands' smoke darkens the bark, and the birds choose which moths live
 * (industrial melanism, natural selection you can watch).
 *
 * <p>A moth population of {@code population} adults carries a dark allele D (dominant) at frequency q. Moths mate at
 * random (Hardy-Weinberg), so the dark morph share is 1 − (1 − q)². Each year:
 * <ul>
 *   <li>The forge burns at the level set for that decade (0..1). Soot on the bark rises by
 *       {@code sootPerLevel}·level·(1 − filter share) and washes off at {@code washOff} a year. Bark darkness is the
 *       soot, 0..1.</li>
 *   <li>Birds take {@code predation} of the moths that show against the bark: a dark moth with chance
 *       {@code predation}·(1 − bark), a pale moth with chance {@code predation}·bark.</li>
 *   <li>The survivors' genes make the next generation. q' comes from genotype fitness, and the seeded sampling of
 *       2N gene copies adds genetic drift.</li>
 * </ul>
 *
 * <p>The forge must make {@code forgeGoal} level-years of iron. The keeper can fit up to {@code maxFilters} smoke
 * filters, each removing {@code filterShare} of the soot. Outcomes:
 * <ul>
 *   <li>MORPH_LOST: an allele is lost (q reaches 0 or 1).</li>
 *   <li>RESTORED: at least {@code paleGoal} of the moths are pale at the end and the forge met its goal.</li>
 *   <li>DARKENED: anything else.</li>
 * </ul>
 */
public final class SootMoths {

    /** How the moths came through. */
    public enum Outcome { RESTORED, DARKENED, MORPH_LOST }

    /**
     * Tuning.
     *
     * @param years        years to run
     * @param population   adult moths
     * @param startDark    starting dark allele frequency q
     * @param startSoot    starting bark darkness 0..1
     * @param sootPerLevel soot a full-burning forge adds a year
     * @param washOff      fraction of soot rain washes off a year
     * @param predation    share of visible moths the birds take
     * @param filterShare  soot each filter removes (shares add, capped at 1)
     * @param maxFilters   most filters the keeper can fit
     * @param forgeGoal    forge level-years the island needs
     * @param paleGoal     pale share needed at the end
     */
    public record Settings(int years, int population, double startDark, double startSoot, double sootPerLevel,
            double washOff, double predation, double filterShare, int maxFilters, double forgeGoal,
            double paleGoal) {

        /** The forge islands after a century of smoke: dark moths everywhere. */
        public static final Settings DEFAULT = new Settings(40, 500, 0.6, 0.8, 0.2, 0.2, 0.2, 0.25, 3, 24, 0.5);

        /** Rejects tuning that cannot run. */
        public Settings {
            if (years < 1 || population < 1 || !(startDark >= 0 && startDark <= 1)
                    || !(startSoot >= 0 && startSoot <= 1) || !(sootPerLevel >= 0) || !(washOff >= 0 && washOff <= 1)
                    || !(predation >= 0 && predation <= 1) || !(filterShare >= 0 && filterShare <= 1)
                    || maxFilters < 0 || !(forgeGoal >= 0) || !(paleGoal >= 0 && paleGoal <= 1)) {
                throw new IllegalArgumentException("bad soot moth settings");
            }
        }
    }

    /** One year. */
    public record Year(int index, double forge, double bark, double darkAllele, double darkShare, double eaten) {}

    /** The result. */
    public record Report(Outcome outcome, double darkAllele, double paleShare, double forgeMade, List<Year> years) {

        /** Defensive copy. */
        public Report {
            years = List.copyOf(years);
        }

        /** Bark as a band: soot-black trunks read as BARE (no lichen), clean bark as OAK woodland. */
        public Vegetation bark() {
            double b = years.isEmpty() ? 0 : years.get(years.size() - 1).bark();
            return b >= 0.5 ? Vegetation.BARE : b >= 0.2 ? Vegetation.SCRUB : Vegetation.OAK;
        }
    }

    private final Settings s;
    private final long seed;
    private final double[] forge;
    private int filters;

    private SootMoths(Settings s, long seed) {
        this.s = s;
        this.seed = seed;
        forge = new double[(s.years() + 9) / 10];
        Arrays.fill(forge, 1.0);
    }

    /** A seeded population. The forge starts at full burn every decade. */
    public static SootMoths population(Settings settings, long seed) {
        if (settings == null) {
            throw new IllegalArgumentException("settings");
        }
        return new SootMoths(settings, seed);
    }

    /** Set the forge level (0..1) for one decade. False out of range. */
    public boolean forge(int decade, double level) {
        if (decade < 0 || decade >= forge.length || !(level >= 0 && level <= 1)) {
            return false;
        }
        forge[decade] = level;
        return true;
    }

    /** Fit one more smoke filter. False over the budget. */
    public boolean filter() {
        if (filters >= s.maxFilters()) {
            return false;
        }
        filters++;
        return true;
    }

    /** Runs the years. Deterministic in the settings, the seed and the plan. */
    public Report run() {
        SplittableRandom rng = new SplittableRandom(seed);
        double q = s.startDark();
        double bark = s.startSoot();
        double clean = Math.min(1, filters * s.filterShare());
        double made = 0;
        List<Year> log = new ArrayList<>();
        boolean fixed = q <= 0 || q >= 1;
        for (int y = 0; y < s.years(); y++) {
            double level = forge[y / 10];
            made += level;
            bark = Math.min(1, Math.max(0, bark * (1 - s.washOff()) + s.sootPerLevel() * level * (1 - clean)));
            double wDark = 1 - s.predation() * (1 - bark);
            double wPale = 1 - s.predation() * bark;
            double p = 1 - q;
            double dd = q * q;
            double dp = 2 * p * q;
            double pp = p * p;
            double mean = (dd + dp) * wDark + pp * wPale;
            double eaten = 1 - mean;
            double expected = mean <= 0 ? q : (dd * wDark + 0.5 * dp * wDark) / mean;
            int copies = 2 * s.population();
            int dark = 0;
            for (int c = 0; c < copies; c++) {
                if (rng.nextDouble() < expected) {
                    dark++;
                }
            }
            q = (double) dark / copies;
            fixed = dark == 0 || dark == copies;
            log.add(new Year(y, level, bark, q, 1 - (1 - q) * (1 - q), eaten));
        }
        double pale = (1 - q) * (1 - q);
        Outcome outcome = fixed ? Outcome.MORPH_LOST
                : pale >= s.paleGoal() && made >= s.forgeGoal() ? Outcome.RESTORED : Outcome.DARKENED;
        return new Report(outcome, q, pale, made, log);
    }
}
