// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.mill;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.PriorityQueue;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 36 of the Youtube Master Island story, "The Grain Mill" (quest {@code q_grain_mill}). The millstone grinds
 * any two sacks into one, and the work is their combined weight. {@link #least()} is the exact least total work by the
 * Huffman greedy (always grind the two lightest). Ending with one sack at that work earns credit; more work does not.
 */
public final class GrainMill {
    public static final String QUEST_ID = "q_grain_mill";

    public enum Outcome { GROUND, NOT_THERE, UNFINISHED, WELL, HEAVY, DUPLICATE, IGNORED }

    private final List<Integer> start;
    private final List<Integer> sacks;
    private final int least;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("grind", "pair", 1),
            new QuestProgress.Step("sack", "well", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int work;
    private Outcome last;

    public GrainMill(int... weights) {
        if (weights == null || weights.length < 2) {
            throw new IllegalArgumentException("at least two sacks");
        }
        start = new ArrayList<>();
        PriorityQueue<Integer> pq = new PriorityQueue<>();
        for (int w : weights) {
            if (w <= 0) {
                throw new IllegalArgumentException("sacks weigh something");
            }
            start.add(w);
            pq.add(w);
        }
        int total = 0;
        while (pq.size() > 1) {
            int s = pq.poll() + pq.poll();
            total += s;
            pq.add(s);
        }
        least = total;
        sacks = new ArrayList<>(start);
    }

    /** A seeded store of 2-7 sacks weighing 1-20. */
    public static GrainMill seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x3111L);
        int[] w = new int[2 + rng.nextInt(6)];
        for (int i = 0; i < w.length; i++) {
            w[i] = 1 + rng.nextInt(20);
        }
        return new GrainMill(w);
    }

    /** The least total work to grind every sack into one. */
    public int least() {
        return least;
    }

    /** The sacks still to grind, in store order (a ground pair's sack goes at the end). */
    public List<Integer> sacks() {
        return List.copyOf(sacks);
    }

    public int work() {
        return work;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    private Outcome guard(String eventId) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        return events.contains(eventId) ? Outcome.DUPLICATE : null;
    }

    /** Grinds the sacks at two positions into one. */
    public Outcome grind(String eventId, int a, int b) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (a == b || a < 0 || b < 0 || a >= sacks.size() || b >= sacks.size()) {
            return Outcome.NOT_THERE;
        }
        events.add(eventId);
        int s = sacks.get(a) + sacks.get(b);
        sacks.remove(Math.max(a, b));
        sacks.remove(Math.min(a, b));
        sacks.add(s);
        work += s;
        last = Outcome.GROUND;
        quest.apply(eventId, "grind", "pair");
        return Outcome.GROUND;
    }

    /** Refills the store to grind again. */
    public void restart() {
        sacks.clear();
        sacks.addAll(start);
        work = 0;
        last = null;
    }

    /** Ties off the last sack: UNFINISHED while two or more remain, WELL at the least work, else HEAVY. */
    public Outcome sack(String eventId) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (sacks.size() > 1) {
            return Outcome.UNFINISHED;
        }
        events.add(eventId);
        last = work == least ? Outcome.WELL : Outcome.HEAVY;
        if (last == Outcome.WELL) {
            quest.apply(eventId, "sack", "well");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the flour was sacked well. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperMillLines.THANKS;
        }
        return KeeperMillLines.line(this);
    }
}
