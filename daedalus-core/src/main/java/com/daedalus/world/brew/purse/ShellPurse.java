// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.purse;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 88 of the Youtube Master Island story, "The Shell Purse" (quest {@code q_shell_purse}). The market takes
 * shell coins of a few distinct values, any number of each. {@link #ways()} counts the handfuls (multisets) that pay
 * {@code total} exactly, by the coin-change counting DP (coins in the outer loop); {@link #orders()} is the trap, the
 * count of ordered sequences (amount in the outer loop). Naming the ways earns credit; a WRONG count, or a price that
 * is UNPAYABLE with these shells, earns none.
 */
public final class ShellPurse {
    public static final String QUEST_ID = "q_shell_purse";

    public enum Outcome { RIGHT, WRONG, UNPAYABLE, MALFORMED, DUPLICATE, IGNORED }

    private final List<Integer> coins;
    private final int total;
    private final long ways;
    private final long orders;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("read", "coins", 1),
            new QuestProgress.Step("count", "ways", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** Distinct shell values (1+) and a price (0+). */
    public ShellPurse(List<Integer> coins, int total) {
        if (coins == null || coins.isEmpty() || total < 0 || coins.stream().anyMatch(c -> c == null || c < 1)
                || new HashSet<>(coins).size() != coins.size()) {
            throw new IllegalArgumentException("real distinct shells and a price");
        }
        this.coins = List.copyOf(coins);
        this.total = total;
        long[] w = new long[total + 1];
        w[0] = 1;
        for (int c : this.coins) {
            for (int a = c; a <= total; a++) {
                w[a] += w[a - c];
            }
        }
        ways = w[total];
        long[] o = new long[total + 1];
        o[0] = 1;
        for (int a = 1; a <= total; a++) {
            for (int c : this.coins) {
                if (c <= a) {
                    o[a] += o[a - c];
                }
            }
        }
        orders = o[total];
    }

    /** A seeded purse of 1-3 distinct values 1-5 and a price 0-10. */
    public static ShellPurse seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x5EE1L);
        int k = 1 + rng.nextInt(3);
        List<Integer> c = new ArrayList<>();
        while (c.size() < k) {
            int v = 1 + rng.nextInt(5);
            if (!c.contains(v)) {
                c.add(v);
            }
        }
        return new ShellPurse(c, rng.nextInt(11));
    }

    public List<Integer> coins() {
        return coins;
    }

    public int total() {
        return total;
    }

    /** Handfuls (order ignored) that pay the price exactly. */
    public int ways() {
        return (int) ways;
    }

    /** Ordered sequences that pay the price: the trap. */
    public int orders() {
        return (int) orders;
    }

    /** Whether no handful pays the price. */
    public boolean unpayable() {
        return ways == 0;
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

    /** Reads the shell values: the quest's first step. */
    public void read(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "read", "coins");
        }
    }

    /** Names the answer: RIGHT, WRONG, UNPAYABLE or MALFORMED. */
    public Outcome count(String eventId, int guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (unpayable()) {
            last = Outcome.UNPAYABLE;
            return last;
        }
        if (guess < 0) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = guess;
        last = guess == ways() ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "ways");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the answer is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperShellPurse.THANKS;
        }
        return KeeperShellPurse.line(this);
    }
}
