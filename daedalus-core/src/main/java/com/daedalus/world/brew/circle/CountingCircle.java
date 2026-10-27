// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.circle;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 70 of the Youtube Master Island story, "The Counting Circle" (quest {@code q_counting_circle}). Children
 * 0..n-1 in a circle; counting from child 0, every k-th steps out. {@link #survivor()} is the last child left, from the
 * Josephus recurrence J(1) = 0, J(m) = (J(m-1) + k) mod m. Naming that child earns credit; any other is OUT.
 */
public final class CountingCircle {
    public static final String QUEST_ID = "q_counting_circle";

    public enum Outcome { LAST, OUT, NOT_THERE, DUPLICATE, IGNORED }

    private final int children;
    private final int step;
    private final int survivor;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("gather", "circle", 1),
            new QuestProgress.Step("name", "last", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** n children and a count of k (both 1 or more). */
    public CountingCircle(int children, int step) {
        if (children <= 0 || step <= 0) {
            throw new IllegalArgumentException("children and a count");
        }
        this.children = children;
        this.step = step;
        int j = 0;
        for (int m = 2; m <= children; m++) {
            j = (j + step) % m;
        }
        survivor = j;
    }

    /** A seeded circle of 1-15 children and a count of 1-6. */
    public static CountingCircle seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xC12CL);
        return new CountingCircle(1 + rng.nextInt(15), 1 + rng.nextInt(6));
    }

    public int children() {
        return children;
    }

    public int step() {
        return step;
    }

    /** The last child left. */
    public int survivor() {
        return survivor;
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

    /** Gathers the circle: the quest's first step. */
    public void gather(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "gather", "circle");
        }
    }

    /** Names the last child: LAST or OUT. */
    public Outcome name(String eventId, int child) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (child < 0 || child >= children) {
            return Outcome.NOT_THERE;
        }
        events.add(eventId);
        named = child;
        last = child == survivor ? Outcome.LAST : Outcome.OUT;
        if (last == Outcome.LAST) {
            quest.apply(eventId, "name", "last");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the last child is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return String.format(KeeperCircleLines.THANKS, survivor);
        }
        return KeeperCircleLines.line(this);
    }
}
