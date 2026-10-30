// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.rites;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.PriorityQueue;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 62 of the Youtube Master Island story, "The Festival Rites" (quest {@code q_festival_rites}). Rites 0..n-1
 * with "a before b" needs; {@link #order()} is the lexicographically smallest order keeping every need, from Kahn's
 * algorithm with a min-heap. A circle of needs is {@link #tangled()}. Giving that order earns credit; an OUT_OF_ORDER
 * or NOT_FIRST order earns none.
 */
public final class FestivalRites {
    public static final String QUEST_ID = "q_festival_rites";

    public enum Outcome { FIRST, OUT_OF_ORDER, NOT_FIRST, TANGLED, MALFORMED, DUPLICATE, IGNORED }

    private final int rites;
    private final List<int[]> needs;
    private final List<Integer> order;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("read", "list", 1),
            new QuestProgress.Step("order", "first", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int[] broken = {-1, -1};
    private Outcome last;

    /** Needs {a, b}: rite a must come before rite b. */
    public FestivalRites(int rites, List<int[]> needs) {
        if (rites <= 0 || needs == null) {
            throw new IllegalArgumentException("at least one rite");
        }
        this.rites = rites;
        this.needs = new ArrayList<>();
        List<List<Integer>> after = new ArrayList<>();
        int[] waiting = new int[rites];
        for (int i = 0; i < rites; i++) {
            after.add(new ArrayList<>());
        }
        for (int[] n : needs) {
            if (n.length != 2 || n[0] < 0 || n[1] < 0 || n[0] >= rites || n[1] >= rites || n[0] == n[1]) {
                throw new IllegalArgumentException("a need joins two real rites");
            }
            this.needs.add(n.clone());
            after.get(n[0]).add(n[1]);
            waiting[n[1]]++;
        }
        PriorityQueue<Integer> ready = new PriorityQueue<>();
        for (int i = 0; i < rites; i++) {
            if (waiting[i] == 0) {
                ready.add(i);
            }
        }
        List<Integer> out = new ArrayList<>();
        while (!ready.isEmpty()) {
            int r = ready.poll();
            out.add(r);
            for (int b : after.get(r)) {
                if (--waiting[b] == 0) {
                    ready.add(b);
                }
            }
        }
        order = out.size() == rites ? List.copyOf(out) : List.of();
    }

    /** A seeded festival of 1-6 rites and 0-7 needs drawn forward over a shuffled list (never tangled). */
    public static FestivalRites seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x717EL);
        int n = 1 + rng.nextInt(6);
        int[] p = new int[n];
        for (int i = 0; i < n; i++) {
            int j = rng.nextInt(i + 1);
            p[i] = p[j];
            p[j] = i;
        }
        List<int[]> needs = new ArrayList<>();
        int m = n < 2 ? 0 : rng.nextInt(8);
        for (int i = 0; i < m; i++) {
            int a = rng.nextInt(n - 1);
            int b = a + 1 + rng.nextInt(n - 1 - a);
            needs.add(new int[] {p[a], p[b]});
        }
        return new FestivalRites(n, needs);
    }

    public int rites() {
        return rites;
    }

    /** The needs (copies). */
    public List<int[]> needs() {
        List<int[]> out = new ArrayList<>();
        for (int[] n : needs) {
            out.add(n.clone());
        }
        return out;
    }

    /** The lexicographically smallest valid order, or empty if tangled. */
    public List<Integer> order() {
        return order;
    }

    public boolean tangled() {
        return order.isEmpty();
    }

    /** The need {a, b} the last OUT_OF_ORDER answer broke. */
    public int[] broken() {
        return broken.clone();
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Reads the list: the quest's first step. */
    public void read(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "read", "list");
        }
    }

    /** Gives an order of every rite once: FIRST, OUT_OF_ORDER, NOT_FIRST, TANGLED or MALFORMED. */
    public Outcome give(String eventId, List<Integer> answer) {
        if (eventId == null || eventId.isBlank() || answer == null) {
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
        int[] pos = new int[rites];
        java.util.Arrays.fill(pos, -1);
        boolean ok = answer.size() == rites;
        for (int i = 0; ok && i < rites; i++) {
            Integer r = answer.get(i);
            ok = r != null && r >= 0 && r < rites && pos[r] < 0;
            if (ok) {
                pos[r] = i;
            }
        }
        if (!ok) {
            last = Outcome.MALFORMED;
            return last;
        }
        for (int[] n : needs) {
            if (pos[n[0]] > pos[n[1]]) {
                broken = n.clone();
                last = Outcome.OUT_OF_ORDER;
                return last;
            }
        }
        last = answer.equals(order) ? Outcome.FIRST : Outcome.NOT_FIRST;
        if (last == Outcome.FIRST) {
            quest.apply(eventId, "order", "first");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the first order is given. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperRiteLines.THANKS;
        }
        return KeeperRiteLines.line(this);
    }
}
