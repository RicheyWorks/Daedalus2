// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.post;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 34 of the Youtube Master Island story, "The Island Post" (quest {@code q_island_post}). The post boat leaves
 * isle 0, must call at every other isle once, and row home. {@link #shortest()} is the exact shortest round trip by
 * Held-Karp dynamic programming over subsets. Coming home after the shortest round earns credit; a longer round does
 * not, and coming home with isles unvisited is {@link Outcome#MISSED}.
 */
public final class IslandPost {
    public static final String QUEST_ID = "q_island_post";

    public enum Outcome { CALLED, ALREADY, NOT_THERE, WELL, LONG, MISSED, DUPLICATE, IGNORED }

    private final int[][] dist;
    private final int shortest;
    private final boolean[] visited;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("call", "isle", 1),
            new QuestProgress.Step("home", "well", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int at;
    private int rowed;
    private Outcome last;

    /** @param dist symmetric leagues between every pair of isles, zero on the diagonal */
    public IslandPost(int[][] dist) {
        if (dist == null || dist.length < 2 || dist.length > 10) {
            throw new IllegalArgumentException("2 to 10 isles");
        }
        int n = dist.length;
        this.dist = new int[n][];
        for (int i = 0; i < n; i++) {
            if (dist[i].length != n || dist[i][i] != 0) {
                throw new IllegalArgumentException("square leagues, zero to the same isle");
            }
            for (int j = 0; j < n; j++) {
                if ((i != j && dist[i][j] <= 0) || dist[i][j] != dist[j][i]) {
                    throw new IllegalArgumentException("positive leagues, the same both ways");
                }
            }
            this.dist[i] = dist[i].clone();
        }
        visited = new boolean[n];
        visited[0] = true;
        shortest = heldKarp();
    }

    /** A seeded sea of 4-7 isles, 1-9 leagues apart. */
    public static IslandPost seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x9057L);
        int n = 4 + rng.nextInt(4);
        int[][] d = new int[n][n];
        for (int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                d[i][j] = 1 + rng.nextInt(9);
                d[j][i] = d[i][j];
            }
        }
        return new IslandPost(d);
    }

    private int heldKarp() {
        int n = dist.length;
        int full = 1 << n;
        int inf = Integer.MAX_VALUE / 2;
        int[][] dp = new int[full][n];
        for (int[] row : dp) {
            Arrays.fill(row, inf);
        }
        dp[1][0] = 0;
        for (int mask = 1; mask < full; mask += 2) {
            for (int v = 0; v < n; v++) {
                if (dp[mask][v] >= inf || (mask >> v & 1) == 0) {
                    continue;
                }
                for (int w = 1; w < n; w++) {
                    if ((mask >> w & 1) == 0) {
                        int nm = mask | 1 << w;
                        dp[nm][w] = Math.min(dp[nm][w], dp[mask][v] + dist[v][w]);
                    }
                }
            }
        }
        int best = inf;
        for (int v = 1; v < n; v++) {
            best = Math.min(best, dp[full - 1][v] + dist[v][0]);
        }
        return best;
    }

    public int isles() {
        return dist.length;
    }

    public int dist(int a, int b) {
        return dist[a][b];
    }

    /** The shortest round from isle 0 through every isle and home. */
    public int shortest() {
        return shortest;
    }

    /** Isles called at so far, counting isle 0. */
    public int called() {
        int k = 0;
        for (boolean b : visited) {
            if (b) {
                k++;
            }
        }
        return k;
    }

    public int rowed() {
        return rowed;
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

    /** Rows to an isle not yet called at and hands over its letters. */
    public Outcome call(String eventId, int isle) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (isle < 0 || isle >= dist.length) {
            return Outcome.NOT_THERE;
        }
        if (visited[isle]) {
            return Outcome.ALREADY;
        }
        events.add(eventId);
        rowed += dist[at][isle];
        at = isle;
        visited[isle] = true;
        last = Outcome.CALLED;
        quest.apply(eventId, "call", "isle");
        return Outcome.CALLED;
    }

    /** Rows home to isle 0: MISSED with isles unvisited, else WELL at the shortest or LONG. */
    public Outcome home(String eventId) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        events.add(eventId);
        if (called() < dist.length) {
            last = Outcome.MISSED;
            return last;
        }
        rowed += dist[at][0];
        at = 0;
        last = rowed == shortest ? Outcome.WELL : Outcome.LONG;
        if (last == Outcome.WELL) {
            quest.apply(eventId, "home", "well");
        }
        return last;
    }

    /** Refills the post bag for another round from isle 0. */
    public void restart() {
        Arrays.fill(visited, false);
        visited[0] = true;
        at = 0;
        rowed = 0;
        last = null;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the round came home well. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperPostLines.THANKS;
        }
        return KeeperPostLines.line(this);
    }
}
