// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.racks;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 41 of the Youtube Master Island story, "The Smokehouse Racks" (quest {@code q_smokehouse_racks}). Sides of
 * fish of different weights hang on racks that each hold at most {@code load}. {@link #fewest()} is the exact fewest
 * racks (bin packing) by dynamic programming over subsets of sides. A hanging on that many racks earns credit; more
 * racks do not, and an overloaded rack is refused credit.
 */
public final class SmokehouseRacks {
    public static final String QUEST_ID = "q_smokehouse_racks";

    public enum Outcome { WELL, WASTEFUL, OVERLOAD, NOT_THERE, DUPLICATE, IGNORED }

    private final int[] side;
    private final int load;
    private final int fewest;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("weigh", "catch", 1),
            new QuestProgress.Step("hang", "well", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int racksUsed;
    private int overRack = -1;
    private Outcome last;

    public SmokehouseRacks(int load, int... side) {
        if (side == null || side.length == 0 || side.length > 16) {
            throw new IllegalArgumentException("one to sixteen sides");
        }
        for (int w : side) {
            if (w <= 0 || w > load) {
                throw new IllegalArgumentException("every side must fit on a rack");
            }
        }
        this.side = side.clone();
        this.load = load;
        int n = side.length;
        int full = (1 << n) - 1;
        // best[mask] = racks used * (load + 1) + weight on the open rack; smaller is better.
        long[] best = new long[1 << n];
        java.util.Arrays.fill(best, Long.MAX_VALUE);
        best[0] = (long) (load + 1);
        for (int mask = 0; mask <= full; mask++) {
            if (best[mask] == Long.MAX_VALUE) {
                continue;
            }
            long racks = best[mask] / (load + 1);
            long open = best[mask] % (load + 1);
            for (int i = 0; i < n; i++) {
                if ((mask & (1 << i)) != 0) {
                    continue;
                }
                long next = open + side[i] <= load
                        ? racks * (load + 1) + open + side[i]
                        : (racks + 1) * (load + 1) + side[i];
                int m = mask | (1 << i);
                if (next < best[m]) {
                    best[m] = next;
                }
            }
        }
        fewest = (int) (best[full] / (load + 1));
    }

    /** A seeded catch of 2-8 sides, 1-9 each, on racks holding 10. */
    public static SmokehouseRacks seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x5307L);
        int[] w = new int[2 + rng.nextInt(7)];
        for (int i = 0; i < w.length; i++) {
            w[i] = 1 + rng.nextInt(9);
        }
        return new SmokehouseRacks(10, w);
    }

    public int sides() {
        return side.length;
    }

    public int side(int i) {
        return side[i];
    }

    public int load() {
        return load;
    }

    /** The fewest racks that hold the whole catch. */
    public int fewest() {
        return fewest;
    }

    public int racksUsed() {
        return racksUsed;
    }

    /** The first overloaded rack of the last hanging, or -1. */
    public int overRack() {
        return overRack;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Weighs the catch: the quest's first step. */
    public void weigh(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "weigh", "catch");
        }
    }

    /** Hangs side i on rack {@code rackOf[i]}: OVERLOAD past the load, WELL on the fewest racks, else WASTEFUL. */
    public Outcome hang(String eventId, int... rackOf) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        int n = side.length;
        if (rackOf == null || rackOf.length != n) {
            return Outcome.NOT_THERE;
        }
        for (int r : rackOf) {
            if (r < 0 || r >= n) {
                return Outcome.NOT_THERE;
            }
        }
        events.add(eventId);
        int[] onRack = new int[n];
        for (int i = 0; i < n; i++) {
            onRack[rackOf[i]] += side[i];
        }
        racksUsed = 0;
        overRack = -1;
        for (int r = 0; r < n; r++) {
            if (onRack[r] > 0) {
                racksUsed++;
            }
            if (onRack[r] > load && overRack < 0) {
                overRack = r;
            }
        }
        if (overRack >= 0) {
            last = Outcome.OVERLOAD;
        } else {
            last = racksUsed == fewest ? Outcome.WELL : Outcome.WASTEFUL;
        }
        if (last == Outcome.WELL) {
            quest.apply(eventId, "hang", "well");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the catch hangs on the fewest racks. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperRackLines.THANKS;
        }
        return KeeperRackLines.line(this);
    }
}
