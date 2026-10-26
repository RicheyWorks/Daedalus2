// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;

/**
 * Kennel Isle ark chapter "The Warm Crates" (contest G180, after G147 Landfall on the Cinder Shelf). The seaworthy ark
 * comes home with the animals the rescue swimmer brought aboard, and each needs a pen of its own kind before nightfall:
 * a perch for the sky-crane, pasture for the salt goat, a warm crate for the ember fox or the ark cat (one warm crate
 * holds two), a pool for the reef otter and a burrow for the cinder hare. Pens are built from
 * {@link #STORES} planks of Kennel stores plus the driftwood left over from the Cinder Shelf repair. The plan pens the
 * cheapest animals first (rescue order breaks ties), which pens as many animals as the planks allow. Pure and
 * deterministic.
 */
public final class KennelArkPens {
    public static final int STORES = 4;

    public enum Pen {
        PERCH(2, 1), PASTURE(3, 1), WARM_CRATE(1, 2), POOL(4, 1), BURROW(1, 1);

        private final int cost;
        private final int room;

        Pen(int cost, int room) {
            this.cost = cost;
            this.room = room;
        }

        public int cost() {
            return cost;
        }

        public int room() {
            return room;
        }
    }

    /** The pen each stranded animal ({@link KennelArkLandfall#STRANDED}) needs. */
    public static final Map<String, Pen> NEEDS = Map.of("sky-crane", Pen.PERCH, "salt goat", Pen.PASTURE,
        "ember fox", Pen.WARM_CRATE, "reef otter", Pen.POOL, "cinder hare", Pen.BURROW, "ark cat", Pen.WARM_CRATE);

    public record Plan(List<String> penned, List<String> unpenned, List<Pen> built, int planksUsed, int planksLeft) {
        public Plan {
            penned = List.copyOf(penned);
            unpenned = List.copyOf(unpenned);
            built = List.copyOf(built);
        }

        public boolean allPenned() {
            return unpenned.isEmpty();
        }
    }

    public record WarmCrates(KennelArkLandfall.Chapter landing, Plan plan, boolean complete, String failReason) { }

    private KennelArkPens() { }

    public static Pen need(String animal) {
        Pen p = NEEDS.get(animal);
        if (p == null) {
            throw new IllegalArgumentException("no pen known for " + animal);
        }
        return p;
    }

    /** Driftwood left after the repair: planks fetched minus the hull they mended (repairs cap at full hull). */
    public static int spare(int arrivalHull, KennelArkLandfall.Landfall l) {
        if (l == null || arrivalHull < 0 || arrivalHull > l.hull()) {
            throw new IllegalArgumentException("spare planks need the landfall and the hull it started from");
        }
        return l.days().stream().mapToInt(KennelArkLandfall.Day::planks).sum() - (l.hull() - arrivalHull);
    }

    /** Pen the rescued animals with the plank budget: cheapest pen first, a warm crate with room is reused for free. */
    public static Plan plan(List<String> rescued, int planks) {
        if (rescued == null || planks < 0) {
            throw new IllegalArgumentException("a pen plan needs the rescued animals and a plank budget >= 0");
        }
        List<String> order = new ArrayList<>(rescued);
        order.forEach(KennelArkPens::need);
        order.sort(Comparator.comparingInt(a -> need(a).cost()));
        Map<Pen, Integer> room = new EnumMap<>(Pen.class);
        List<String> penned = new ArrayList<>();
        List<String> unpenned = new ArrayList<>();
        List<Pen> built = new ArrayList<>();
        int left = planks;
        for (String a : order) {
            Pen p = need(a);
            if (room.getOrDefault(p, 0) == 0) {
                if (p.cost() > left) {
                    unpenned.add(a);
                    continue;
                }
                left -= p.cost();
                built.add(p);
                room.merge(p, p.room(), Integer::sum);
            }
            room.merge(p, -1, Integer::sum);
            penned.add(a);
        }
        return new Plan(penned, unpenned, built, planks - left, left);
    }

    /** The chapter: G147 landfall (same seed); if the ark comes home, pen everyone it brought with stores + spare planks. */
    public static WarmCrates theWarmCrates(List<KennelGrowth.Pup> hounds, long seed) {
        KennelArkLandfall.Chapter c = KennelArkLandfall.landfallOnTheCinderShelf(hounds, seed);
        if (!c.complete()) {
            return new WarmCrates(c, null, false, "the ark never came home: " + c.failReason());
        }
        Plan p = plan(c.landfall().rescued(), STORES + spare(c.voyage().hull(), c.landfall()));
        if (c.landfall().rescued().isEmpty()) {
            return new WarmCrates(c, p, false, "no animals came aboard");
        }
        return new WarmCrates(c, p, p.allPenned(), p.allPenned() ? null : "not every animal has a pen");
    }
}
