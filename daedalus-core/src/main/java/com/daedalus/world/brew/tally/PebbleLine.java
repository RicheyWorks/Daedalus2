// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.tally;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 66 of the Youtube Master Island story, "The Pebble Line" (quest {@code q_pebble_line}). Pebbles of given
 * sizes in a line; the fewest neighbour swaps to sort them is the number of out-of-order pairs, {@link #swaps()},
 * counted with a Fenwick (binary indexed) tree. Naming it earns credit; a MISCOUNT earns none.
 */
public final class PebbleLine {
    public static final String QUEST_ID = "q_pebble_line";
    static final int MAX_SIZE = 1000;

    public enum Outcome { COUNTED, MISCOUNT, DUPLICATE, IGNORED }

    private final List<Integer> sizes;
    private final long swaps;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("line", "pebbles", 1),
            new QuestProgress.Step("count", "swaps", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private long named = -1;
    private Outcome last;

    /** Pebble sizes 1..1000, ties allowed (equal pebbles never need swapping). */
    public PebbleLine(List<Integer> sizes) {
        if (sizes == null || sizes.isEmpty()) {
            throw new IllegalArgumentException("at least one pebble");
        }
        for (Integer s : sizes) {
            if (s == null || s <= 0 || s > MAX_SIZE) {
                throw new IllegalArgumentException("a pebble has size 1 to 1000");
            }
        }
        this.sizes = List.copyOf(sizes);
        long[] tree = new long[MAX_SIZE + 1];
        long count = 0;
        for (int i = 0; i < sizes.size(); i++) {
            int s = sizes.get(i);
            count += i - prefix(tree, s);
            for (int x = s; x <= MAX_SIZE; x += x & -x) {
                tree[x]++;
            }
        }
        swaps = count;
    }

    /** How many pebbles already placed have size at most s. */
    static long prefix(long[] tree, int s) {
        long sum = 0;
        for (int x = s; x > 0; x -= x & -x) {
            sum += tree[x];
        }
        return sum;
    }

    /** A seeded line of 1-12 pebbles of size 1-9. */
    public static PebbleLine seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x9EBBL);
        int n = 1 + rng.nextInt(12);
        List<Integer> s = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            s.add(1 + rng.nextInt(9));
        }
        return new PebbleLine(s);
    }

    public List<Integer> sizes() {
        return sizes;
    }

    /** The fewest neighbour swaps to sort the line. */
    public long swaps() {
        return swaps;
    }

    public long named() {
        return named;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Lines the pebbles up: the quest's first step. */
    public void line(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "line", "pebbles");
        }
    }

    /** Names the swap count: COUNTED if right, else MISCOUNT. */
    public Outcome count(String eventId, long n) {
        if (eventId == null || eventId.isBlank() || n < 0) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        named = n;
        last = n == swaps ? Outcome.COUNTED : Outcome.MISCOUNT;
        if (last == Outcome.COUNTED) {
            quest.apply(eventId, "count", "swaps");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the count is right. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperPebbleLines.THANKS;
        }
        return KeeperPebbleLines.line(this);
    }
}
