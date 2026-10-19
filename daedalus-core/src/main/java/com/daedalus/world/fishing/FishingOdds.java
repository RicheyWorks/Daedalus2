// SPDX-License-Identifier: MIT

package com.daedalus.world.fishing;

import com.daedalus.world.odds.Intervals;
import com.daedalus.world.odds.OddsRng;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * The OddsReaper view of a fishing spot: exact per-cast odds (which fish bites, the chance the angler lands it, the
 * expected sale value of one cast), a seeded Monte Carlo check of the same numbers with a 95% Wilson interval, and the
 * "Storm Parlay" a storm-island inn chalks up: name the catch of each of the next casts in order and see the true chance
 * and the fair payout multiplier. Built on the Combat Odds Engine's {@link OddsRng} and {@link Intervals}.
 */
public final class FishingOdds {

    /** Salt that separates a cast's reaction stream from the cast's own (wait, pick) stream. */
    static final long REACTION_SALT = 0x0DD5_2EA9_E2F1_5E77L;

    private FishingOdds() {
    }

    /** One fish's line in a breakdown. {@code catchShare} = biteShare x catchChance; {@code value} = catchShare x price. */
    public record Line(String name, Rarity rarity, double biteShare, double catchChance, double catchShare, double value) {
    }

    /** Exact odds for one cast at a spot. */
    public static final class Breakdown {
        private final Conditions conditions;
        private final AnglerSkill skill;
        private final List<Line> lines;
        private final double landChance;
        private final double expectedValue;

        Breakdown(Conditions conditions, AnglerSkill skill, List<Line> lines) {
            this.conditions = conditions;
            this.skill = skill;
            this.lines = List.copyOf(lines);
            double land = 0;
            double ev = 0;
            for (Line l : lines) {
                land += l.catchShare();
                ev += l.value();
            }
            this.landChance = land;
            this.expectedValue = ev;
        }

        public Conditions conditions() {
            return conditions;
        }

        public AnglerSkill skill() {
            return skill;
        }

        /** Per-fish lines in table order. A copy. */
        public List<Line> lines() {
            return new ArrayList<>(lines);
        }

        /** Chance a single cast (struck at the bite) lands anything. */
        public double landChance() {
            return landChance;
        }

        /** Expected sale value of one cast, in gold. */
        public double expectedValue() {
            return expectedValue;
        }

        /** Chance one cast lands {@code name}. */
        public double catchShare(String name) {
            for (Line l : lines) {
                if (l.name().equals(name)) {
                    return l.catchShare();
                }
            }
            throw new IllegalArgumentException("no fish '" + name + "' in this breakdown");
        }

        /** Chance one cast lands a RARE or LEGENDARY fish. */
        public double rareShare() {
            double r = 0;
            for (Line l : lines) {
                if (l.rarity().isRare()) {
                    r += l.catchShare();
                }
            }
            return r;
        }

        /** Expected casts to land {@code name} at least once (geometric mean wait); infinite if it cannot be landed. */
        public double castsToLand(String name) {
            double p = catchShare(name);
            return p > 0 ? 1 / p : Double.POSITIVE_INFINITY;
        }
    }

    /** What a seeded run of casts actually did. */
    public static final class Simulation {
        private final long seed;
        private final int casts;
        private final int landed;
        private final double low;
        private final double high;
        private final double meanValue;
        private final Map<String, Integer> catches;

        Simulation(long seed, int casts, int landed, double[] wilson, double meanValue, Map<String, Integer> catches) {
            this.seed = seed;
            this.casts = casts;
            this.landed = landed;
            this.low = wilson[0];
            this.high = wilson[1];
            this.meanValue = meanValue;
            this.catches = Collections.unmodifiableMap(new LinkedHashMap<>(catches));
        }

        public long seed() {
            return seed;
        }

        public int casts() {
            return casts;
        }

        public int landed() {
            return landed;
        }

        public double landRate() {
            return (double) landed / casts;
        }

        /** Lower end of the 95% Wilson interval on the land rate. */
        public double low() {
            return low;
        }

        /** Upper end of the 95% Wilson interval on the land rate. */
        public double high() {
            return high;
        }

        /** Mean sale value per cast. */
        public double meanValue() {
            return meanValue;
        }

        /** Landed count per fish, table order. A read-only snapshot. */
        public Map<String, Integer> catches() {
            return new LinkedHashMap<>(catches);
        }
    }

    /** A Storm Parlay ticket: every leg must land, in order. */
    public record Parlay(int legs, double probability, double fairMultiplier) {

        /** Expected profit of staking {@code stake} at an offered multiplier (stake back included in the multiplier). */
        public double expectedProfit(double stake, double offeredMultiplier) {
            return stake * (probability * offeredMultiplier - 1);
        }

        /** True when an offered multiplier pays at least the fair one, i.e. the ticket is not a sucker bet. */
        public boolean fair(double offeredMultiplier) {
            return offeredMultiplier >= fairMultiplier;
        }
    }

    /** Exact odds of one cast at a spot stocked by {@code table}. */
    public static Breakdown exact(FishTable table, Conditions c, AnglerSkill skill) {
        double tot = table.totalWeight(c);
        List<Line> lines = new ArrayList<>();
        for (FishSpecies f : table.fish()) {
            double share = c.weight(f) / tot;
            double land = skill.catchChance(c.window(f));
            lines.add(new Line(f.name(), f.rarity(), share, land, share * land, share * land * f.price()));
        }
        return new Breakdown(c, skill, lines);
    }

    /**
     * Plays {@code casts} casts through {@link CastSession}: wait for the bite, then strike after a reaction drawn from
     * {@code skill}. Deterministic in {@code seed}; cast {@code i} uses its own streams, so order does not matter.
     */
    public static Simulation simulate(FishTable table, Conditions c, AnglerSkill skill, long seed, int casts) {
        if (casts < 1) {
            throw new IllegalArgumentException("simulate needs at least one cast, got " + casts);
        }
        Map<String, Integer> catches = new LinkedHashMap<>();
        for (FishSpecies f : table.fish()) {
            catches.put(f.name(), 0);
        }
        int landed = 0;
        double value = 0;
        for (int i = 0; i < casts; i++) {
            CastSession cast = new CastSession(table, c, seed, i);
            cast.tick(cast.waitSeconds());
            cast.tick(skill.sampleReaction(OddsRng.forTrial(seed ^ REACTION_SALT, i)));
            if (cast.strike() == CastSession.Outcome.CAUGHT) {
                FishSpecies f = cast.fish().orElseThrow();
                landed++;
                value += f.price();
                catches.merge(f.name(), 1, Integer::sum);
            }
        }
        return new Simulation(seed, casts, landed, Intervals.wilson(landed, casts), value / casts, catches);
    }

    /** The Storm Parlay for landing {@code legs} in order, one per cast. */
    public static Parlay parlay(FishTable table, Conditions c, AnglerSkill skill, List<String> legs) {
        if (legs == null || legs.isEmpty()) {
            throw new IllegalArgumentException("a parlay needs at least one leg");
        }
        Breakdown b = exact(table, c, skill);
        double p = 1;
        for (String leg : legs) {
            p *= b.catchShare(leg);
        }
        return new Parlay(legs.size(), p, p > 0 ? 1 / p : Double.POSITIVE_INFINITY);
    }

    /** A short plain-text table of a breakdown, for logs and the demo. */
    public static String describe(Breakdown b) {
        StringBuilder s = new StringBuilder();
        s.append(String.format(Locale.ROOT, "%s, reaction %.2fs: land %.1f%%, rare %.2f%%, EV %.2f gold/cast%n",
                b.conditions().label(), b.skill().reactionMean(), 100 * b.landChance(), 100 * b.rareShare(),
                b.expectedValue()));
        for (Line l : b.lines) {
            s.append(String.format(Locale.ROOT, "  %-16s %-9s bite %5.1f%%  land %5.1f%%  -> %5.2f%%%n", l.name(),
                    l.rarity(), 100 * l.biteShare(), 100 * l.catchChance(), 100 * l.catchShare()));
        }
        return s.toString();
    }
}
