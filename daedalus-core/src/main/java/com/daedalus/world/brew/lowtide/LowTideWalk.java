// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.lowtide;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 43 of the Youtube Master Island story, "The Low Tide Walk" (quest {@code q_low_tide_walk}). The tide
 * almanac gives the water level for each hour, and crossing the flats takes {@code k} hours in a row. The danger of a
 * walk is the highest water during it. {@link #safest()} is the lowest such danger over every start hour, by a
 * sliding-window maximum on a monotonic deque. Starting at an hour with that danger earns credit; a deeper walk does not.
 */
public final class LowTideWalk {
    public static final String QUEST_ID = "q_low_tide_walk";

    public enum Outcome { SAFE, DEEP, NOT_THERE, DUPLICATE, IGNORED }

    private final int[] level;
    private final int k;
    private final int[] windowMax;
    private final int safest;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("read", "almanac", 1),
            new QuestProgress.Step("walk", "safe", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int start = -1;
    private Outcome last;

    public LowTideWalk(int k, int... level) {
        if (level == null || k <= 0 || k > level.length) {
            throw new IllegalArgumentException("the walk must fit in the almanac");
        }
        for (int h : level) {
            if (h < 0) {
                throw new IllegalArgumentException("water below the seabed");
            }
        }
        this.level = level.clone();
        this.k = k;
        int n = level.length;
        windowMax = new int[n - k + 1];
        Deque<Integer> dq = new ArrayDeque<>();
        for (int i = 0; i < n; i++) {
            while (!dq.isEmpty() && level[dq.peekLast()] <= level[i]) {
                dq.pollLast();
            }
            dq.addLast(i);
            if (dq.peekFirst() <= i - k) {
                dq.pollFirst();
            }
            if (i >= k - 1) {
                windowMax[i - k + 1] = level[dq.peekFirst()];
            }
        }
        int best = Integer.MAX_VALUE;
        for (int m : windowMax) {
            best = Math.min(best, m);
        }
        safest = best;
    }

    /** A seeded almanac of 4-16 hours, levels 0-9, with a walk of 2-4 hours. */
    public static LowTideWalk seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x71DEL);
        int[] h = new int[4 + rng.nextInt(13)];
        for (int i = 0; i < h.length; i++) {
            h[i] = rng.nextInt(10);
        }
        return new LowTideWalk(2 + rng.nextInt(3), h);
    }

    public int hours() {
        return level.length;
    }

    public int level(int hour) {
        return level[hour];
    }

    public int walkHours() {
        return k;
    }

    /** The highest water on a walk starting at {@code hour}. */
    public int danger(int hour) {
        return windowMax[hour];
    }

    /** The lowest danger of any walk. */
    public int safest() {
        return safest;
    }

    public int start() {
        return start;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Reads the tide almanac: the quest's first step. */
    public void read(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "read", "almanac");
        }
    }

    /** Sets out at {@code hour}: SAFE at the lowest danger earns credit, DEEP does not. */
    public Outcome walk(String eventId, int hour) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (hour < 0 || hour >= windowMax.length) {
            return Outcome.NOT_THERE;
        }
        events.add(eventId);
        start = hour;
        last = windowMax[hour] == safest ? Outcome.SAFE : Outcome.DEEP;
        if (last == Outcome.SAFE) {
            quest.apply(eventId, "walk", "safe");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the walk was safe. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperTideLines.THANKS;
        }
        return KeeperTideLines.line(this);
    }
}
