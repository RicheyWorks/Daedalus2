// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.crews;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 40 of the Youtube Master Island story, "The Fishing Crews" (quest {@code q_fishing_crews}). Each of n crews
 * rows each of n boats in a different number of hours. {@link #fewest()} is the exact minimum-cost assignment of one
 * crew per boat, by dynamic programming over subsets of crews. A rota at that cost earns credit; a costlier one does
 * not, and a rota that leaves a boat unmanned or sends a crew twice is refused.
 */
public final class FishingCrews {
    public static final String QUEST_ID = "q_fishing_crews";

    public enum Outcome { WELL, COSTLY, CLASH, NOT_THERE, DUPLICATE, IGNORED }

    private final int[][] hours;
    private final int fewest;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("ask", "crews", 1),
            new QuestProgress.Step("rota", "well", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int cost = -1;
    private Outcome last;

    /** {@code hours[boat][crew]}: a square table, n from 1 to 12. */
    public FishingCrews(int[][] hours) {
        if (hours == null || hours.length == 0 || hours.length > 12) {
            throw new IllegalArgumentException("one to twelve boats");
        }
        int n = hours.length;
        this.hours = new int[n][];
        for (int b = 0; b < n; b++) {
            if (hours[b] == null || hours[b].length != n) {
                throw new IllegalArgumentException("one crew per boat");
            }
            for (int h : hours[b]) {
                if (h < 0) {
                    throw new IllegalArgumentException("no negative hours");
                }
            }
            this.hours[b] = hours[b].clone();
        }
        int[] dp = new int[1 << n];
        Arrays.fill(dp, Integer.MAX_VALUE);
        dp[0] = 0;
        for (int mask = 0; mask < (1 << n); mask++) {
            if (dp[mask] == Integer.MAX_VALUE) {
                continue;
            }
            int boat = Integer.bitCount(mask);
            if (boat == n) {
                continue;
            }
            for (int c = 0; c < n; c++) {
                if ((mask & (1 << c)) == 0) {
                    int next = mask | (1 << c);
                    dp[next] = Math.min(dp[next], dp[mask] + this.hours[boat][c]);
                }
            }
        }
        fewest = dp[(1 << n) - 1];
    }

    /** A seeded harbour of 2-7 boats, 1-20 hours each. */
    public static FishingCrews seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xC4E5L);
        int n = 2 + rng.nextInt(6);
        int[][] h = new int[n][n];
        for (int[] row : h) {
            for (int c = 0; c < n; c++) {
                row[c] = 1 + rng.nextInt(20);
            }
        }
        return new FishingCrews(h);
    }

    public int boats() {
        return hours.length;
    }

    public int hours(int boat, int crew) {
        return hours[boat][crew];
    }

    /** The fewest total hours for one crew per boat. */
    public int fewest() {
        return fewest;
    }

    /** The cost of the last accepted rota, or -1. */
    public int cost() {
        return cost;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Asks the crews their hours: the quest's first step. */
    public void ask(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "ask", "crews");
        }
    }

    /** Posts a rota, {@code crewOf[boat]}: CLASH if a crew rows twice, WELL at the fewest hours, else COSTLY. */
    public Outcome rota(String eventId, int... crewOf) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        int n = hours.length;
        if (crewOf == null || crewOf.length != n) {
            return Outcome.NOT_THERE;
        }
        for (int c : crewOf) {
            if (c < 0 || c >= n) {
                return Outcome.NOT_THERE;
            }
        }
        events.add(eventId);
        boolean[] used = new boolean[n];
        int total = 0;
        for (int b = 0; b < n; b++) {
            if (used[crewOf[b]]) {
                last = Outcome.CLASH;
                cost = -1;
                return last;
            }
            used[crewOf[b]] = true;
            total += hours[b][crewOf[b]];
        }
        cost = total;
        last = total == fewest ? Outcome.WELL : Outcome.COSTLY;
        if (last == Outcome.WELL) {
            quest.apply(eventId, "rota", "well");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the rota is the cheapest. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperCrewLines.THANKS;
        }
        return KeeperCrewLines.line(this);
    }
}
