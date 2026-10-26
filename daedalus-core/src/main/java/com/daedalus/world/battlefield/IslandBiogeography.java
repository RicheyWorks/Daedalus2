// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import java.util.ArrayList;
import java.util.List;

/**
 * Island Biogeography (contest G119): MacArthur and Wilson's equilibrium on the sky islands.
 *
 * <p>A mainland holds a pool of {@code pool} species. Each island has an area and a distance from the mainland. Every
 * year, independently for every island and species:
 * <ul>
 *   <li>an absent species arrives with chance {@code I = colonize · exp(−d/reach)}, where d is the island's effective
 *       distance;</li>
 *   <li>a present species dies out with chance {@code E = min(1, extinct / area^z)}.</li>
 * </ul>
 * Each species then flips between two states, so the island's expected richness settles at
 * {@code S* = pool · I / (I + E)}. Near and large islands hold the most species. The player has {@code stones}
 * stepping-stone rafts; each raft put on the way to an island divides its effective distance by (1 + rafts).
 * Every draw is a splitmix hash of (seed, year, island, species, salt), so moving a raft never shifts other dice.
 *
 * <p>The closing census (the refuge's mean richness over the last ten years) must reach {@code goal}: THRIVING. At least three quarters of the goal is
 * FRAGILE, and anything less is BARREN.
 */
public final class IslandBiogeography {

    /** Years the closing census averages over. */
    public static final int CENSUS_YEARS = 10;

    /** How the refuge ended. */
    public enum Outcome { THRIVING, FRAGILE, BARREN }

    /**
     * An island.
     *
     * @param name     display name
     * @param area     area in hectares (positive)
     * @param distance distance from the mainland in km (non-negative)
     */
    public record Isle(String name, double area, double distance) {

        /** Rejects an island that cannot exist. */
        public Isle {
            if (name == null || name.isBlank() || !(area > 0) || !(distance >= 0) || Double.isInfinite(area)
                    || Double.isInfinite(distance)) {
                throw new IllegalArgumentException("bad isle");
            }
        }
    }

    /**
     * Archipelago tuning.
     *
     * @param pool     mainland species pool
     * @param years    years to run
     * @param colonize arrival chance at distance 0
     * @param reach    distance scale of arrivals (km)
     * @param extinct  extinction chance on a 1 ha island
     * @param z        area exponent of extinction
     * @param stones   stepping-stone rafts the player can place
     * @param refuge   index of the ark refuge island
     * @param goal     species the refuge needs
     */
    public record Settings(int pool, int years, double colonize, double reach, double extinct, double z, int stones,
            int refuge, int goal) {

        /** The default archipelago tuning. */
        public static final Settings DEFAULT = new Settings(40, 80, 0.2, 3.0, 0.6, 0.5, 3, 3, 18);

        /** Rejects tuning that cannot run. */
        public Settings {
            if (pool < 1 || years < 1 || !(colonize >= 0 && colonize <= 1) || !(reach > 0) || !(extinct >= 0)
                    || !(z >= 0) || stones < 0 || refuge < 0 || goal < 0 || goal > pool) {
                throw new IllegalArgumentException("bad biogeography settings");
            }
        }
    }

    /** The default sky archipelago. The refuge (index 3) is large but far out. */
    public static final List<Isle> SKY = List.of(
            new Isle("Gull Stack", 4, 1),
            new Isle("Fernholm", 25, 3),
            new Isle("Thimble", 1, 6),
            new Isle("Ark Refuge", 64, 9),
            new Isle("Cinder Key", 9, 12));

    /** One year of richness per island. */
    public record Year(int index, List<Integer> richness) {

        /** Defensive copy. */
        public Year {
            richness = List.copyOf(richness);
        }
    }

    /**
     * The result. {@code census} is the refuge's mean richness over the last {@link #CENSUS_YEARS} years (the
     * Tidewardens' count), which is what the quest judges; {@code richness} is each island's count in the final year.
     */
    public record Report(Outcome outcome, double census, List<Integer> richness, List<Double> equilibrium, List<Integer> rafts,
            List<Year> years) {

        /** Defensive copies. */
        public Report {
            richness = List.copyOf(richness);
            equilibrium = List.copyOf(equilibrium);
            rafts = List.copyOf(rafts);
            years = List.copyOf(years);
        }

        /**
         * Island {@code i}'s cover band: share of the pool present. Under 15% is BARE, under 35% SCRUB, under 60%
         * MEADOW, otherwise OAK.
         */
        public Vegetation band(int i, int pool) {
            double share = (double) richness.get(i) / pool;
            if (share < 0.15) {
                return Vegetation.BARE;
            }
            if (share < 0.35) {
                return Vegetation.SCRUB;
            }
            return share < 0.6 ? Vegetation.MEADOW : Vegetation.OAK;
        }
    }

    private final Settings s;
    private final List<Isle> isles;
    private final long seed;
    private final int[] rafts;

    private IslandBiogeography(Settings s, List<Isle> isles, long seed) {
        this.s = s;
        this.isles = List.copyOf(isles);
        this.seed = seed;
        this.rafts = new int[isles.size()];
    }

    /** A seeded archipelago. */
    public static IslandBiogeography archipelago(Settings settings, List<Isle> isles, long seed) {
        if (settings == null || isles == null || isles.isEmpty() || settings.refuge() >= isles.size()) {
            throw new IllegalArgumentException("bad archipelago");
        }
        return new IslandBiogeography(settings, isles, seed);
    }

    /** Puts one stepping-stone raft on the way to island {@code i}. False if none are left or i is not an island. */
    public boolean raft(int i) {
        if (i < 0 || i >= rafts.length || raftsLeft() == 0) {
            return false;
        }
        rafts[i]++;
        return true;
    }

    /** Rafts not yet placed. */
    public int raftsLeft() {
        int used = 0;
        for (int r : rafts) {
            used += r;
        }
        return s.stones() - used;
    }

    /** Island {@code i}'s effective distance with its rafts. */
    public double distance(int i) {
        return isles.get(i).distance() / (1 + rafts[i]);
    }

    /** Island {@code i}'s yearly arrival chance per absent species. */
    public double immigration(int i) {
        return s.colonize() * Math.exp(-distance(i) / s.reach());
    }

    /** Island {@code i}'s yearly extinction chance per present species. */
    public double extinction(int i) {
        return Math.min(1.0, s.extinct() / Math.pow(isles.get(i).area(), s.z()));
    }

    /** Island {@code i}'s equilibrium richness {@code pool · I / (I + E)} (0 when both are 0). */
    public double equilibrium(int i) {
        double in = immigration(i);
        double out = extinction(i);
        return in + out <= 0 ? 0 : s.pool() * in / (in + out);
    }

    /** Runs the archipelago from empty islands. Deterministic in the settings, isles, seed and rafts. */
    public Report run() {
        int n = isles.size();
        boolean[][] here = new boolean[n][s.pool()];
        List<Year> log = new ArrayList<>();
        for (int y = 0; y < s.years(); y++) {
            List<Integer> rich = new ArrayList<>();
            for (int i = 0; i < n; i++) {
                double in = immigration(i);
                double out = extinction(i);
                int count = 0;
                for (int sp = 0; sp < s.pool(); sp++) {
                    double r = roll(y, i, sp);
                    here[i][sp] = here[i][sp] ? r >= out : r < in;
                    if (here[i][sp]) {
                        count++;
                    }
                }
                rich.add(count);
            }
            log.add(new Year(y, rich));
        }
        List<Integer> end = log.get(log.size() - 1).richness();
        List<Double> eq = new ArrayList<>();
        List<Integer> placed = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            eq.add(equilibrium(i));
            placed.add(rafts[i]);
        }
        int from = Math.max(0, log.size() - CENSUS_YEARS);
        double census = 0;
        for (int y = from; y < log.size(); y++) {
            census += log.get(y).richness().get(s.refuge());
        }
        census /= log.size() - from;
        Outcome outcome = census >= s.goal() ? Outcome.THRIVING
                : census * 4 >= s.goal() * 3 ? Outcome.FRAGILE : Outcome.BARREN;
        return new Report(outcome, census, end, eq, placed, log);
    }

    private double roll(int year, int isle, int species) {
        long z = seed + 0x9E3779B97F4A7C15L * (year + 1) + 0xBF58476D1CE4E5B9L * (isle + 1)
                + 0x94D049BB133111EBL * (species + 1);
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        z = z ^ (z >>> 31);
        return (z >>> 11) * 0x1.0p-53;
    }
}
