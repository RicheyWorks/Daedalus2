// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.applebaskets;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 106 of the Youtube Master Island story, "The Apple Baskets" (quest {@code q_apple_baskets}). Alike apples go
 * into baskets that take any number. {@link #ways()} counts the shares by stars and bars from Pascal's triangle;
 * {@link #labelled()} is the trap, treating each apple as different. Naming the ways earns credit; a WRONG count, or
 * NO_APPLES, earns none.
 */
public final class AppleBaskets {
    public static final String QUEST_ID = "q_apple_baskets";

    public enum Outcome { RIGHT, WRONG, NO_APPLES, MALFORMED, DUPLICATE, IGNORED }

    private final int apples;
    private final int baskets;
    private final int ways;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("read", "harvest", 1),
            new QuestProgress.Step("count", "shares", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** 0-12 apples and 1-6 baskets. */
    public AppleBaskets(int apples, int baskets) {
        if (apples < 0 || apples > 12 || baskets < 1 || baskets > 6) {
            throw new IllegalArgumentException("0-12 apples and 1-6 baskets");
        }
        this.apples = apples;
        this.baskets = baskets;
        int n = apples + baskets - 1;
        long[][] pascal = new long[n + 1][n + 1];
        for (int i = 0; i <= n; i++) {
            pascal[i][0] = 1;
            for (int j = 1; j <= i; j++) {
                pascal[i][j] = pascal[i - 1][j - 1] + pascal[i - 1][j];
            }
        }
        ways = (int) pascal[n][baskets - 1];
    }

    /** A seeded harvest of 0-8 apples and 1-4 baskets. */
    public static AppleBaskets seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xA991L);
        return new AppleBaskets(rng.nextInt(9), 1 + rng.nextInt(4));
    }

    public int apples() {
        return apples;
    }

    public int baskets() {
        return baskets;
    }

    /** Ways to share alike apples (stars and bars). */
    public int ways() {
        return ways;
    }

    /** A basket chosen for each apple as if all were different: the trap. */
    public int labelled() {
        int t = 1;
        for (int i = 0; i < apples; i++) {
            t *= baskets;
        }
        return t;
    }

    /** Whether there are no apples. */
    public boolean noApples() {
        return apples == 0;
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

    /** Reads the harvest: the quest's first step. */
    public void read(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "read", "harvest");
        }
    }

    /** Names the answer: RIGHT, WRONG, NO_APPLES or MALFORMED. */
    public Outcome count(String eventId, int guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (noApples()) {
            last = Outcome.NO_APPLES;
            return last;
        }
        if (guess < 0) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = guess;
        last = guess == ways() ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "shares");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the answer is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperAppleBaskets.THANKS;
        }
        return KeeperAppleBaskets.line(this);
    }
}
