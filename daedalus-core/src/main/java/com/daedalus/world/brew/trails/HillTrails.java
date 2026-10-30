// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.trails;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 56 of the Youtube Master Island story, "The Hill Trails" (quest {@code q_hill_trails}). Huts on a hill
 * joined by two-way trails of given lengths; {@link #dist(int, int)} is the shortest walk between every pair, from
 * Floyd-Warshall. The player walks a route from {@link #from()} to {@link #to()}: SHORTEST earns credit, a LONG or
 * BROKEN route earns none.
 */
public final class HillTrails {
    public static final String QUEST_ID = "q_hill_trails";
    /** No walk between two huts. */
    public static final int NONE = -1;

    public enum Outcome { SHORTEST, LONG, BROKEN, DUPLICATE, IGNORED }

    private final int huts;
    private final int[][] trail;
    private final int[][] dist;
    private final int to;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("survey", "trails", 1),
            new QuestProgress.Step("walk", "shortest", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int walked = NONE;
    private Outcome last;

    /** Trails {a, b, length}; the healer walks from hut 0 to the last hut. */
    public HillTrails(int huts, List<int[]> trails) {
        if (huts < 2 || trails == null) {
            throw new IllegalArgumentException("at least two huts");
        }
        this.huts = huts;
        this.to = huts - 1;
        trail = new int[huts][huts];
        dist = new int[huts][huts];
        for (int i = 0; i < huts; i++) {
            java.util.Arrays.fill(trail[i], NONE);
            trail[i][i] = 0;
        }
        for (int[] t : trails) {
            if (t.length != 3 || t[0] < 0 || t[1] < 0 || t[0] >= huts || t[1] >= huts || t[0] == t[1] || t[2] <= 0) {
                throw new IllegalArgumentException("a trail joins two real huts and has a length");
            }
            if (trail[t[0]][t[1]] == NONE || t[2] < trail[t[0]][t[1]]) {
                trail[t[0]][t[1]] = t[2];
                trail[t[1]][t[0]] = t[2];
            }
        }
        for (int i = 0; i < huts; i++) {
            dist[i] = trail[i].clone();
        }
        for (int k = 0; k < huts; k++) {
            for (int i = 0; i < huts; i++) {
                for (int j = 0; j < huts; j++) {
                    if (dist[i][k] != NONE && dist[k][j] != NONE
                            && (dist[i][j] == NONE || dist[i][k] + dist[k][j] < dist[i][j])) {
                        dist[i][j] = dist[i][k] + dist[k][j];
                    }
                }
            }
        }
    }

    /** A seeded hill of 2-6 huts with 0-9 trails of length 1-9. */
    public static HillTrails seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x7A11L);
        int n = 2 + rng.nextInt(5);
        int m = rng.nextInt(10);
        List<int[]> t = new ArrayList<>();
        for (int i = 0; i < m; i++) {
            int a = rng.nextInt(n);
            int b = (a + 1 + rng.nextInt(n - 1)) % n;
            t.add(new int[] {a, b, 1 + rng.nextInt(9)});
        }
        return new HillTrails(n, t);
    }

    public int huts() {
        return huts;
    }

    /** The trail length between two huts, 0 for the same hut, or {@link #NONE}. */
    public int trail(int a, int b) {
        return trail[a][b];
    }

    /** The shortest walk between two huts, or {@link #NONE}. */
    public int dist(int a, int b) {
        return dist[a][b];
    }

    public int from() {
        return 0;
    }

    public int to() {
        return to;
    }

    public int walked() {
        return walked;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Surveys the trails: the quest's first step. */
    public void survey(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "survey", "trails");
        }
    }

    /** Walks a route of huts: BROKEN unless it runs from hut 0 to the last hut on trails, then SHORTEST or LONG. */
    public Outcome walk(String eventId, List<Integer> route) {
        if (eventId == null || eventId.isBlank() || route == null) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        int len = 0;
        boolean ok = route.size() >= 2 && route.get(0) == 0 && route.get(route.size() - 1) == to;
        for (int i = 0; ok && i + 1 < route.size(); i++) {
            int a = route.get(i);
            int b = route.get(i + 1);
            ok = a >= 0 && b >= 0 && a < huts && b < huts && a != b && trail[a][b] != NONE;
            len += ok ? trail[a][b] : 0;
        }
        walked = ok ? len : NONE;
        last = !ok ? Outcome.BROKEN : len == dist[0][to] ? Outcome.SHORTEST : Outcome.LONG;
        if (last == Outcome.SHORTEST) {
            quest.apply(eventId, "walk", "shortest");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the shortest walk is found. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperTrailLines.THANKS;
        }
        return KeeperTrailLines.line(this);
    }
}
