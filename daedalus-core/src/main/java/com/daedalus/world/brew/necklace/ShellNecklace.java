// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.necklace;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 100 of the Youtube Master Island story, "The Shell Necklace" (quest {@code q_shell_necklace}). Any unbroken
 * run of shells can be cut as a bracelet. {@link #distinct()} counts the different bracelets, the distinct substrings,
 * from a suffix array (prefix doubling) and Kasai's LCP array; {@link #cuts()} is the trap, every cut. Naming the
 * distinct count earns credit; a WRONG count, or a BARE string, earns none.
 */
public final class ShellNecklace {
    public static final String QUEST_ID = "q_shell_necklace";

    public enum Outcome { RIGHT, WRONG, BARE, MALFORMED, DUPLICATE, IGNORED }

    private final String shells;
    private final int distinct;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("read", "necklace", 1),
            new QuestProgress.Step("count", "bracelets", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** Shells as letters a-z (possibly none). */
    public ShellNecklace(String shells) {
        if (shells == null || !shells.matches("[a-z]*")) {
            throw new IllegalArgumentException("real shells");
        }
        this.shells = shells;
        int n = shells.length();
        Integer[] sa = new Integer[n];
        int[] rank = new int[n];
        for (int i = 0; i < n; i++) {
            sa[i] = i;
            rank[i] = shells.charAt(i);
        }
        for (int k = 1; n > 0; k *= 2) {
            final int step = k;
            final int[] rk = rank.clone();
            Comparator<Integer> cmp = Comparator.<Integer>comparingInt(i -> rk[i])
                    .thenComparingInt(i -> i + step < n ? rk[i + step] : -1);
            Arrays.sort(sa, cmp);
            int[] nr = new int[n];
            for (int i = 1; i < n; i++) {
                nr[sa[i]] = nr[sa[i - 1]] + (cmp.compare(sa[i - 1], sa[i]) < 0 ? 1 : 0);
            }
            rank = nr;
            if (nr[sa[n - 1]] == n - 1 || step >= n) {
                break;
            }
        }
        long lcpSum = 0;
        int h = 0;
        for (int i = 0; i < n; i++) {
            if (rank[i] > 0) {
                int j = sa[rank[i] - 1];
                while (i + h < n && j + h < n && shells.charAt(i + h) == shells.charAt(j + h)) {
                    h++;
                }
                lcpSum += h;
                if (h > 0) {
                    h--;
                }
            } else {
                h = 0;
            }
        }
        distinct = (int) ((long) n * (n + 1) / 2 - lcpSum);
    }

    /** A seeded necklace of 0-10 shells from a-c. */
    public static ShellNecklace seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x5E11L);
        int n = rng.nextInt(11);
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < n; i++) {
            b.append((char) ('a' + rng.nextInt(3)));
        }
        return new ShellNecklace(b.toString());
    }

    public String shells() {
        return shells;
    }

    /** Different bracelets: distinct substrings (suffix array + LCP). */
    public int distinct() {
        return distinct;
    }

    /** Every cut: the trap. */
    public int cuts() {
        int n = shells.length();
        return n * (n + 1) / 2;
    }

    /** Whether there are no shells. */
    public boolean bare() {
        return shells.isEmpty();
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

    /** Reads the necklace: the quest's first step. */
    public void read(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "read", "necklace");
        }
    }

    /** Names the answer: RIGHT, WRONG, BARE or MALFORMED. */
    public Outcome count(String eventId, int guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (bare()) {
            last = Outcome.BARE;
            return last;
        }
        if (guess < 0) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = guess;
        last = guess == distinct() ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "bracelets");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the answer is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperShellNecklace.THANKS;
        }
        return KeeperShellNecklace.line(this);
    }
}
