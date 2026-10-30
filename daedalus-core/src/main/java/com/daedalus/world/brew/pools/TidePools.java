// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.pools;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 39 of the Youtube Master Island story, "The Tide Pools" (quest {@code q_tide_pools}). A rock shelf is a row
 * of unit-wide rocks of different heights. Rain fills every hollow up to the lower of the tallest rocks on either
 * side. {@link #held()} is the exact water held, by two pointers. Naming exactly that amount earns credit; any other
 * guess is a WRONG reading and earns none.
 */
public final class TidePools {
    public static final String QUEST_ID = "q_tide_pools";

    public enum Outcome { RIGHT, WRONG, IGNORED, DUPLICATE }

    private final int[] rock;
    private final int held;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("walk", "shelf", 1),
            new QuestProgress.Step("read", "right", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int guess = -1;
    private Outcome last;

    public TidePools(int... rock) {
        if (rock == null || rock.length == 0) {
            throw new IllegalArgumentException("at least one rock");
        }
        for (int h : rock) {
            if (h < 0) {
                throw new IllegalArgumentException("rocks cannot sit below the sand");
            }
        }
        this.rock = rock.clone();
        int lo = 0;
        int hi = rock.length - 1;
        int leftMax = 0;
        int rightMax = 0;
        int water = 0;
        while (lo <= hi) {
            if (leftMax <= rightMax) {
                leftMax = Math.max(leftMax, rock[lo]);
                water += leftMax - rock[lo];
                lo++;
            } else {
                rightMax = Math.max(rightMax, rock[hi]);
                water += rightMax - rock[hi];
                hi--;
            }
        }
        held = water;
    }

    /** A seeded shelf of 3-14 rocks, 0-9 high. */
    public static TidePools seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x7001L);
        int[] h = new int[3 + rng.nextInt(12)];
        for (int i = 0; i < h.length; i++) {
            h[i] = rng.nextInt(10);
        }
        return new TidePools(h);
    }

    public int rocks() {
        return rock.length;
    }

    public int rock(int i) {
        return rock[i];
    }

    /** The water the shelf holds after rain. */
    public int held() {
        return held;
    }

    public int guess() {
        return guess;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Walks the shelf: the quest's first step. */
    public void walk(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "walk", "shelf");
        }
    }

    /** Names how much water the pools hold: RIGHT earns credit, WRONG does not. */
    public Outcome read(String eventId, int water) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (!events.add(eventId)) {
            return Outcome.DUPLICATE;
        }
        guess = water;
        last = water == held ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "read", "right");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the reading is right. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperPoolLines.THANKS;
        }
        return KeeperPoolLines.line(this);
    }
}
