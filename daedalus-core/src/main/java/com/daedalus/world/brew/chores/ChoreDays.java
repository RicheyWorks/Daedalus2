// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.chores;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 91 of the Youtube Master Island story, "The Chore Days" (quest {@code q_chore_days}). Festival chores have
 * "before" rules and the whole village works at once. {@link #days()} is the fewest days, the number of layers in
 * Kahn's topological sort; {@link #oneADay()} is the trap, one chore per day. Naming the days earns credit; a WRONG
 * count, or a TANGLED list whose rules loop, earns none.
 */
public final class ChoreDays {
    public static final String QUEST_ID = "q_chore_days";

    public enum Outcome { RIGHT, WRONG, TANGLED, MALFORMED, DUPLICATE, IGNORED }

    private final int chores;
    private final List<List<Integer>> rules;
    private final int days;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("read", "chores", 1),
            new QuestProgress.Step("count", "days", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** Chores 1+ and "before" rules [a, b] (chore a before chore b). */
    public ChoreDays(int chores, List<List<Integer>> rules) {
        if (chores < 1 || rules == null || rules.stream().anyMatch(r -> r == null || r.size() != 2
                || r.get(0) == null || r.get(1) == null || r.get(0) < 0 || r.get(1) < 0
                || r.get(0) >= chores || r.get(1) >= chores || r.get(0).equals(r.get(1)))) {
            throw new IllegalArgumentException("real chores and rules");
        }
        this.chores = chores;
        this.rules = List.copyOf(rules.stream().map(List::copyOf).toList());
        int[] waits = new int[chores];
        for (List<Integer> r : this.rules) {
            waits[r.get(1)]++;
        }
        List<Integer> today = new ArrayList<>();
        for (int c = 0; c < chores; c++) {
            if (waits[c] == 0) {
                today.add(c);
            }
        }
        int d = 0;
        int done = 0;
        while (!today.isEmpty()) {
            d++;
            done += today.size();
            List<Integer> next = new ArrayList<>();
            for (int c : today) {
                for (List<Integer> r : this.rules) {
                    if (r.get(0) == c && --waits[r.get(1)] == 0) {
                        next.add(r.get(1));
                    }
                }
            }
            today = next;
        }
        days = done == chores ? d : -1;
    }

    /** A seeded list of 1-5 chores and 0-5 rules. */
    public static ChoreDays seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xC40EL);
        int n = 1 + rng.nextInt(5);
        List<List<Integer>> r = new ArrayList<>();
        int k = n < 2 ? 0 : rng.nextInt(6);
        while (r.size() < k) {
            int a = rng.nextInt(n);
            int b = rng.nextInt(n);
            if (a != b) {
                r.add(List.of(a, b));
            }
        }
        return new ChoreDays(n, r);
    }

    public int chores() {
        return chores;
    }

    public List<List<Integer>> rules() {
        return rules;
    }

    /** Fewest days with everyone working at once (Kahn layers), or -1 if tangled. */
    public int days() {
        return days;
    }

    /** One chore a day: the trap. */
    public int oneADay() {
        return chores;
    }

    /** Whether the rules loop, so the chores can never be finished. */
    public boolean tangled() {
        return days < 0;
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

    /** Reads the chore list: the quest's first step. */
    public void read(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "read", "chores");
        }
    }

    /** Names the answer: RIGHT, WRONG, TANGLED or MALFORMED. */
    public Outcome count(String eventId, int guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (tangled()) {
            last = Outcome.TANGLED;
            return last;
        }
        if (guess < 0) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = guess;
        last = guess == days() ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "days");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the answer is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperChoreDays.THANKS;
        }
        return KeeperChoreDays.line(this);
    }
}
