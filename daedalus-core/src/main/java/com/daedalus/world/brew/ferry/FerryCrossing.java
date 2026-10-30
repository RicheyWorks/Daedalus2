// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.ferry;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 27 of the Youtube Master Island story, "The Ferry Crossing" (quest {@code q_ferry_crossing}). The children
 * sail from isle 0 to the inn on the last isle. Each ferry leg has a fare in shells. {@link #cheapest()} is exact
 * Dijkstra over the fare matrix; docking at the inn having paid exactly that much earns credit, paying more does not,
 * and an unreachable inn gives {@link Outcome#NO_ROUTE}.
 */
public final class FerryCrossing {
    public static final String QUEST_ID = "q_ferry_crossing";
    /** No ferry on this leg. */
    public static final int NONE = 0;

    public enum Outcome { SAILED, NO_FERRY, NOT_HOME, WELL, DEAR, NO_ROUTE, DUPLICATE, IGNORED }

    private final int[][] fare;
    private final int cheapest;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("sail", "leg", 1),
            new QuestProgress.Step("dock", "well", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int at;
    private int paid;
    private Outcome last;

    /** @param fare symmetric matrix of leg fares, {@link #NONE} where no ferry runs */
    public FerryCrossing(int[][] fare) {
        if (fare == null || fare.length < 2) {
            throw new IllegalArgumentException("need at least two isles");
        }
        int n = fare.length;
        this.fare = new int[n][];
        for (int i = 0; i < n; i++) {
            if (fare[i].length != n || fare[i][i] != NONE) {
                throw new IllegalArgumentException("square fares, none to the same isle");
            }
            for (int j = 0; j < n; j++) {
                if (fare[i][j] < 0 || fare[i][j] != fare[j][i]) {
                    throw new IllegalArgumentException("fares are non-negative and run both ways");
                }
            }
            this.fare[i] = fare[i].clone();
        }
        cheapest = dijkstra();
    }

    /** A seeded harbour of 4-7 isles, each leg running with probability one half at 1-9 shells. */
    public static FerryCrossing seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xFE77L);
        int n = 4 + rng.nextInt(4);
        int[][] f = new int[n][n];
        for (int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                if (rng.nextBoolean()) {
                    f[i][j] = 1 + rng.nextInt(9);
                    f[j][i] = f[i][j];
                }
            }
        }
        return new FerryCrossing(f);
    }

    private int dijkstra() {
        int n = fare.length;
        int[] dist = new int[n];
        boolean[] done = new boolean[n];
        Arrays.fill(dist, Integer.MAX_VALUE);
        dist[0] = 0;
        for (int k = 0; k < n; k++) {
            int u = -1;
            for (int i = 0; i < n; i++) {
                if (!done[i] && dist[i] != Integer.MAX_VALUE && (u < 0 || dist[i] < dist[u])) {
                    u = i;
                }
            }
            if (u < 0) {
                break;
            }
            done[u] = true;
            for (int v = 0; v < n; v++) {
                if (fare[u][v] != NONE && dist[u] + fare[u][v] < dist[v]) {
                    dist[v] = dist[u] + fare[u][v];
                }
            }
        }
        return dist[n - 1] == Integer.MAX_VALUE ? -1 : dist[n - 1];
    }

    public int isles() {
        return fare.length;
    }

    public int fare(int a, int b) {
        return fare[a][b];
    }

    /** The fewest shells home, or -1 when no route runs. */
    public int cheapest() {
        return cheapest;
    }

    public int at() {
        return at;
    }

    public int paid() {
        return paid;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    private Outcome guard(String eventId) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        return events.contains(eventId) ? Outcome.DUPLICATE : null;
    }

    /** Takes the ferry from the current isle to another. */
    public Outcome sail(String eventId, int to) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (to < 0 || to >= fare.length || fare[at][to] == NONE) {
            return Outcome.NO_FERRY;
        }
        events.add(eventId);
        paid += fare[at][to];
        at = to;
        last = Outcome.SAILED;
        quest.apply(eventId, "sail", "leg");
        return Outcome.SAILED;
    }

    /** Walks back to isle 0 with a fresh purse, to try the crossing again. */
    public void restart() {
        at = 0;
        paid = 0;
        last = null;
    }

    /** Docks at the inn: WELL at the cheapest fare, DEAR above it, NO_ROUTE if the inn cannot be reached. */
    public Outcome dock(String eventId) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (cheapest < 0) {
            return Outcome.NO_ROUTE;
        }
        if (at != fare.length - 1) {
            return Outcome.NOT_HOME;
        }
        events.add(eventId);
        last = paid == cheapest ? Outcome.WELL : Outcome.DEAR;
        if (last == Outcome.WELL) {
            quest.apply(eventId, "dock", "well");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once docked well. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperFerryLines.THANKS;
        }
        return KeeperFerryLines.line(this);
    }
}
