// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.stage;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 97 of the Youtube Master Island story, "The Stage Bookings" (quest {@code q_stage_bookings}). Bands book the
 * one festival stage for coins. {@link #best()} is the most coins from bookings that don't overlap, by weighted interval
 * scheduling with binary search; {@link #greedy()} is the trap, always taking the band that finishes first. Naming the
 * best earns credit; a WRONG total, or an EMPTY stage, earns none.
 */
public final class StageBookings {
    public static final String QUEST_ID = "q_stage_bookings";

    public enum Outcome { RIGHT, WRONG, EMPTY, MALFORMED, DUPLICATE, IGNORED }

    private final List<List<Integer>> bookings;
    private final int best;
    private final int greedy;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("read", "bookings", 1),
            new QuestProgress.Step("count", "coins", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** Bookings [start, end, coins] with start < end and coins 1+. */
    public StageBookings(List<List<Integer>> bookings) {
        if (bookings == null || bookings.stream().anyMatch(b -> b == null || b.size() != 3
                || b.stream().anyMatch(x -> x == null) || b.get(0) < 0 || b.get(0) >= b.get(1) || b.get(2) < 1)) {
            throw new IllegalArgumentException("real bookings");
        }
        this.bookings = List.copyOf(bookings.stream().map(List::copyOf).toList());
        List<List<Integer>> byEnd = new ArrayList<>(this.bookings);
        byEnd.sort(Comparator.comparingInt(b -> b.get(1)));
        int n = byEnd.size();
        int[] dp = new int[n + 1];
        for (int i = 1; i <= n; i++) {
            List<Integer> b = byEnd.get(i - 1);
            int lo = 0;
            int hi = i - 1;
            while (lo < hi) {
                int mid = (lo + hi + 1) / 2;
                if (byEnd.get(mid - 1).get(1) <= b.get(0)) {
                    lo = mid;
                } else {
                    hi = mid - 1;
                }
            }
            dp[i] = Math.max(dp[i - 1], b.get(2) + dp[lo]);
        }
        best = dp[n];
        int g = 0;
        int free = Integer.MIN_VALUE;
        for (List<Integer> b : byEnd) {
            if (b.get(0) >= free) {
                g += b.get(2);
                free = b.get(1);
            }
        }
        greedy = g;
    }

    /** A seeded list of 0-7 bookings. */
    public static StageBookings seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x57A6L);
        int n = rng.nextInt(8);
        List<List<Integer>> b = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            int s = rng.nextInt(9);
            b.add(List.of(s, s + 1 + rng.nextInt(4), 1 + rng.nextInt(9)));
        }
        return new StageBookings(b);
    }

    public List<List<Integer>> bookings() {
        return bookings;
    }

    /** Most coins from bookings that don't overlap (weighted interval scheduling). */
    public int best() {
        return best;
    }

    /** Coins from always taking the band that finishes first: the trap. */
    public int greedy() {
        return greedy;
    }

    /** Whether nobody booked. */
    public boolean empty() {
        return bookings.isEmpty();
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

    /** Reads the bookings: the quest's first step. */
    public void read(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "read", "bookings");
        }
    }

    /** Names the answer: RIGHT, WRONG, EMPTY or MALFORMED. */
    public Outcome count(String eventId, int guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (empty()) {
            last = Outcome.EMPTY;
            return last;
        }
        if (guess < 0) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = guess;
        last = guess == best() ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "coins");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the answer is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperStageBookings.THANKS;
        }
        return KeeperStageBookings.line(this);
    }
}
