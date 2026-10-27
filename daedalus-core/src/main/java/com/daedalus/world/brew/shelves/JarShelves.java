// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.shelves;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 101 of the Youtube Master Island story, "The Jar Shelves" (quest {@code q_jar_shelves}). Numbered jars sit
 * out of place. {@link #swaps()} is the fewest swaps to send every jar home: jars minus the cycles of the order;
 * {@link #misplaced()} is the trap, the count of jars out of place. Naming the swaps earns credit; a WRONG count, or a
 * shelf already SORTED, earns none.
 */
public final class JarShelves {
    public static final String QUEST_ID = "q_jar_shelves";

    public enum Outcome { RIGHT, WRONG, SORTED, MALFORMED, DUPLICATE, IGNORED }

    private final List<Integer> order;
    private final int swaps;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("read", "shelf", 1),
            new QuestProgress.Step("count", "swaps", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** The shelf order: a permutation of 0..n-1 (jar k belongs in place k). */
    public JarShelves(List<Integer> order) {
        if (order == null || order.isEmpty() || order.stream().anyMatch(j -> j == null || j < 0 || j >= order.size())
                || new HashSet<>(order).size() != order.size()) {
            throw new IllegalArgumentException("a real shelf");
        }
        this.order = List.copyOf(order);
        int n = order.size();
        boolean[] seen = new boolean[n];
        int cycles = 0;
        for (int i = 0; i < n; i++) {
            if (!seen[i]) {
                cycles++;
                for (int j = i; !seen[j]; j = this.order.get(j)) {
                    seen[j] = true;
                }
            }
        }
        swaps = n - cycles;
    }

    /** A seeded shelf of 1-6 jars in random order. */
    public static JarShelves seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x5E1FL);
        int n = 1 + rng.nextInt(6);
        List<Integer> o = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            o.add(i);
        }
        for (int i = n - 1; i > 0; i--) {
            Collections.swap(o, i, rng.nextInt(i + 1));
        }
        return new JarShelves(o);
    }

    public List<Integer> order() {
        return order;
    }

    /** Fewest swaps (jars minus cycles). */
    public int swaps() {
        return swaps;
    }

    /** Jars out of place: the trap. */
    public int misplaced() {
        int m = 0;
        for (int i = 0; i < order.size(); i++) {
            m += order.get(i) == i ? 0 : 1;
        }
        return m;
    }

    /** Whether every jar is home. */
    public boolean sorted() {
        return swaps == 0;
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

    /** Reads the shelf: the quest's first step. */
    public void read(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "read", "shelf");
        }
    }

    /** Names the answer: RIGHT, WRONG, SORTED or MALFORMED. */
    public Outcome count(String eventId, int guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (sorted()) {
            last = Outcome.SORTED;
            return last;
        }
        if (guess < 0) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = guess;
        last = guess == swaps() ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "swaps");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the answer is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperJarShelves.THANKS;
        }
        return KeeperJarShelves.line(this);
    }
}
