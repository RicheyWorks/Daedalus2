// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.hives;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 64 of the Youtube Master Island story, "The Lucky Hives" (quest {@code q_lucky_hives}). Hives numbered 1..n;
 * a hive is lucky if its number is prime. {@link #isLucky(int)} comes from a sieve of Eratosthenes and
 * {@link #lucky()} is the count. Naming the count earns credit; a MISCOUNT earns none.
 */
public final class LuckyHives {
    public static final String QUEST_ID = "q_lucky_hives";

    public enum Outcome { COUNTED, MISCOUNT, DUPLICATE, IGNORED }

    private final int hives;
    private final boolean[] composite;
    private final int lucky;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("visit", "hives", 1),
            new QuestProgress.Step("count", "lucky", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** 1 to 100000 hives. */
    public LuckyHives(int hives) {
        if (hives <= 0 || hives > 100_000) {
            throw new IllegalArgumentException("1 to 100000 hives");
        }
        this.hives = hives;
        composite = new boolean[hives + 1];
        composite[0] = true;
        composite[1] = true;
        for (int p = 2; (long) p * p <= hives; p++) {
            if (!composite[p]) {
                for (int m = p * p; m <= hives; m += p) {
                    composite[m] = true;
                }
            }
        }
        int c = 0;
        for (int i = 2; i <= hives; i++) {
            c += composite[i] ? 0 : 1;
        }
        lucky = c;
    }

    /** A seeded hill of 1-200 hives. */
    public static LuckyHives seeded(long seed) {
        return new LuckyHives(1 + new SplittableRandom(seed ^ 0xB1EEL).nextInt(200));
    }

    public int hives() {
        return hives;
    }

    /** Whether hive n (1..hives) is lucky. */
    public boolean isLucky(int n) {
        return !composite[n];
    }

    public int lucky() {
        return lucky;
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

    /** Visits the hives: the quest's first step. */
    public void visit(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "visit", "hives");
        }
    }

    /** Names the count of lucky hives: COUNTED if right, else MISCOUNT. */
    public Outcome count(String eventId, int n) {
        if (eventId == null || eventId.isBlank() || n < 0) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        named = n;
        last = n == lucky ? Outcome.COUNTED : Outcome.MISCOUNT;
        if (last == Outcome.COUNTED) {
            quest.apply(eventId, "count", "lucky");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the count is right. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperHiveLines.THANKS;
        }
        return KeeperHiveLines.line(this);
    }
}
