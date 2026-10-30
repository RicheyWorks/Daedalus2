// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.planks;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 96 of the Youtube Master Island story, "The Flood Planks" (quest {@code q_flood_planks}). Flood tides lift
 * stretches of dock planks. {@link #highest()} is the highest plank afterwards, from a segment tree of maxima with lazy
 * range add; {@link #allFloods()} is the trap, every flood added together. Naming the height earns credit; a WRONG
 * height, or a CALM season with no floods, earns none.
 */
public final class FloodPlanks {
    public static final String QUEST_ID = "q_flood_planks";

    public enum Outcome { RIGHT, WRONG, CALM, MALFORMED, DUPLICATE, IGNORED }

    private final int planks;
    private final List<List<Integer>> floods;
    private final long[] max;
    private final long[] lazy;
    private final int highest;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("read", "floods", 1),
            new QuestProgress.Step("count", "height", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** Planks 1+ and floods [first, last, rise] with 0 <= first <= last < planks and rise 1+. */
    public FloodPlanks(int planks, List<List<Integer>> floods) {
        if (planks < 1 || floods == null || floods.stream().anyMatch(f -> f == null || f.size() != 3
                || f.stream().anyMatch(x -> x == null) || f.get(0) < 0 || f.get(0) > f.get(1) || f.get(1) >= planks || f.get(2) < 1)) {
            throw new IllegalArgumentException("real planks and floods");
        }
        this.planks = planks;
        this.floods = List.copyOf(floods.stream().map(List::copyOf).toList());
        max = new long[4 * planks];
        lazy = new long[4 * planks];
        for (List<Integer> f : this.floods) {
            add(1, 0, planks - 1, f.get(0), f.get(1), f.get(2));
        }
        highest = (int) max[1];
    }

    private void add(int node, int lo, int hi, int from, int to, int rise) {
        if (to < lo || hi < from) {
            return;
        }
        if (from <= lo && hi <= to) {
            max[node] += rise;
            lazy[node] += rise;
            return;
        }
        int mid = (lo + hi) / 2;
        add(2 * node, lo, mid, from, to, rise);
        add(2 * node + 1, mid + 1, hi, from, to, rise);
        max[node] = lazy[node] + Math.max(max[2 * node], max[2 * node + 1]);
    }

    /** A seeded dock of 1-8 planks and 0-5 floods. */
    public static FloodPlanks seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xF100L);
        int n = 1 + rng.nextInt(8);
        int k = rng.nextInt(6);
        List<List<Integer>> f = new ArrayList<>();
        for (int i = 0; i < k; i++) {
            int a = rng.nextInt(n);
            int b = rng.nextInt(n);
            f.add(List.of(Math.min(a, b), Math.max(a, b), 1 + rng.nextInt(3)));
        }
        return new FloodPlanks(n, f);
    }

    public int planks() {
        return planks;
    }

    public List<List<Integer>> floods() {
        return floods;
    }

    /** Height of the highest plank (segment tree, lazy range add). */
    public int highest() {
        return highest;
    }

    /** Every flood added together: the trap. */
    public int allFloods() {
        return floods.stream().mapToInt(f -> f.get(2)).sum();
    }

    /** Whether there were no floods. */
    public boolean calm() {
        return floods.isEmpty();
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

    /** Reads the floods: the quest's first step. */
    public void read(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "read", "floods");
        }
    }

    /** Names the answer: RIGHT, WRONG, CALM or MALFORMED. */
    public Outcome count(String eventId, int guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (calm()) {
            last = Outcome.CALM;
            return last;
        }
        if (guess < 0) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = guess;
        last = guess == highest() ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "height");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the answer is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperFloodPlanks.THANKS;
        }
        return KeeperFloodPlanks.line(this);
    }
}
