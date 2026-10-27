// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.cairns;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 104 of the Youtube Master Island story, "The Cairn Run" (quest {@code q_cairn_run}). Standing cairns are
 * noted in the order found. {@link #run()} is the longest run of consecutive numbers standing, from a hash set,
 * counting only from numbers with no predecessor; {@link #walkRun()} is the trap, numbers found one after another.
 * Naming the run earns credit; a WRONG count, or NONE found, earns none.
 */
public final class CairnRun {
    public static final String QUEST_ID = "q_cairn_run";

    public enum Outcome { RIGHT, WRONG, NONE, MALFORMED, DUPLICATE, IGNORED }

    private final List<Integer> found;
    private final int run;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("read", "cairns", 1),
            new QuestProgress.Step("count", "run", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** Cairn numbers in the order found (possibly none, repeats allowed). */
    public CairnRun(List<Integer> found) {
        if (found == null || found.stream().anyMatch(c -> c == null)) {
            throw new IllegalArgumentException("real cairns");
        }
        this.found = List.copyOf(found);
        Set<Integer> standing = new HashSet<>(this.found);
        int best = 0;
        for (int c : standing) {
            if (!standing.contains(c - 1)) {
                int len = 1;
                while (standing.contains(c + len)) {
                    len++;
                }
                best = Math.max(best, len);
            }
        }
        run = best;
    }

    /** A seeded walk of 0-8 cairn numbers 0-9. */
    public static CairnRun seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xCA12L);
        int n = rng.nextInt(9);
        List<Integer> f = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            f.add(rng.nextInt(10));
        }
        return new CairnRun(f);
    }

    public List<Integer> found() {
        return found;
    }

    /** Longest run of consecutive numbers standing (hash set). */
    public int run() {
        return run;
    }

    /** Longest stretch found one after another on the walk: the trap. */
    public int walkRun() {
        int best = found.isEmpty() ? 0 : 1;
        int len = 1;
        for (int i = 1; i < found.size(); i++) {
            len = found.get(i) == found.get(i - 1) + 1 ? len + 1 : 1;
            best = Math.max(best, len);
        }
        return best;
    }

    /** Whether no cairn was found. */
    public boolean none() {
        return found.isEmpty();
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

    /** Reads the cairns: the quest's first step. */
    public void read(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "read", "cairns");
        }
    }

    /** Names the answer: RIGHT, WRONG, NONE or MALFORMED. */
    public Outcome count(String eventId, int guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (none()) {
            last = Outcome.NONE;
            return last;
        }
        if (guess < 0) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = guess;
        last = guess == run() ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "run");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the answer is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperCairnRun.THANKS;
        }
        return KeeperCairnRun.line(this);
    }
}
