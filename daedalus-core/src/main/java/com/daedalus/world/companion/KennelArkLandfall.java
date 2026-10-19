// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Kennel Isle ark chapter "Landfall on the Cinder Shelf" (contest, after G140 Crossing the Storm Belt). The ark that
 * crossed the storm belt beaches on the Cinder Shelf, a fragment of the shattered planet, with whatever hull and water
 * it arrived with. Over at most {@link #DAYS} days the crew mends the hull before setting out again: each day the spring
 * finder (G107 "fetch" post) brings {@link #FETCH_PLANKS} driftwood planks on a hit, the deck runner ("come" post) hauls
 * {@link #HAUL_PLANKS} more, and every plank mends one hull up to {@link #HULL_FULL}. The rescue swimmer ("rescue" post)
 * brings one stranded animal ashore on a hit. Water drops by one each day. The ark is seaworthy when the hull is full
 * before the casks run dry. Every day rolls fetch, haul and rescue once each, in that order, so results are pure and
 * deterministic; an empty post always misses.
 */
public final class KennelArkLandfall {
    public static final int DAYS = 5;
    public static final int HULL_FULL = KennelArkVoyage.START_HULL;
    public static final int FETCH_PLANKS = 2;
    public static final int HAUL_PLANKS = 1;
    public static final int STRANDED_COUNT = 3;
    public static final int ROLLS_PER_DAY = 3;
    /** Animals that can be found stranded on the shelf. */
    public static final List<String> STRANDED = List.of("sky-crane", "salt goat", "ember fox", "reef otter", "cinder hare",
        "ark cat");

    public record Day(int day, boolean fetched, boolean hauled, String rescued, int planks, int hull, int water) { }

    public record Landfall(boolean seaworthy, List<Day> days, int hull, int water, List<String> rescued, String failReason) {
        public Landfall {
            days = List.copyOf(days);
            rescued = List.copyOf(rescued);
        }
    }

    /** The whole chapter: the G140 voyage (same seeds as {@code crossingTheStormBelt}) and, if it arrived, the landfall. */
    public record Chapter(KennelArkVoyage.Voyage voyage, Landfall landfall) {
        public boolean complete() {
            return voyage.arrived() && landfall != null && landfall.seaworthy();
        }

        public String failReason() {
            if (!voyage.arrived()) {
                return voyage.legs().isEmpty() ? voyage.failReason() : "the ark never made landfall: " + voyage.failReason();
            }
            return landfall.failReason();
        }
    }

    private KennelArkLandfall() { }

    /** The seeded animals stranded on the shelf: {@link #STRANDED_COUNT} distinct ones, in rescue order. */
    public static List<String> stranded(long seed) {
        SplittableRandom r = new SplittableRandom(seed);
        List<String> pool = new ArrayList<>(STRANDED);
        List<String> out = new ArrayList<>();
        for (int i = 0; i < STRANDED_COUNT; i++) {
            out.add(pool.remove(r.nextInt(pool.size())));
        }
        return out;
    }

    private static int pct(KennelArkMuster.Roster roster, String role) {
        return roster.posts().stream().filter(p -> p.role().equals(role)).mapToInt(KennelArkMuster.Post::pct).findFirst()
            .orElse(0);
    }

    /** Mend the beached ark. Stops on the day the hull is full or the casks run dry; a full hull needs no days. */
    public static Landfall repair(KennelArkMuster.Roster roster, int hull, int water, List<String> stranded, long seed) {
        if (roster == null || stranded == null || hull < 1 || hull > HULL_FULL || water < 1
            || water > KennelArkVoyage.START_WATER) {
            throw new IllegalArgumentException("landfall needs a roster, stranded list, hull 1.." + HULL_FULL
                + " and water 1.." + KennelArkVoyage.START_WATER);
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[] rolls = new int[ROLLS_PER_DAY * DAYS];
        for (int i = 0; i < rolls.length; i++) {
            rolls[i] = r.nextInt(100);
        }
        return repairRolls(roster, hull, water, stranded, rolls);
    }

    /**
     * The roll-driven rule behind {@link #repair}: {@link #ROLLS_PER_DAY} rolls 0..99 per day (fetch, haul, rescue). The
     * C++ twin {@code DaedalusKennelVoyageCore.h} (G154) replays exactly this from server rolls.
     */
    public static Landfall repairRolls(KennelArkMuster.Roster roster, int hull, int water, List<String> stranded, int[] rolls) {
        if (roster == null || stranded == null || hull < 1 || hull > HULL_FULL || water < 1
            || water > KennelArkVoyage.START_WATER || rolls == null || rolls.length < ROLLS_PER_DAY * DAYS) {
            throw new IllegalArgumentException("landfall needs a roster, stranded list, hull 1.." + HULL_FULL
                + ", water 1.." + KennelArkVoyage.START_WATER + " and " + ROLLS_PER_DAY * DAYS + " rolls");
        }
        int fetchPct = pct(roster, "fetch");
        int haulPct = pct(roster, "come");
        int rescuePct = pct(roster, "rescue");
        List<Day> days = new ArrayList<>();
        List<String> rescued = new ArrayList<>();
        for (int d = 1; d <= DAYS && hull < HULL_FULL; d++) {
            int k = (d - 1) * ROLLS_PER_DAY;
            boolean fetched = rolls[k] < fetchPct;
            boolean hauled = rolls[k + 1] < haulPct;
            boolean swam = rolls[k + 2] < rescuePct;
            String saved = swam && rescued.size() < stranded.size() ? stranded.get(rescued.size()) : null;
            if (saved != null) {
                rescued.add(saved);
            }
            int planks = (fetched ? FETCH_PLANKS : 0) + (hauled ? HAUL_PLANKS : 0);
            hull = Math.min(HULL_FULL, hull + planks);
            water--;
            days.add(new Day(d, fetched, hauled, saved, planks, hull, water));
            if (water == 0) {
                return new Landfall(false, days, hull, water, rescued, "the casks ran dry on the shelf");
            }
        }
        boolean seaworthy = hull == HULL_FULL;
        return new Landfall(seaworthy, days, hull, water, rescued, seaworthy ? null : "the hull was not mended in time");
    }

    /** The chapter: G107 lift, G140 crossing (identical seeds), then landfall and repair on the Cinder Shelf. */
    public static Chapter landfallOnTheCinderShelf(List<KennelGrowth.Pup> hounds, long seed) {
        SplittableRandom r = new SplittableRandom(seed);
        KennelArkMuster.QuestResult lift = KennelArkMuster.musterAtHullBay(hounds, r.nextLong());
        if (!lift.complete()) {
            return new Chapter(new KennelArkVoyage.Voyage(false, List.of(), KennelArkVoyage.START_HULL,
                KennelArkVoyage.START_WATER, "the ark never lifted: " + lift.failReason()), null);
        }
        KennelArkVoyage.Voyage voyage = KennelArkVoyage.cross(lift.roster(), KennelArkVoyage.storms(r.nextLong()), r.nextLong());
        if (!voyage.arrived()) {
            return new Chapter(voyage, null);
        }
        return new Chapter(voyage, repair(lift.roster(), voyage.hull(), voyage.water(), stranded(r.nextLong()), r.nextLong()));
    }
}