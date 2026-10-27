// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.channels;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.Deque;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 44 of the Youtube Master Island story, "The Water Channels" (quest {@code q_water_channels}). Basins are
 * joined by one-way stone channels, each carrying at most some buckets an hour, from the spring (basin 0) to the
 * cistern (the last basin). {@link #most()} is the maximum flow by Edmonds-Karp. Naming that flow earns credit; more
 * would overflow the channels and less wastes the spring, and neither earns credit.
 */
public final class WaterChannels {
    public static final String QUEST_ID = "q_water_channels";

    public enum Outcome { RIGHT, OVERFLOW, SHORT, DUPLICATE, IGNORED }

    private final int[][] cap;
    private final int most;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("trace", "channels", 1),
            new QuestProgress.Step("open", "right", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** {@code cap[a][b]}: buckets an hour from basin a to basin b; a square table of 2-10 basins. */
    public WaterChannels(int[][] cap) {
        if (cap == null || cap.length < 2 || cap.length > 10) {
            throw new IllegalArgumentException("two to ten basins");
        }
        int n = cap.length;
        this.cap = new int[n][];
        for (int a = 0; a < n; a++) {
            if (cap[a] == null || cap[a].length != n) {
                throw new IllegalArgumentException("a square channel table");
            }
            for (int c : cap[a]) {
                if (c < 0) {
                    throw new IllegalArgumentException("no negative channels");
                }
            }
            this.cap[a] = cap[a].clone();
        }
        int[][] res = new int[n][];
        for (int a = 0; a < n; a++) {
            res[a] = this.cap[a].clone();
        }
        int flow = 0;
        int[] prev = new int[n];
        while (true) {
            Arrays.fill(prev, -1);
            prev[0] = 0;
            Deque<Integer> q = new ArrayDeque<>();
            q.add(0);
            while (!q.isEmpty() && prev[n - 1] < 0) {
                int a = q.poll();
                for (int b = 0; b < n; b++) {
                    if (prev[b] < 0 && res[a][b] > 0) {
                        prev[b] = a;
                        q.add(b);
                    }
                }
            }
            if (prev[n - 1] < 0) {
                break;
            }
            int push = Integer.MAX_VALUE;
            for (int b = n - 1; b != 0; b = prev[b]) {
                push = Math.min(push, res[prev[b]][b]);
            }
            for (int b = n - 1; b != 0; b = prev[b]) {
                res[prev[b]][b] -= push;
                res[b][prev[b]] += push;
            }
            flow += push;
        }
        most = flow;
    }

    /** A seeded hillside of 3-7 basins; each ordered pair has a channel of 1-9 with chance 2/5. */
    public static WaterChannels seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xC4A7L);
        int n = 3 + rng.nextInt(5);
        int[][] c = new int[n][n];
        for (int a = 0; a < n; a++) {
            for (int b = 0; b < n; b++) {
                if (a != b && rng.nextInt(5) < 2) {
                    c[a][b] = 1 + rng.nextInt(9);
                }
            }
        }
        return new WaterChannels(c);
    }

    public int basins() {
        return cap.length;
    }

    public int channel(int a, int b) {
        return cap[a][b];
    }

    /** The most buckets an hour that reach the cistern. */
    public int most() {
        return most;
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

    /** Traces the channels down the hill: the quest's first step. */
    public void trace(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "trace", "channels");
        }
    }

    /** Opens the spring sluice to {@code buckets} an hour: RIGHT earns credit, OVERFLOW and SHORT do not. */
    public Outcome open(String eventId, int buckets) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (!events.add(eventId)) {
            return Outcome.DUPLICATE;
        }
        named = buckets;
        last = buckets == most ? Outcome.RIGHT : buckets > most ? Outcome.OVERFLOW : Outcome.SHORT;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "open", "right");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the sluice is set right. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperChannelLines.THANKS;
        }
        return KeeperChannelLines.line(this);
    }
}
