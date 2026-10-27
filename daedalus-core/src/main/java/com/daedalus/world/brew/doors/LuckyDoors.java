// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.doors;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 83 of the Youtube Master Island story, "The Lucky Doors" (quest {@code q_lucky_doors}). Doors are numbered
 * 1..doors; a door is lucky when its digits add up to {@code luck}. {@link #lucky()} counts the lucky doors by digit DP
 * (digit by digit from the left, tracking the sum so far and whether we are still pinned to {@code doors}'s digits),
 * so it works for a billion doors as fast as for ten. Naming the count earns credit; a WRONG count, or a street with
 * NO_LUCK, earns none.
 */
public final class LuckyDoors {
    public static final String QUEST_ID = "q_lucky_doors";

    public enum Outcome { RIGHT, WRONG, NO_LUCK, MALFORMED, DUPLICATE, IGNORED }

    private final long doors;
    private final int luck;
    private final long lucky;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("walk", "street", 1),
            new QuestProgress.Step("count", "doors", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private long named = -1;
    private Outcome outcome;

    /** Doors 1..doors (1..10^15) and a lucky digit sum 1..140. */
    public LuckyDoors(long doors, int luck) {
        if (doors < 1 || doors > 1_000_000_000_000_000L || luck < 1 || luck > 140) {
            throw new IllegalArgumentException("a real street and a lucky sum");
        }
        this.doors = doors;
        this.luck = luck;
        String d = Long.toString(doors);
        long[] free = new long[luck + 1];
        long pinnedSum = 0;
        for (int i = 0; i < d.length(); i++) {
            int top = d.charAt(i) - '0';
            long[] next = new long[luck + 1];
            for (int s = 0; s <= luck; s++) {
                if (free[s] != 0) {
                    for (int dig = 0; dig <= 9 && s + dig <= luck; dig++) {
                        next[s + dig] += free[s];
                    }
                }
            }
            for (int dig = 0; dig < top; dig++) {
                if (pinnedSum + dig <= luck) {
                    next[(int) pinnedSum + dig]++;
                }
            }
            pinnedSum += top;
            free = next;
        }
        lucky = free[luck] + (pinnedSum == luck ? 1 : 0);
    }

    /** Sum of the digits of x. */
    public static int digitSum(long x) {
        int s = 0;
        for (long v = x; v > 0; v /= 10) {
            s += (int) (v % 10);
        }
        return s;
    }

    /** A seeded street of 1-3000 doors and a lucky sum 1-28. */
    public static LuckyDoors seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xD005L);
        return new LuckyDoors(1 + rng.nextInt(3000), 1 + rng.nextInt(28));
    }

    public long doors() {
        return doors;
    }

    public int luck() {
        return luck;
    }

    /** Doors 1..doors whose digits add up to luck. */
    public long lucky() {
        return lucky;
    }

    public long named() {
        return named;
    }

    public Outcome last() {
        return outcome;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Walks the street: the quest's first step. */
    public void walk(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "walk", "street");
        }
    }

    /** Names how many lucky doors there are: RIGHT, WRONG, NO_LUCK or MALFORMED. */
    public Outcome count(String eventId, long guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (lucky == 0) {
            outcome = Outcome.NO_LUCK;
            return outcome;
        }
        if (guess < 0) {
            outcome = Outcome.MALFORMED;
            return outcome;
        }
        named = guess;
        outcome = guess == lucky ? Outcome.RIGHT : Outcome.WRONG;
        if (outcome == Outcome.RIGHT) {
            quest.apply(eventId, "count", "doors");
        }
        return outcome;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the lucky doors are counted. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperLuckyDoors.THANKS;
        }
        return KeeperLuckyDoors.line(this);
    }
}
