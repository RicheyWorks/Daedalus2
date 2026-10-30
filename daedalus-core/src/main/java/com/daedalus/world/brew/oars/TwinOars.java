// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.oars;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 50 of the Youtube Master Island story, "The Twin Oars" (quest {@code q_twin_oars}). A pile of oars of
 * different lengths lies in the boatyard; the new boat's oarlocks take a pair whose lengths together reach the span
 * without passing it. {@link #best()} is the largest pair total not over the span, by two pointers on the sorted
 * lengths, or -1 if no pair fits. Picking a pair with that total earns credit; a shorter pair does not, and a pair
 * OVER the span earns none.
 */
public final class TwinOars {
    public static final String QUEST_ID = "q_twin_oars";

    public enum Outcome { WELL, SHORT, OVER, NOT_THERE, DUPLICATE, IGNORED }

    private final int[] oar;
    private final int span;
    private final int best;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("sort", "pile", 1),
            new QuestProgress.Step("pick", "well", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int picked = -1;
    private Outcome last;

    public TwinOars(int span, int... oar) {
        if (oar == null || oar.length < 2 || span <= 0) {
            throw new IllegalArgumentException("at least two oars and a span");
        }
        for (int o : oar) {
            if (o <= 0) {
                throw new IllegalArgumentException("oars have length");
            }
        }
        this.oar = oar.clone();
        this.span = span;
        int[] s = oar.clone();
        Arrays.sort(s);
        int lo = 0;
        int hi = s.length - 1;
        int found = -1;
        while (lo < hi) {
            int sum = s[lo] + s[hi];
            if (sum > span) {
                hi--;
            } else {
                found = Math.max(found, sum);
                lo++;
            }
        }
        best = found;
    }

    /** A seeded pile of 2-12 oars of 1-20 and a span of 5-40. */
    public static TwinOars seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x0A25L);
        int[] o = new int[2 + rng.nextInt(11)];
        for (int i = 0; i < o.length; i++) {
            o[i] = 1 + rng.nextInt(20);
        }
        return new TwinOars(5 + rng.nextInt(36), o);
    }

    public int oars() {
        return oar.length;
    }

    public int oar(int i) {
        return oar[i];
    }

    public int span() {
        return span;
    }

    /** The largest pair total not over the span, or -1. */
    public int best() {
        return best;
    }

    public int picked() {
        return picked;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Sorts the pile by length: the quest's first step. */
    public void sort(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "sort", "pile");
        }
    }

    /** Picks oars {@code i} and {@code j}: OVER past the span, WELL at the best total, else SHORT. */
    public Outcome pick(String eventId, int i, int j) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (i < 0 || j < 0 || i >= oar.length || j >= oar.length || i == j) {
            return Outcome.NOT_THERE;
        }
        events.add(eventId);
        picked = oar[i] + oar[j];
        last = picked > span ? Outcome.OVER : picked == best ? Outcome.WELL : Outcome.SHORT;
        if (last == Outcome.WELL) {
            quest.apply(eventId, "pick", "well");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the pair is picked well. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperOarLines.THANKS;
        }
        return KeeperOarLines.line(this);
    }
}
