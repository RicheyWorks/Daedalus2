// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.driftwood;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 78 of the Youtube Master Island story, "The Driftwood Cuts" (quest {@code q_driftwood_cuts}). A driftwood
 * plank of length L and the shells a trader gives for a piece of each length 1..L; {@link #best()} is the most shells
 * for cutting the whole plank, by rod-cutting DP.
 * Cutting pieces that use the whole plank for that many shells earns credit; a CHEAP cut, a cut of the WRONG_LENGTH,
 * or a trader with NO_BUYERS earn none.
 */
public final class DriftwoodCuts {
    public static final String QUEST_ID = "q_driftwood_cuts";

    public enum Outcome { BEST, CHEAP, WRONG_LENGTH, NO_BUYERS, MALFORMED, DUPLICATE, IGNORED }

    private final List<Integer> price;
    private final int best;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("measure", "plank", 1),
            new QuestProgress.Step("cut", "pieces", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int earned = -1;
    private Outcome last;

    /** price.get(j - 1) is the shells for a piece of length j; the plank is price.size() long. */
    public DriftwoodCuts(List<Integer> price) {
        if (price == null || price.isEmpty()) {
            throw new IllegalArgumentException("a plank at least one long");
        }
        for (Integer p : price) {
            if (p == null || p < 0) {
                throw new IllegalArgumentException("prices are never negative");
            }
        }
        this.price = List.copyOf(price);
        int n = price.size();
        int[] dp = new int[n + 1];
        for (int i = 1; i <= n; i++) {
            for (int j = 1; j <= i; j++) {
                dp[i] = Math.max(dp[i], price.get(j - 1) + dp[i - j]);
            }
        }
        best = dp[n];
    }

    /** A seeded plank of length 1-8 with prices 0-9. */
    public static DriftwoodCuts seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xD81F7L);
        int n = 1 + rng.nextInt(8);
        List<Integer> p = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            p.add(rng.nextInt(10));
        }
        return new DriftwoodCuts(p);
    }

    public int length() {
        return price.size();
    }

    public List<Integer> prices() {
        return price;
    }

    /** Shells for these pieces (each 1..L long). */
    public int worth(List<Integer> pieces) {
        int s = 0;
        for (int p : pieces) {
            s += price.get(p - 1);
        }
        return s;
    }

    /** The most shells for the whole plank. */
    public int best() {
        return best;
    }

    public int earned() {
        return earned;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Measures the plank: the quest's first step. */
    public void measure(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "measure", "plank");
        }
    }

    /** Cuts the plank into pieces: BEST, CHEAP, WRONG_LENGTH, NO_BUYERS or MALFORMED. */
    public Outcome cut(String eventId, List<Integer> pieces) {
        if (eventId == null || eventId.isBlank() || pieces == null) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (best == 0) {
            last = Outcome.NO_BUYERS;
            return last;
        }
        int total = 0;
        for (Integer p : pieces) {
            if (p == null || p < 1 || p > price.size()) {
                last = Outcome.MALFORMED;
                return last;
            }
            total += p;
        }
        if (total != price.size()) {
            last = Outcome.WRONG_LENGTH;
            return last;
        }
        earned = worth(pieces);
        last = earned == best ? Outcome.BEST : Outcome.CHEAP;
        if (last == Outcome.BEST) {
            quest.apply(eventId, "cut", "pieces");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the best cut is made. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperDriftwood.THANKS;
        }
        return KeeperDriftwood.line(this);
    }
}
