// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import java.util.EnumMap;
import java.util.Map;
import java.util.SplittableRandom;

/**
 * Ark Seed Vault (contest G43): keep the ark's seed lots alive on the voyage so there is seed to bring a scorched
 * fragment back (ASH01 Ashfall Regrowth).
 *
 * <p>Seed ageing follows the Ellis and Roberts (1980) seed viability equation. A lot's viability in probits is
 * {@code v = Ki - p / sigma}, where Ki is its starting probit, p the days in store, and
 * {@code log10 sigma = KE - CW log10 m - CH T - CQ T^2}, with moisture content m in % fresh weight, temperature T
 * in degrees C, the universal temperature constants CH = 0.0329 and CQ = 0.000478, and species constants KE and CW.
 * The share of seeds alive is the normal CDF of v. Conditions change year by year, so each year subtracts
 * 365 / sigma at that year's conditions.
 *
 * <p>The player runs the vault one year at a time against the ark's power budget:
 * <ul>
 *   <li>{@link #dry} brings a lot's moisture down (power per point). Oak acorns are recalcitrant: dried below
 *       {@code OAK_CRITICAL_MOISTURE} they die.</li>
 *   <li>{@link #year} keeps the whole vault at one temperature for a year (power per degree below the hold's
 *       ambient). Any lot moister than {@code ICE_MOISTURE} dies if kept below 0 C, because ice forms in the seed.</li>
 *   <li>{@link #regrow} plants a whole lot on a stopover fragment (every {@code stopoverEvery} years) and harvests
 *       fresh seed in proportion to the live seed planted.</li>
 *   <li>{@link #germinationTest} spends seeds to measure a lot (a seeded binomial draw).</li>
 * </ul>
 * At landfall, every {@code seedsPerCache} live seeds of a lot fill one ark seed cache for Ashfall Regrowth.
 */
public final class SeedVault {

    public static final double CH = 0.0329;
    public static final double CQ = 0.000478;
    /** Oak acorns die when dried below this moisture (% fresh weight). */
    public static final double OAK_CRITICAL_MOISTURE = 30.0;
    /** Lots moister than this die if stored below 0 C. */
    public static final double ICE_MOISTURE = 20.0;
    /** Probit of a dead lot. */
    public static final double DEAD = -10.0;

    /** The ark's seed stock: one lot per succession band, with its viability constants. */
    public enum Species {
        MEADOW_GRASS(8.6, 4.9, 15.0, Vegetation.MEADOW),
        BRAMBLE(9.4, 5.0, 15.0, Vegetation.SCRUB),
        PINE(8.8, 4.6, 15.0, Vegetation.PINE),
        OAK(6.0, 2.0, 40.0, Vegetation.OAK),
        WILLOW(7.2, 4.5, 15.0, Vegetation.WETLAND);

        private final double ke;
        private final double cw;
        private final double freshMoisture;
        private final Vegetation grows;

        Species(double ke, double cw, double freshMoisture, Vegetation grows) {
            this.ke = ke;
            this.cw = cw;
            this.freshMoisture = freshMoisture;
            this.grows = grows;
        }

        public double ke() { return ke; }
        public double cw() { return cw; }
        public double freshMoisture() { return freshMoisture; }
        public Vegetation grows() { return grows; }

        /** Ellis-Roberts sigma in days at moisture m (%) and temperature t (C). */
        public double sigmaDays(double moisturePct, double tempC) {
            return Math.pow(10, ke - cw * Math.log10(moisturePct) - CH * tempC - CQ * tempC * tempC);
        }
    }

    /**
     * Tuning.
     *
     * @param voyageYears     years until landfall
     * @param seedsPerLot     seeds in each lot at the start (and a lot's capacity)
     * @param startProbit     Ki of fresh seed (2.0 = 97.7% alive)
     * @param ambientC        temperature of the uncooled hold
     * @param powerPerYear    the vault's power budget for a year
     * @param coolCost        power per degree below ambient per year
     * @param dryCost         power per moisture point removed from a lot
     * @param stopoverEvery   a stopover fragment every this many years (regrowing allowed then)
     * @param regrowsPerStop  lots that can be regrown at one stopover
     * @param harvestPerSeed  fresh seeds harvested per live seed planted
     * @param seedsPerCache   live seeds per ark seed cache at landfall
     */
    public record Settings(int voyageYears, int seedsPerLot, double startProbit, double ambientC, double powerPerYear,
            double coolCost, double dryCost, int stopoverEvery, int regrowsPerStop, double harvestPerSeed,
            int seedsPerCache) {

        public static final Settings DEFAULT = new Settings(12, 6000, 2.0, 20.0, 40, 1, 1, 3, 2, 5, 1000);

        public Settings {
            if (voyageYears < 1 || seedsPerLot < 1 || !Double.isFinite(startProbit) || !Double.isFinite(ambientC)
                    || !(powerPerYear >= 0) || !(coolCost >= 0) || !(dryCost >= 0) || stopoverEvery < 1
                    || regrowsPerStop < 0 || !(harvestPerSeed >= 0) || seedsPerCache < 1) {
                throw new IllegalArgumentException("bad SeedVault settings");
            }
        }
    }

    private final Settings s;
    private final SplittableRandom rng;
    private final Map<Species, double[]> lots = new EnumMap<>(Species.class);   // {seeds, probit, moisture}
    private int year;
    private double powerLeft;
    private int regrowsLeft;

    private SeedVault(Settings s, long seed) {
        this.s = s;
        this.rng = new SplittableRandom(seed);
        for (Species sp : Species.values()) {
            lots.put(sp, new double[] {s.seedsPerLot(), s.startProbit(), sp.freshMoisture()});
        }
        this.powerLeft = s.powerPerYear();
    }

    /** The vault as the ark leaves: one fresh lot per species. */
    public static SeedVault stock(Settings settings, long seed) {
        if (settings == null) {
            throw new IllegalArgumentException("settings are required");
        }
        return new SeedVault(settings, seed);
    }

    // ---- the keeper's moves -------------------------------------------------------------------------------------

    /**
     * Dries a lot down to the moisture given (% fresh weight), paying {@code dryCost} per point from this year's
     * power. False when it would raise the moisture, costs more power than is left, or the voyage is over. Drying oak
     * below the critical moisture kills it.
     */
    public boolean dry(Species sp, double moisturePct) {
        double[] lot = lot(sp);
        if (landed() || !(moisturePct > 0) || moisturePct > lot[2]) {
            return false;
        }
        double cost = (lot[2] - moisturePct) * s.dryCost();
        if (cost > powerLeft + 1e-9) {
            return false;
        }
        powerLeft -= cost;
        lot[2] = moisturePct;
        if (sp == Species.OAK && moisturePct < OAK_CRITICAL_MOISTURE) {
            lot[1] = DEAD;
        }
        return true;
    }

    /**
     * Keeps the vault at this temperature for one year. False (and no time passes) when the cooling costs more than
     * the power left this year or the voyage is over. Each lot loses 365 / sigma probits; moist lots below 0 C die.
     */
    public boolean year(double tempC) {
        if (landed() || !Double.isFinite(tempC)) {
            return false;
        }
        double cost = Math.max(0, s.ambientC() - tempC) * s.coolCost();
        if (cost > powerLeft + 1e-9) {
            return false;
        }
        for (Map.Entry<Species, double[]> e : lots.entrySet()) {
            double[] lot = e.getValue();
            if (lot[1] <= DEAD) {
                continue;
            }
            if (tempC < 0 && lot[2] > ICE_MOISTURE) {
                lot[1] = DEAD;
                continue;
            }
            lot[1] = Math.max(DEAD, lot[1] - 365.0 / e.getKey().sigmaDays(lot[2], tempC));
        }
        year++;
        powerLeft = s.powerPerYear();
        regrowsLeft = year % s.stopoverEvery() == 0 && !landed() ? s.regrowsPerStop() : 0;
        return true;
    }

    /**
     * Plants the whole lot on this year's stopover fragment and harvests fresh seed: {@code harvestPerSeed} per live
     * seed, up to the lot's capacity, at the fresh probit and the species' fresh moisture (dry it again). False when
     * this is not a stopover year, the stopover's regrows are used, or the lot has no live seed.
     */
    public boolean regrow(Species sp) {
        double[] lot = lot(sp);
        double live = liveSeeds(sp);
        if (regrowsLeft == 0 || live < 1) {
            return false;
        }
        regrowsLeft--;
        lot[0] = Math.min(s.seedsPerLot(), Math.floor(live * s.harvestPerSeed()));
        lot[1] = s.startProbit();
        lot[2] = sp.freshMoisture();
        return true;
    }

    /** Germinates n seeds from the lot (they are used up) and returns how many came up. */
    public int germinationTest(Species sp, int n) {
        double[] lot = lot(sp);
        if (n < 1 || n > lot[0]) {
            throw new IllegalArgumentException("test needs 1.." + (long) lot[0] + " seeds");
        }
        lot[0] -= n;
        double p = viability(sp);
        int up = 0;
        for (int k = 0; k < n; k++) {
            up += rng.nextDouble() < p ? 1 : 0;
        }
        return up;
    }

    // ---- queries ------------------------------------------------------------------------------------------------

    /** Share of the lot's seeds alive: the normal CDF of its probit. */
    public double viability(Species sp) {
        double v = lot(sp)[1];
        return v <= DEAD ? 0 : phi(v);
    }

    public double probit(Species sp) { return lot(sp)[1]; }
    public double moisture(Species sp) { return lot(sp)[2]; }
    public int seeds(Species sp) { return (int) lot(sp)[0]; }
    public double liveSeeds(Species sp) { return lot(sp)[0] * viability(sp); }
    public int year() { return year; }
    public boolean landed() { return year >= s.voyageYears(); }
    public double powerLeft() { return powerLeft; }
    public int regrowsLeft() { return regrowsLeft; }

    /** Ark seed caches this lot fills at landfall. */
    public int caches(Species sp) { return (int) Math.floor(liveSeeds(sp) / s.seedsPerCache()); }

    /** All the ark seed caches the vault fills. */
    public int caches() {
        int n = 0;
        for (Species sp : Species.values()) {
            n += caches(sp);
        }
        return n;
    }

    /** Species that still fill at least one cache. */
    public int survivingSpecies() {
        int n = 0;
        for (Species sp : Species.values()) {
            n += caches(sp) > 0 ? 1 : 0;
        }
        return n;
    }

    /** Ashfall Regrowth settings with this vault's caches. */
    public AshfallRegrowth.Settings forRegrowth(AshfallRegrowth.Settings base) {
        return new AshfallRegrowth.Settings(base.yearsPerSeason(), base.seedReach(), base.cacheRadius(), caches(),
                base.waterPerSeason(), base.waterRadius(), base.carryCells(), base.waterBoost(), base.herds(),
                base.grazeRadius(), base.strikeChance(), base.dryWind(), base.maxFireTicks(), base.oldGrowthTarget(),
                base.scorchedAt(), base.maxSeasons());
    }

    /** Standard normal CDF, via erfc (Numerical Recipes erfcc, fractional error below 1.2e-7). */
    static double phi(double x) {
        double z = Math.abs(x) / Math.sqrt(2);
        double t = 1 / (1 + 0.5 * z);
        double erfc = t * Math.exp(-z * z - 1.26551223 + t * (1.00002368 + t * (0.37409196 + t * (0.09678418
                + t * (-0.18628806 + t * (0.27886807 + t * (-1.13520398 + t * (1.48851587
                + t * (-0.82215223 + t * 0.17087277)))))))));
        return x >= 0 ? 1 - 0.5 * erfc : 0.5 * erfc;
    }

    private double[] lot(Species sp) {
        if (sp == null) {
            throw new IllegalArgumentException("species is required");
        }
        return lots.get(sp);
    }
}
