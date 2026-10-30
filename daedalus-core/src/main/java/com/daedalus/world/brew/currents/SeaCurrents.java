// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.currents;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 59 of the Youtube Master Island story, "The Sea Currents" (quest {@code q_sea_currents}). One-way currents
 * between coves cost rowing effort, and a helping current has negative cost. {@link #cost(int)} is the least effort
 * from cove 0, by Bellman-Ford; a circle of currents with negative total is a {@link #whirlpool()} and the sea cannot
 * be sailed. Sailing a CHEAPEST route to the last cove earns credit; COSTLY or BROKEN routes earn none.
 */
public final class SeaCurrents {
    public static final String QUEST_ID = "q_sea_currents";
    /** No route to a cove. */
    public static final long NONE = Long.MAX_VALUE;

    public enum Outcome { CHEAPEST, COSTLY, BROKEN, WHIRLPOOL, DUPLICATE, IGNORED }

    private final int coves;
    private final Long[][] current;
    private final long[] cost;
    private final boolean whirlpool;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("chart", "currents", 1),
            new QuestProgress.Step("sail", "cheapest", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private long sailed = NONE;
    private Outcome last;

    /** One-way currents {from, to, effort}; effort may be negative. */
    public SeaCurrents(int coves, List<int[]> currents) {
        if (coves < 2 || currents == null) {
            throw new IllegalArgumentException("at least two coves");
        }
        this.coves = coves;
        current = new Long[coves][coves];
        for (int[] c : currents) {
            if (c.length != 3 || c[0] < 0 || c[1] < 0 || c[0] >= coves || c[1] >= coves || c[0] == c[1]) {
                throw new IllegalArgumentException("a current runs between two real coves");
            }
            if (current[c[0]][c[1]] == null || c[2] < current[c[0]][c[1]]) {
                current[c[0]][c[1]] = (long) c[2];
            }
        }
        cost = new long[coves];
        Arrays.fill(cost, NONE);
        cost[0] = 0;
        for (int round = 0; round < coves - 1; round++) {
            relax();
        }
        whirlpool = relax();
    }

    private boolean relax() {
        boolean changed = false;
        for (int a = 0; a < coves; a++) {
            for (int b = 0; b < coves; b++) {
                if (cost[a] != NONE && current[a][b] != null && cost[a] + current[a][b] < cost[b]) {
                    cost[b] = cost[a] + current[a][b];
                    changed = true;
                }
            }
        }
        return changed;
    }

    /** A seeded sea of 2-6 coves with 0-10 forward currents of effort -4..8 (no whirlpools). */
    public static SeaCurrents seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xC0BEL);
        int n = 2 + rng.nextInt(5);
        int m = rng.nextInt(11);
        List<int[]> c = new ArrayList<>();
        for (int i = 0; i < m; i++) {
            int a = rng.nextInt(n - 1);
            int b = a + 1 + rng.nextInt(n - 1 - a);
            c.add(new int[] {a, b, rng.nextInt(13) - 4});
        }
        return new SeaCurrents(n, c);
    }

    public int coves() {
        return coves;
    }

    /** The effort of the current a to b, or null if none runs that way. */
    public Long current(int a, int b) {
        return current[a][b];
    }

    /** The least effort from cove 0, or {@link #NONE}; meaningless if {@link #whirlpool()}. */
    public long cost(int cove) {
        return cost[cove];
    }

    public boolean whirlpool() {
        return whirlpool;
    }

    public int to() {
        return coves - 1;
    }

    public long sailed() {
        return sailed;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Charts the currents: the quest's first step. */
    public void chart(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "chart", "currents");
        }
    }

    /** Sails a route of coves from 0 to the last cove along currents: CHEAPEST, COSTLY or BROKEN. */
    public Outcome sail(String eventId, List<Integer> route) {
        if (eventId == null || eventId.isBlank() || route == null) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (whirlpool) {
            last = Outcome.WHIRLPOOL;
            return last;
        }
        long len = 0;
        boolean ok = route.size() >= 2 && route.get(0) == 0 && route.get(route.size() - 1) == to();
        for (int i = 0; ok && i + 1 < route.size(); i++) {
            int a = route.get(i);
            int b = route.get(i + 1);
            ok = a >= 0 && b >= 0 && a < coves && b < coves && current[a][b] != null;
            len += ok ? current[a][b] : 0;
        }
        sailed = ok ? len : NONE;
        last = !ok ? Outcome.BROKEN : len == cost[to()] ? Outcome.CHEAPEST : Outcome.COSTLY;
        if (last == Outcome.CHEAPEST) {
            quest.apply(eventId, "sail", "cheapest");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the cheapest sail is found. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperCurrentLines.THANKS;
        }
        return KeeperCurrentLines.line(this);
    }
}
