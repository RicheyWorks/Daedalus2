// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.splice;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 60 of the Youtube Master Island story, "The Rope Splicing" (quest {@code q_rope_splicing}). Rope i runs from
 * thickness {@code ends[i]} to {@code ends[i+1]}; splicing two neighbouring pieces a..k and k..b costs
 * {@code ends[a] * ends[k] * ends[b]}. {@link #least()} is the least total work, by matrix-chain interval DP. Naming it
 * earns credit; a HEAVY answer earns none.
 */
public final class RopeSplicing {
    public static final String QUEST_ID = "q_rope_splicing";

    public enum Outcome { LEAST, HEAVY, DUPLICATE, IGNORED }

    private final List<Integer> ends;
    private final long least;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("lay", "ropes", 1),
            new QuestProgress.Step("name", "least", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private long named = -1;
    private Outcome last;

    /** End thicknesses, at least two (one rope), each 1 or more. */
    public RopeSplicing(List<Integer> ends) {
        if (ends == null || ends.size() < 2) {
            throw new IllegalArgumentException("at least one rope");
        }
        for (Integer e : ends) {
            if (e == null || e <= 0) {
                throw new IllegalArgumentException("a rope end has a thickness");
            }
        }
        this.ends = List.copyOf(ends);
        int n = ends.size() - 1;
        long[][] dp = new long[n + 1][n + 1];
        for (int len = 2; len <= n; len++) {
            for (int a = 0; a + len <= n; a++) {
                int b = a + len;
                long best = Long.MAX_VALUE;
                for (int k = a + 1; k < b; k++) {
                    best = Math.min(best, dp[a][k] + dp[k][b] + (long) ends.get(a) * ends.get(k) * ends.get(b));
                }
                dp[a][b] = best;
            }
        }
        least = dp[0][n];
    }

    /** A seeded walk of 1-6 ropes with end thickness 1-9. */
    public static RopeSplicing seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x5911L);
        int n = 1 + rng.nextInt(6);
        List<Integer> e = new ArrayList<>();
        for (int i = 0; i <= n; i++) {
            e.add(1 + rng.nextInt(9));
        }
        return new RopeSplicing(e);
    }

    public List<Integer> ends() {
        return ends;
    }

    public int ropes() {
        return ends.size() - 1;
    }

    /** The least total splicing work. */
    public long least() {
        return least;
    }

    /** The work of splicing strictly left to right. */
    public long leftToRight() {
        long w = 0;
        for (int k = 1; k < ropes(); k++) {
            w += (long) ends.get(0) * ends.get(k) * ends.get(k + 1);
        }
        return w;
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

    /** Lays the ropes out: the quest's first step. */
    public void lay(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "lay", "ropes");
        }
    }

    /** Names the work: LEAST if it is the least, else HEAVY. */
    public Outcome name(String eventId, long work) {
        if (eventId == null || eventId.isBlank() || work < 0) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        named = work;
        last = work == least ? Outcome.LEAST : Outcome.HEAVY;
        if (last == Outcome.LEAST) {
            quest.apply(eventId, "name", "least");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the least work is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperSpliceLines.THANKS;
        }
        return KeeperSpliceLines.line(this);
    }
}
