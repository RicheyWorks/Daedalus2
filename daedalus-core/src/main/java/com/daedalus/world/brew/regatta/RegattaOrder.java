// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.regatta;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 103 of the Youtube Master Island story, "The Regatta Order" (quest {@code q_regatta_order}). Boats start in
 * number order and finish in a new one. {@link #swapped()} counts the pairs that swapped places, the inversions, by
 * merge sort; {@link #neighbours()} is the trap, neighbouring boats out of order. Naming the swaps earns credit; a
 * WRONG count, or a finish IN_ORDER, earns none.
 */
public final class RegattaOrder {
    public static final String QUEST_ID = "q_regatta_order";

    public enum Outcome { RIGHT, WRONG, IN_ORDER, MALFORMED, DUPLICATE, IGNORED }

    private final List<Integer> finish;
    private final int swapped;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("read", "finish", 1),
            new QuestProgress.Step("count", "swaps", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** Distinct boat numbers in finishing order (1 or more). */
    public RegattaOrder(List<Integer> finish) {
        if (finish == null || finish.isEmpty() || finish.stream().anyMatch(b -> b == null)
                || new HashSet<>(finish).size() != finish.size()) {
            throw new IllegalArgumentException("a real finish");
        }
        this.finish = List.copyOf(finish);
        int[] a = new int[finish.size()];
        for (int i = 0; i < a.length; i++) {
            a[i] = finish.get(i);
        }
        swapped = (int) sortCount(a, new int[a.length], 0, a.length);
    }

    private static long sortCount(int[] a, int[] tmp, int lo, int hi) {
        if (hi - lo < 2) {
            return 0;
        }
        int mid = (lo + hi) / 2;
        long inv = sortCount(a, tmp, lo, mid) + sortCount(a, tmp, mid, hi);
        int i = lo;
        int j = mid;
        int k = lo;
        while (i < mid || j < hi) {
            if (j >= hi || i < mid && a[i] <= a[j]) {
                tmp[k++] = a[i++];
            } else {
                inv += mid - i;
                tmp[k++] = a[j++];
            }
        }
        System.arraycopy(tmp, lo, a, lo, hi - lo);
        return inv;
    }

    /** A seeded finish of 1-8 distinct boats numbered 0-9. */
    public static RegattaOrder seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x2E6AL);
        int n = 1 + rng.nextInt(8);
        List<Integer> f = new ArrayList<>();
        while (f.size() < n) {
            int b = rng.nextInt(10);
            if (!f.contains(b)) {
                f.add(b);
            }
        }
        return new RegattaOrder(f);
    }

    public List<Integer> finish() {
        return finish;
    }

    /** Pairs of boats that swapped places (merge-sort inversions). */
    public int swapped() {
        return swapped;
    }

    /** Neighbouring boats out of order: the trap. */
    public int neighbours() {
        int d = 0;
        for (int i = 1; i < finish.size(); i++) {
            d += finish.get(i - 1) > finish.get(i) ? 1 : 0;
        }
        return d;
    }

    /** Whether the boats finished in starting order. */
    public boolean inOrder() {
        return swapped == 0;
    }

    public int named() {
        return named;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Reads the finish: the quest's first step. */
    public void read(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "read", "finish");
        }
    }

    /** Names the answer: RIGHT, WRONG, IN_ORDER or MALFORMED. */
    public Outcome count(String eventId, int guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (inOrder()) {
            last = Outcome.IN_ORDER;
            return last;
        }
        if (guess < 0) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = guess;
        last = guess == swapped() ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "swaps");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the answer is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperRegattaOrder.THANKS;
        }
        return KeeperRegattaOrder.line(this);
    }
}
