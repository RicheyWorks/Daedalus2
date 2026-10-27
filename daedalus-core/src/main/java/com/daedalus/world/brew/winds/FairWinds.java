// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.winds;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 29 of the Youtube Master Island story, "The Fair Winds" (quest {@code q_fair_winds}). The wind almanac
 * scores each day of the season (foul days score below zero). The crew sails one unbroken run of at least one day.
 * {@link #best()} is the exact maximum-sum run by Kadane's scan; choosing a run that reaches it earns credit, a weaker
 * run does not.
 */
public final class FairWinds {
    public static final String QUEST_ID = "q_fair_winds";

    public enum Outcome { WELL, WEAK, NOT_THERE, DUPLICATE, IGNORED }

    private final int[] wind;
    private final int best;
    private final int bestFrom;
    private final int bestTo;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("read", "almanac", 1),
            new QuestProgress.Step("sail", "well", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int from = -1;
    private int to = -1;
    private Outcome last;

    public FairWinds(int[] wind) {
        if (wind == null || wind.length == 0) {
            throw new IllegalArgumentException("at least one day");
        }
        this.wind = wind.clone();
        int bestSum = wind[0];
        int bf = 0;
        int bt = 0;
        int run = 0;
        int start = 0;
        for (int i = 0; i < wind.length; i++) {
            if (run <= 0) {
                run = wind[i];
                start = i;
            } else {
                run += wind[i];
            }
            if (run > bestSum) {
                bestSum = run;
                bf = start;
                bt = i;
            }
        }
        best = bestSum;
        bestFrom = bf;
        bestTo = bt;
    }

    /** A seeded almanac of 5-14 days scoring -6 to 6. */
    public static FairWinds seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x3171DL);
        int[] w = new int[5 + rng.nextInt(10)];
        for (int i = 0; i < w.length; i++) {
            w[i] = rng.nextInt(13) - 6;
        }
        return new FairWinds(w);
    }

    public int days() {
        return wind.length;
    }

    public int wind(int day) {
        return wind[day];
    }

    /** The best total any unbroken run of at least one day can give. */
    public int best() {
        return best;
    }

    /** One best run as {from, to}, inclusive. */
    public int[] bestRun() {
        return new int[] {bestFrom, bestTo};
    }

    public int from() {
        return from;
    }

    public int to() {
        return to;
    }

    public int chosenSum() {
        int s = 0;
        for (int i = from; i >= 0 && i <= to; i++) {
            s += wind[i];
        }
        return s;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Reads the almanac aloud: the quest's first step. */
    public void read(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "read", "almanac");
        }
    }

    /** Sails days {@code a} to {@code b} inclusive: WELL at the best total, WEAK below it. */
    public Outcome sail(String eventId, int a, int b) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (a < 0 || b >= wind.length || a > b) {
            return Outcome.NOT_THERE;
        }
        events.add(eventId);
        from = a;
        to = b;
        last = chosenSum() == best ? Outcome.WELL : Outcome.WEAK;
        if (last == Outcome.WELL) {
            quest.apply(eventId, "sail", "well");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the crew sailed well. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperWindLines.THANKS;
        }
        return KeeperWindLines.line(this);
    }
}
