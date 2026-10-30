// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.scales;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 63 of the Youtube Master Island story, "The Treasure Scales" (quest {@code q_treasure_scales}). Treasures of
 * given weights and a scale cap; {@link #best()} is the heaviest subset at or under the cap, by meet-in-the-middle:
 * every subset sum of each half, the second half sorted, and a binary search for each first-half sum. Loading that
 * weight earns credit; a LIGHT or OVER load earns none.
 */
public final class TreasureScales {
    public static final String QUEST_ID = "q_treasure_scales";

    public enum Outcome { BEST, LIGHT, OVER, MALFORMED, DUPLICATE, IGNORED }

    private final List<Integer> weights;
    private final long cap;
    private final long best;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("weigh", "treasures", 1),
            new QuestProgress.Step("load", "best", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private long loaded = -1;
    private Outcome last;

    /** Positive weights (at most 24) and a non-negative cap. */
    public TreasureScales(List<Integer> weights, long cap) {
        if (weights == null || weights.isEmpty() || weights.size() > 24 || cap < 0) {
            throw new IllegalArgumentException("1-24 treasures and a cap");
        }
        for (Integer w : weights) {
            if (w == null || w <= 0) {
                throw new IllegalArgumentException("a treasure has weight");
            }
        }
        this.weights = List.copyOf(weights);
        this.cap = cap;
        int h = weights.size() / 2;
        long[] left = sums(this.weights.subList(0, h));
        long[] right = sums(this.weights.subList(h, weights.size()));
        Arrays.sort(right);
        long b = 0;
        for (long l : left) {
            if (l > cap) {
                continue;
            }
            int i = Arrays.binarySearch(right, cap - l);
            int at = i >= 0 ? i : -i - 2;
            if (at >= 0) {
                b = Math.max(b, l + right[at]);
            }
        }
        best = b;
    }

    static long[] sums(List<Integer> part) {
        long[] out = new long[1 << part.size()];
        for (int i = 0; i < part.size(); i++) {
            int size = 1 << i;
            for (int m = 0; m < size; m++) {
                out[size + m] = out[m] + part.get(i);
            }
        }
        return out;
    }

    /** A seeded hoard of 1-12 treasures of weight 1-50 and a cap of 0-200. */
    public static TreasureScales seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x5CA1L);
        int n = 1 + rng.nextInt(12);
        List<Integer> w = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            w.add(1 + rng.nextInt(50));
        }
        return new TreasureScales(w, rng.nextInt(201));
    }

    public List<Integer> weights() {
        return weights;
    }

    public long cap() {
        return cap;
    }

    /** The heaviest load at or under the cap. */
    public long best() {
        return best;
    }

    public long loaded() {
        return loaded;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Weighs the treasures: the quest's first step. */
    public void weigh(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "weigh", "treasures");
        }
    }

    /** Loads treasures by index (each once): BEST, LIGHT, OVER or MALFORMED. */
    public Outcome load(String eventId, List<Integer> picks) {
        if (eventId == null || eventId.isBlank() || picks == null) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        Set<Integer> seen = new HashSet<>();
        long sum = 0;
        for (Integer p : picks) {
            if (p == null || p < 0 || p >= weights.size() || !seen.add(p)) {
                last = Outcome.MALFORMED;
                return last;
            }
            sum += weights.get(p);
        }
        loaded = sum;
        last = sum > cap ? Outcome.OVER : sum == best ? Outcome.BEST : Outcome.LIGHT;
        if (last == Outcome.BEST) {
            quest.apply(eventId, "load", "best");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the best load is on. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperScaleLines.THANKS;
        }
        return KeeperScaleLines.line(this);
    }
}
