// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.baskets;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 89 of the Youtube Master Island story, "The Twin Baskets" (quest {@code q_twin_baskets}). Each ferry trip
 * carries two baskets weighing exactly {@code load} together. {@link #pairs()} counts the unordered pairs in one pass
 * with a hash map of weights seen so far (two-sum counting); {@link #ordered()} is the trap, counting each pair both
 * ways. Naming the pairs earns credit; a WRONG count, or a dock with FEW baskets, earns none.
 */
public final class TwinBaskets {
    public static final String QUEST_ID = "q_twin_baskets";

    public enum Outcome { RIGHT, WRONG, FEW, MALFORMED, DUPLICATE, IGNORED }

    private final List<Integer> baskets;
    private final int load;
    private final int pairs;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("read", "baskets", 1),
            new QuestProgress.Step("count", "pairs", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** Basket weights (1+) and the ferry load (1+). */
    public TwinBaskets(List<Integer> baskets, int load) {
        if (baskets == null || load < 1 || baskets.stream().anyMatch(b -> b == null || b < 1)) {
            throw new IllegalArgumentException("real baskets and a load");
        }
        this.baskets = List.copyOf(baskets);
        this.load = load;
        Map<Integer, Integer> seen = new HashMap<>();
        int p = 0;
        for (int b : this.baskets) {
            p += seen.getOrDefault(load - b, 0);
            seen.merge(b, 1, Integer::sum);
        }
        pairs = p;
    }

    /** A seeded dock of 0-9 baskets weighing 1-6 and a load 2-12. */
    public static TwinBaskets seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x7B5AL);
        int n = rng.nextInt(10);
        List<Integer> b = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            b.add(1 + rng.nextInt(6));
        }
        return new TwinBaskets(b, 2 + rng.nextInt(11));
    }

    public List<Integer> baskets() {
        return baskets;
    }

    public int load() {
        return load;
    }

    /** Unordered pairs of baskets that make the load. */
    public int pairs() {
        return pairs;
    }

    /** Ordered pairs (A then B and B then A): the trap. */
    public int ordered() {
        return 2 * pairs;
    }

    /** Whether there are fewer than two baskets. */
    public boolean few() {
        return baskets.size() < 2;
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

    /** Reads the basket weights: the quest's first step. */
    public void read(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "read", "baskets");
        }
    }

    /** Names the answer: RIGHT, WRONG, FEW or MALFORMED. */
    public Outcome count(String eventId, int guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (few()) {
            last = Outcome.FEW;
            return last;
        }
        if (guess < 0) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = guess;
        last = guess == pairs() ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "pairs");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the answer is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperTwinBaskets.THANKS;
        }
        return KeeperTwinBaskets.line(this);
    }
}
