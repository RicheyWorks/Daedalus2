// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.forks;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 52 of the Youtube Master Island story, "The Stream Forks" (quest {@code q_stream_forks}). Melt streams run
 * downhill between pools numbered from the spring (0) to the sea (the last pool); water only runs to a lower pool, so
 * pool numbers are a topological order. {@link #routes()} counts the different ways from spring to sea by dynamic
 * programming in that order. Naming the count earns credit; a wrong count earns none.
 */
public final class StreamForks {
    public static final String QUEST_ID = "q_stream_forks";

    public enum Outcome { RIGHT, WRONG, DUPLICATE, IGNORED }

    private final int pools;
    private final List<int[]> streams;
    private final long routes;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("follow", "streams", 1),
            new QuestProgress.Step("count", "right", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private long named = -1;
    private Outcome last;

    /** Streams {from, to} with from below to; 2-20 pools. */
    public StreamForks(int pools, List<int[]> streams) {
        if (pools < 2 || pools > 20 || streams == null) {
            throw new IllegalArgumentException("two to twenty pools");
        }
        this.pools = pools;
        this.streams = new ArrayList<>();
        List<List<Integer>> down = new ArrayList<>();
        for (int i = 0; i < pools; i++) {
            down.add(new ArrayList<>());
        }
        for (int[] s : streams) {
            if (s.length != 2 || s[0] < 0 || s[1] >= pools || s[0] >= s[1]) {
                throw new IllegalArgumentException("water only runs downhill");
            }
            this.streams.add(s.clone());
            down.get(s[0]).add(s[1]);
        }
        long[] ways = new long[pools];
        ways[0] = 1;
        for (int p = 0; p < pools; p++) {
            for (int q : down.get(p)) {
                ways[q] += ways[p];
            }
        }
        routes = ways[pools - 1];
    }

    /** A seeded hillside of 3-9 pools, each downhill pair joined with chance 2/5. */
    public static StreamForks seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xF0C5L);
        int n = 3 + rng.nextInt(7);
        List<int[]> s = new ArrayList<>();
        for (int a = 0; a < n; a++) {
            for (int b = a + 1; b < n; b++) {
                if (rng.nextInt(5) < 2) {
                    s.add(new int[] {a, b});
                }
            }
        }
        return new StreamForks(n, s);
    }

    public int pools() {
        return pools;
    }

    /** The streams (copies). */
    public List<int[]> streams() {
        List<int[]> out = new ArrayList<>();
        for (int[] s : streams) {
            out.add(s.clone());
        }
        return out;
    }

    /** Different routes from spring to sea. */
    public long routes() {
        return routes;
    }

    public long named() {
        return named;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Follows the streams down: the quest's first step. */
    public void follow(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "follow", "streams");
        }
    }

    /** Names the number of routes: RIGHT earns credit, WRONG does not. */
    public Outcome count(String eventId, long n) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (!events.add(eventId)) {
            return Outcome.DUPLICATE;
        }
        named = n;
        last = n == routes ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "right");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the count is right. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperForkLines.THANKS;
        }
        return KeeperForkLines.line(this);
    }
}
