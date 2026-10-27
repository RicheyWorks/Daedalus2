// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.cargo;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.BitSet;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 102 of the Youtube Master Island story, "The Cargo Weights" (quest {@code q_cargo_weights}). The boat takes
 * any non-empty selection of crates. {@link #loads()} counts the different total loads with a bitset subset-sum DP;
 * {@link #selections()} is the trap, the number of selections. Naming the loads earns credit; a WRONG count, or an
 * EMPTY quay, earns none.
 */
public final class CargoWeights {
    public static final String QUEST_ID = "q_cargo_weights";

    public enum Outcome { RIGHT, WRONG, EMPTY, MALFORMED, DUPLICATE, IGNORED }

    private final List<Integer> crates;
    private final int loads;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("read", "crates", 1),
            new QuestProgress.Step("count", "loads", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** Crate weights, each 1+ (possibly none). */
    public CargoWeights(List<Integer> crates) {
        if (crates == null || crates.stream().anyMatch(c -> c == null || c < 1)) {
            throw new IllegalArgumentException("real crates");
        }
        this.crates = List.copyOf(crates);
        BitSet reach = new BitSet();
        reach.set(0);
        for (int w : this.crates) {
            BitSet shifted = new BitSet();
            for (int i = reach.nextSetBit(0); i >= 0; i = reach.nextSetBit(i + 1)) {
                shifted.set(i + w);
            }
            reach.or(shifted);
        }
        loads = reach.cardinality() - 1;
    }

    /** A seeded quay of 0-7 crates weighing 1-6. */
    public static CargoWeights seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xCA60L);
        int n = rng.nextInt(8);
        List<Integer> c = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            c.add(1 + rng.nextInt(6));
        }
        return new CargoWeights(c);
    }

    public List<Integer> crates() {
        return crates;
    }

    /** Different non-empty loads (bitset subset-sum DP). */
    public int loads() {
        return loads;
    }

    /** Non-empty selections of crates: the trap. */
    public int selections() {
        return (1 << crates.size()) - 1;
    }

    /** Whether the quay has no crates. */
    public boolean empty() {
        return crates.isEmpty();
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

    /** Reads the crates: the quest's first step. */
    public void read(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "read", "crates");
        }
    }

    /** Names the answer: RIGHT, WRONG, EMPTY or MALFORMED. */
    public Outcome count(String eventId, int guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (empty()) {
            last = Outcome.EMPTY;
            return last;
        }
        if (guess < 0) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = guess;
        last = guess == loads() ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "loads");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the answer is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperCargoWeights.THANKS;
        }
        return KeeperCargoWeights.line(this);
    }
}
