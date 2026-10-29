// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.catches;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 71 of the Youtube Master Island story, "The Middle Catch" (quest {@code q_middle_catch}). Fish of given
 * lengths; {@link #kth()} is the k-th smallest length (k from 1), by quickselect with a Lomuto partition, without
 * sorting the whole catch. Naming it earns credit; a WRONG length earns none.
 */
public final class MiddleCatch {
    public static final String QUEST_ID = "q_middle_catch";

    public enum Outcome { RIGHT, WRONG, DUPLICATE, IGNORED }

    private final List<Integer> lengths;
    private final int rank;
    private final int kth;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("land", "catch", 1),
            new QuestProgress.Step("name", "fish", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named;
    private Outcome last;

    /** Fish lengths and a rank 1..n. */
    public MiddleCatch(List<Integer> lengths, int rank) {
        if (lengths == null || lengths.isEmpty() || rank < 1 || rank > lengths.size()) {
            throw new IllegalArgumentException("a catch and a rank inside it");
        }
        int[] a = new int[lengths.size()];
        for (int i = 0; i < a.length; i++) {
            Integer l = lengths.get(i);
            if (l == null || l <= 0) {
                throw new IllegalArgumentException("a fish has length");
            }
            a[i] = l;
        }
        this.lengths = List.copyOf(lengths);
        this.rank = rank;
        int lo = 0;
        int hi = a.length - 1;
        int want = rank - 1;
        while (lo < hi) {
            int p = partition(a, lo, hi);
            if (p == want) {
                break;
            } else if (p < want) {
                lo = p + 1;
            } else {
                hi = p - 1;
            }
        }
        kth = a[want];
    }

    /** Lomuto partition around a[hi]; returns the pivot's final place. */
    static int partition(int[] a, int lo, int hi) {
        int pivot = a[hi];
        int i = lo;
        for (int j = lo; j < hi; j++) {
            if (a[j] < pivot) {
                int t = a[i];
                a[i] = a[j];
                a[j] = t;
                i++;
            }
        }
        int t = a[i];
        a[i] = a[hi];
        a[hi] = t;
        return i;
    }

    /** A seeded catch of 1-15 fish of length 1-20 and any rank. */
    public static MiddleCatch seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xF15BL);
        int n = 1 + rng.nextInt(15);
        List<Integer> l = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            l.add(1 + rng.nextInt(20));
        }
        return new MiddleCatch(l, 1 + rng.nextInt(n));
    }

    public List<Integer> lengths() {
        return lengths;
    }

    public int rank() {
        return rank;
    }

    /** The rank-th smallest length. */
    public int kth() {
        return kth;
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

    /** Lands the catch: the quest's first step. */
    public void land(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "land", "catch");
        }
    }

    /** Names a length: RIGHT if it is the rank-th smallest, else WRONG. */
    public Outcome name(String eventId, int length) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        named = length;
        last = length == kth ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "name", "fish");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the fish is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperCatchLines.THANKS;
        }
        return KeeperCatchLines.line(this);
    }
}
