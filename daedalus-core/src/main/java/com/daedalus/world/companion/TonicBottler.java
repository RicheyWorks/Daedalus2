// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import com.daedalus.world.companion.TonicBrewer.Brew;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.OptionalInt;
import java.util.TreeMap;

/**
 * Kennel Isle tonic bottling (contest gap G45). A {@link TonicBrewer} brew is drunk at the trough today; bottling keeps
 * it. The bottle's tier (T1-T4) comes from a quality score: brew strength factor (0-2) times 50, plus the water grade
 * (raw -15, filtered 0, spring +10, from the G17 {@link KennelWaterLoop}), plus 15 if the Labyrinth second roll
 * landed. T4 also needs spring water. Each tier has a duration multiplier, a shelf life and a material list; T4 is
 * sealed in salvaged ark glass instead of a plain bottle. Missing materials bottle the brew at the best tier the shelf
 * can afford. A bottle drops one tier per elapsed shelf life and spoils below T1. Pure and deterministic.
 *
 * <p>Quest "The Ark Glass Cellar" ({@link #cellarReady}): on the quest day the cellar holds at least one T4 bottle and
 * at least four bottles at T3 or better.
 */
public final class TonicBottler {
    public static final String BOTTLE = "bottle";
    public static final String CORK = "cork";
    public static final String WAX = "wax";
    public static final String ARK_GLASS = "ark_glass";

    /** Water the brew was steeped in. */
    public enum Water {
        RAW(-15), FILTERED(0), SPRING(10);

        private final int bonus;

        Water(int bonus) {
            this.bonus = bonus;
        }

        public int bonus() {
            return bonus;
        }
    }

    /** Bottle tiers: duration multiplier, shelf life in days, materials. */
    public enum Tier {
        T1(1.0, 3, Map.of(BOTTLE, 1)),
        T2(1.25, 7, Map.of(BOTTLE, 1, CORK, 1)),
        T3(1.5, 14, Map.of(BOTTLE, 1, CORK, 1, WAX, 1)),
        T4(2.0, 30, Map.of(ARK_GLASS, 1, CORK, 1, WAX, 1));

        private final double durationMult;
        private final int shelfDays;
        private final Map<String, Integer> materials;

        Tier(double durationMult, int shelfDays, Map<String, Integer> materials) {
            this.durationMult = durationMult;
            this.shelfDays = shelfDays;
            this.materials = materials;
        }

        public double durationMult() {
            return durationMult;
        }

        public int shelfDays() {
            return shelfDays;
        }

        public Map<String, Integer> materials() {
            return Collections.unmodifiableMap(new TreeMap<>(materials));
        }

        public int level() {
            return ordinal() + 1;
        }

        static Tier ofLevel(int level) {
            return values()[level - 1];
        }
    }

    public record Bottle(String recipeId, Tier tier, int baseDurationSec, int bottledDay) { }

    /** Result of a bottling: the bottle (empty if not even T1 is affordable) and the materials left. */
    public record Bottling(Optional<Bottle> bottle, Tier qualityTier, Map<String, Integer> remaining) {
        public Bottling {
            remaining = Collections.unmodifiableMap(new TreeMap<>(remaining));
        }
    }

    private TonicBottler() {
    }

    public static int score(double factor, Water water, boolean secondRoll) {
        return (int) Math.round(Math.max(0, Math.min(2, factor)) * 50) + water.bonus() + (secondRoll ? 15 : 0);
    }

    /** The tier the brew deserves, ignoring materials. */
    public static Tier qualityTier(double factor, Water water, boolean secondRoll) {
        int s = score(factor, water, secondRoll);
        if (s >= 100 && water == Water.SPRING) {
            return Tier.T4;
        }
        if (s >= 70) {
            return Tier.T3;
        }
        return s >= 40 ? Tier.T2 : Tier.T1;
    }

    /** Bottles a brew on {@code day}, spending materials from {@code stock}; downgrades if materials run short. */
    public static Bottling bottle(Brew brew, Water water, boolean secondRoll, Map<String, Integer> stock, int day) {
        Tier q = qualityTier(brew.factor(), water, secondRoll);
        for (int lv = q.level(); lv >= 1; lv--) {
            Tier t = Tier.ofLevel(lv);
            if (affords(stock, t)) {
                Map<String, Integer> left = new TreeMap<>(stock);
                t.materials.forEach((k, v) -> left.merge(k, -v, Integer::sum));
                return new Bottling(Optional.of(new Bottle(brew.recipe().id(), t, brew.durationSec(), day)), q, left);
            }
        }
        return new Bottling(Optional.empty(), q, stock);
    }

    static boolean affords(Map<String, Integer> stock, Tier t) {
        return t.materials.entrySet().stream().allMatch(e -> stock.getOrDefault(e.getKey(), 0) >= e.getValue());
    }

    /** The bottle's tier level on {@code day} (1-4), or empty once spoiled. */
    public static OptionalInt tierAt(Bottle b, int day) {
        int remaining = Math.max(0, day - b.bottledDay());
        int lv = b.tier().level();
        while (lv >= 1 && remaining >= Tier.ofLevel(lv).shelfDays()) {
            remaining -= Tier.ofLevel(lv).shelfDays();
            lv--;
        }
        return lv >= 1 ? OptionalInt.of(lv) : OptionalInt.empty();
    }

    /** Effect duration in seconds if drunk on {@code day}; 0 once spoiled. */
    public static int durationAt(Bottle b, int day) {
        OptionalInt lv = tierAt(b, day);
        return lv.isPresent() ? (int) Math.round(b.baseDurationSec() * Tier.ofLevel(lv.getAsInt()).durationMult()) : 0;
    }

    /** Quest check: at least one T4 and at least four bottles at T3 or better on {@code day}. */
    public static boolean cellarReady(List<Bottle> cellar, int day) {
        int t4 = 0;
        int t3plus = 0;
        for (Bottle b : cellar) {
            OptionalInt lv = tierAt(b, day);
            if (lv.isPresent() && lv.getAsInt() >= 3) {
                t3plus++;
                if (lv.getAsInt() == 4) {
                    t4++;
                }
            }
        }
        return t4 >= 1 && t3plus >= 4;
    }
}