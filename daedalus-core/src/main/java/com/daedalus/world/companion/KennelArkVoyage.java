// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Kennel Isle ark voyage (contest, chapter "Crossing the Storm Belt", after G107 The Muster at Hull Bay). The ark that
 * lifted from Hull Bay crosses {@link #LEGS} legs of the storm belt. Each leg brings one seeded trouble, and the hound on
 * the matching G107 post answers it with its G61 odds: a boarding gust (hatch guard), a crewman overboard (rescue
 * swimmer), dry casks (spring finder) or a jammed signal line (deck runner). An answered trouble costs nothing; an
 * unanswered or failed one costs its toll in hull or water. The ark arrives if neither hull nor water runs out.
 * An empty post always fails. Pure and deterministic.
 */
public final class KennelArkVoyage {
    public static final int LEGS = 6;
    public static final int START_HULL = 10;
    public static final int START_WATER = 10;

    /** One kind of trouble per G107 post, in {@link KennelArkMuster#ROLES} order. */
    public enum Trouble {
        BOARDING_GUST("guard", 3, 0), OVERBOARD("rescue", 2, 2), DRY_CASKS("fetch", 0, 4), JAMMED_SIGNAL("come", 2, 1);

        private final String role;
        private final int hullToll;
        private final int waterToll;

        Trouble(String role, int hullToll, int waterToll) {
            this.role = role;
            this.hullToll = hullToll;
            this.waterToll = waterToll;
        }

        public String role() {
            return role;
        }

        public int hullToll() {
            return hullToll;
        }

        public int waterToll() {
            return waterToll;
        }
    }

    public record Leg(int leg, Trouble trouble, String hound, int pct, boolean answered, int hull, int water) { }

    public record Voyage(boolean arrived, List<Leg> legs, int hull, int water, String failReason) {
        public Voyage {
            legs = List.copyOf(legs);
        }
    }

    private KennelArkVoyage() { }

    /** The seeded troubles for a crossing, one per leg. */
    public static List<Trouble> storms(long seed) {
        SplittableRandom r = new SplittableRandom(seed);
        List<Trouble> out = new ArrayList<>();
        Trouble[] all = Trouble.values();
        for (int i = 0; i < LEGS; i++) {
            out.add(all[r.nextInt(all.length)]);
        }
        return out;
    }

    /** Sail the roster through the given troubles; rolls come from the seed. Stops at the leg where hull or water hits 0. */
    public static Voyage cross(KennelArkMuster.Roster roster, List<Trouble> troubles, long seed) {
        if (roster == null || troubles == null || troubles.size() > LEGS) {
            throw new IllegalArgumentException("a crossing has a roster and at most " + LEGS + " legs");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[] rolls = new int[troubles.size()];
        for (int i = 0; i < rolls.length; i++) {
            rolls[i] = r.nextInt(100);
        }
        return crossRolls(roster, troubles, rolls);
    }

    /**
     * The roll-driven rule behind {@link #cross}: one roll 0..99 per trouble, answered when below the post's odds. The
     * C++ twin {@code DaedalusKennelVoyageCore.h} (G154) replays exactly this from server rolls.
     */
    public static Voyage crossRolls(KennelArkMuster.Roster roster, List<Trouble> troubles, int[] rolls) {
        if (roster == null || troubles == null || troubles.size() > LEGS || rolls == null || rolls.length < troubles.size()) {
            throw new IllegalArgumentException("a crossing has a roster, at most " + LEGS + " legs and one roll per leg");
        }
        int hull = START_HULL;
        int water = START_WATER;
        List<Leg> legs = new ArrayList<>();
        for (int i = 0; i < troubles.size(); i++) {
            Trouble t = troubles.get(i);
            KennelArkMuster.Post post = roster.posts().stream().filter(p -> p.role().equals(t.role())).findFirst().orElse(null);
            int roll = rolls[i];
            boolean answered = post != null && roll < post.pct();
            if (!answered) {
                hull = Math.max(0, hull - t.hullToll());
                water = Math.max(0, water - t.waterToll());
            }
            legs.add(new Leg(i + 1, t, post == null ? null : post.hound(), post == null ? 0 : post.pct(), answered, hull, water));
            if (hull == 0 || water == 0) {
                return new Voyage(false, legs, hull, water, hull == 0 ? "the hull gave way" : "the casks ran dry");
            }
        }
        return new Voyage(true, legs, hull, water, null);
    }

    /** The chapter: muster at Hull Bay (G107); if the ark lifts, cross the seeded storm belt. */
    public static Voyage crossingTheStormBelt(List<KennelGrowth.Pup> hounds, long seed) {
        SplittableRandom r = new SplittableRandom(seed);
        KennelArkMuster.QuestResult lift = KennelArkMuster.musterAtHullBay(hounds, r.nextLong());
        if (!lift.complete()) {
            return new Voyage(false, List.of(), START_HULL, START_WATER, "the ark never lifted: " + lift.failReason());
        }
        return cross(lift.roster(), storms(r.nextLong()), r.nextLong());
    }
}
