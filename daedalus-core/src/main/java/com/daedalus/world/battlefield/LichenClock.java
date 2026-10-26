// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Lichen Clock (contest G91): date the shattering's rockfalls by the lichens growing on them (lichenometry).
 *
 * <p>After the planet shattered, aftershocks kept dropping boulder fields onto the fragments. A fresh rock face is bare;
 * map lichen ({@code Rhizocarpon}) colonizes it after a lag, grows fast for a while (the great growth phase), then
 * slowly. The largest lichen on a boulder field dates the fall.
 *
 * <p>A seeded field has {@code events} rockfalls, each between {@code minAge} and {@code maxAge} years ago, with
 * {@code boulders} boulders each. Every boulder carries {@code thalli} lichens. Each thallus colonized at the fall plus
 * the base lag plus a seeded exponential delay (mean {@code delayMean}), so most lichens are younger than their rock.
 * Its diameter follows the growth curve with a little seeded noise:
 * <ul>
 *   <li>0 before colonization;</li>
 *   <li>{@code fastRate} mm/yr for the first {@code fastYears} years;</li>
 *   <li>{@code slowRate} mm/yr after that.</li>
 * </ul>
 *
 * <p>The player has {@code budget} measurements. Measuring {@code n} thalli on a boulder costs {@code n} and returns the
 * largest of them. {@link #age(double)} inverts the curve (plus the base lag). The player then dates each event. An
 * event is dated when the guess is within {@code tolerance} years.
 *
 * <p>Outcomes:
 * <ul>
 *   <li>DATED: every event is within tolerance and the order is right.</li>
 *   <li>ORDERED: the order is right but some date is off.</li>
 *   <li>MUDDLED: anything else.</li>
 * </ul>
 * Sampling more thalli brings the largest lichen closer to the first colonist, so the estimate gets closer to the truth.
 * Sampling a few thalli makes every rockfall look younger than it is.
 */
public final class LichenClock {

    /** How the dating went. */
    public enum Outcome { DATED, ORDERED, MUDDLED }

    /**
     * Field tuning.
     *
     * @param events    rockfall events
     * @param boulders  boulders per event
     * @param thalli    lichens per boulder
     * @param minAge    youngest possible event, years
     * @param maxAge    oldest possible event, years
     * @param lag       years before any lichen can colonize fresh rock
     * @param delayMean mean extra colonization delay per thallus, years
     * @param fastRate  great growth phase rate, mm/yr
     * @param fastYears length of the great growth phase, years
     * @param slowRate  later growth rate, mm/yr
     * @param noise     ± mm of seeded measurement and growth noise
     * @param budget    thalli the player may measure in total
     * @param tolerance years a guess may be off and still date the event
     */
    public record Settings(int events, int boulders, int thalli, int minAge, int maxAge, double lag,
            double delayMean, double fastRate, double fastYears, double slowRate, double noise, int budget,
            double tolerance) {

        /** The default field. */
        public static final Settings DEFAULT = new Settings(4, 2, 30, 30, 220, 8, 25, 0.6, 50, 0.3, 1.0, 120, 10);

        /** Rejects a field that cannot be dated. */
        public Settings {
            if (events < 1 || boulders < 1 || thalli < 1 || minAge < 0 || maxAge < minAge || !(lag >= 0)
                    || !(delayMean >= 0) || !(fastRate > 0) || !(fastYears >= 0) || !(slowRate > 0)
                    || !(noise >= 0) || budget < 0 || !(tolerance >= 0)) {
                throw new IllegalArgumentException("bad lichen clock settings");
            }
        }
    }

    /** One event's judging. */
    public record Dating(int event, int trueAge, double guess, boolean dated) {}

    /** The result. */
    public record Report(Outcome outcome, List<Dating> datings, boolean ordered, double meanError) {

        /** Defensive copy. */
        public Report {
            datings = List.copyOf(datings);
        }
    }

    private final Settings s;
    private final int[] age;
    private final double[][] diameters;
    private int spent;

    private LichenClock(Settings s, long seed) {
        this.s = s;
        SplittableRandom rng = new SplittableRandom(seed);
        age = new int[s.events()];
        diameters = new double[s.events() * s.boulders()][s.thalli()];
        for (int e = 0; e < s.events(); e++) {
            age[e] = s.minAge() + rng.nextInt(s.maxAge() - s.minAge() + 1);
            for (int b = 0; b < s.boulders(); b++) {
                for (int t = 0; t < s.thalli(); t++) {
                    double delay = -s.delayMean() * Math.log(1 - rng.nextDouble());
                    double grown = Math.max(0, age[e] - s.lag() - delay);
                    double d = curve(grown) + s.noise() * (2 * rng.nextDouble() - 1);
                    diameters[e * s.boulders() + b][t] = Math.max(0, d);
                }
            }
        }
    }

    /** A seeded boulder field. */
    public static LichenClock field(Settings settings, long seed) {
        if (settings == null) {
            throw new IllegalArgumentException("settings");
        }
        return new LichenClock(settings, seed);
    }

    /** Diameter in mm after {@code years} of growth. */
    public double curve(double years) {
        if (years <= 0) {
            return 0;
        }
        if (years <= s.fastYears()) {
            return s.fastRate() * years;
        }
        return s.fastRate() * s.fastYears() + s.slowRate() * (years - s.fastYears());
    }

    /** The surface age the largest-lichen method reads from a diameter: the curve inverted, plus the lag. */
    public double age(double diameterMm) {
        if (!(diameterMm > 0)) {
            return s.lag();
        }
        double fast = s.fastRate() * s.fastYears();
        double grown = diameterMm <= fast ? diameterMm / s.fastRate()
                : s.fastYears() + (diameterMm - fast) / s.slowRate();
        return s.lag() + grown;
    }

    /**
     * Measure the first {@code n} thalli on a boulder of an event and return the largest diameter in mm, or -1 when
     * the budget, the event, the boulder or {@code n} is out of range. Measuring the same thalli again costs again.
     */
    public double measure(int event, int boulder, int n) {
        if (event < 0 || event >= s.events() || boulder < 0 || boulder >= s.boulders() || n < 1 || n > s.thalli()
                || spent + n > s.budget()) {
            return -1;
        }
        spent += n;
        double[] d = diameters[event * s.boulders() + boulder];
        double max = 0;
        for (int t = 0; t < n; t++) {
            max = Math.max(max, d[t]);
        }
        return max;
    }

    /**
     * What a boulder field of this surface age looks like on the BattlefieldEcology grid: BARE before lichens can
     * colonize, MEADOW (pioneer cover between the rocks) through the great growth phase, SCRUB after.
     */
    public Vegetation ground(double surfaceAge) {
        if (surfaceAge < s.lag()) {
            return Vegetation.BARE;
        }
        return surfaceAge < s.lag() + s.fastYears() ? Vegetation.MEADOW : Vegetation.SCRUB;
    }

    /** Measurements left. */
    public int budgetLeft() {
        return s.budget() - spent;
    }

    /** Events in the field. */
    public int events() {
        return s.events();
    }

    /** Judge the player's guesses (one surface age per event, years). */
    public Report judge(double[] guesses) {
        if (guesses == null || guesses.length != s.events()) {
            throw new IllegalArgumentException("one guess per event");
        }
        List<Dating> out = new ArrayList<>();
        boolean all = true;
        double err = 0;
        for (int e = 0; e < s.events(); e++) {
            double off = Math.abs(guesses[e] - age[e]);
            boolean ok = off <= s.tolerance();
            all &= ok;
            err += off;
            out.add(new Dating(e, age[e], guesses[e], ok));
        }
        boolean ordered = true;
        for (int a = 0; a < s.events(); a++) {
            for (int b = 0; b < s.events(); b++) {
                if (age[a] < age[b] && !(guesses[a] < guesses[b])) {
                    ordered = false;
                }
            }
        }
        Outcome outcome = all && ordered ? Outcome.DATED : ordered ? Outcome.ORDERED : Outcome.MUDDLED;
        return new Report(outcome, out, ordered, err / s.events());
    }
}
