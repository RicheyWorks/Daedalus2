// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.giftswap;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 105 of the Youtube Master Island story, "The Gift Swap" (quest {@code q_gift_swap}). Friends draw gifts by
 * lot. {@link #ways()} counts the draws where nobody gets their own gift, by the derangement recurrence
 * D(n) = (n - 1)(D(n - 1) + D(n - 2)); {@link #allButOne()} is the trap, every draw but the identity. Naming the ways
 * earns credit; a WRONG count, or one friend ALONE, earns none.
 */
public final class GiftSwap {
    public static final String QUEST_ID = "q_gift_swap";

    public enum Outcome { RIGHT, WRONG, ALONE, MALFORMED, DUPLICATE, IGNORED }

    private final int friends;
    private final int ways;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("read", "friends", 1),
            new QuestProgress.Step("count", "draws", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** 1-12 friends. */
    public GiftSwap(int friends) {
        if (friends < 1 || friends > 12) {
            throw new IllegalArgumentException("1 to 12 friends");
        }
        this.friends = friends;
        long prev = 1;
        long cur = 0;
        for (int k = 2; k <= friends; k++) {
            long next = (k - 1) * (cur + prev);
            prev = cur;
            cur = next;
        }
        ways = (int) cur;
    }

    /** A seeded swap of 1-7 friends. */
    public static GiftSwap seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x6F75L);
        return new GiftSwap(1 + rng.nextInt(7));
    }

    public int friends() {
        return friends;
    }

    /** Draws where nobody gets their own gift (derangements). */
    public int ways() {
        return ways;
    }

    /** Every draw but the one where all keep their own: the trap. */
    public int allButOne() {
        int f = 1;
        for (int k = 2; k <= friends; k++) {
            f *= k;
        }
        return f - 1;
    }

    /** Whether there is only one friend. */
    public boolean alone() {
        return friends == 1;
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

    /** Reads the friends: the quest's first step. */
    public void read(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "read", "friends");
        }
    }

    /** Names the answer: RIGHT, WRONG, ALONE or MALFORMED. */
    public Outcome count(String eventId, int guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (alone()) {
            last = Outcome.ALONE;
            return last;
        }
        if (guess < 0) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = guess;
        last = guess == ways() ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "draws");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the answer is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperGiftSwap.THANKS;
        }
        return KeeperGiftSwap.line(this);
    }
}
