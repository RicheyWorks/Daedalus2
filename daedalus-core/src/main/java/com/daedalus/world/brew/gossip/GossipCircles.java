// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.gossip;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Deque;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 79 of the Youtube Master Island story, "The Gossip Circles" (quest {@code q_gossip_circles}). Islanders
 * 0..n-1 and one-way tellings {a, b} (a tells b their news); a gossip circle is a group where news from any member
 * reaches every other. {@link #circles()} counts the circles of two or more islanders, by Kosaraju's two-pass search
 * (finish order, then the reversed tellings). Naming that count earns credit; a WRONG count, or a village where every
 * islander is LONE, earns none.
 */
public final class GossipCircles {
    public static final String QUEST_ID = "q_gossip_circles";

    public enum Outcome { RIGHT, WRONG, LONE, MALFORMED, DUPLICATE, IGNORED }

    private final int islanders;
    private final List<List<Integer>> out = new ArrayList<>();
    private final List<List<Integer>> in = new ArrayList<>();
    private final int[] group;
    private final int circles;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("listen", "village", 1),
            new QuestProgress.Step("count", "circles", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** Islanders 0..n-1 and tellings {a, b} with a != b. */
    public GossipCircles(int islanders, List<int[]> tellings) {
        if (islanders <= 0 || tellings == null) {
            throw new IllegalArgumentException("at least one islander");
        }
        this.islanders = islanders;
        for (int i = 0; i < islanders; i++) {
            out.add(new ArrayList<>());
            in.add(new ArrayList<>());
        }
        for (int[] t : tellings) {
            if (t.length != 2 || t[0] < 0 || t[1] < 0 || t[0] >= islanders || t[1] >= islanders || t[0] == t[1]) {
                throw new IllegalArgumentException("a telling goes from one real islander to another");
            }
            out.get(t[0]).add(t[1]);
            in.get(t[1]).add(t[0]);
        }
        boolean[] seen = new boolean[islanders];
        Deque<Integer> order = new ArrayDeque<>();
        for (int i = 0; i < islanders; i++) {
            if (!seen[i]) {
                finish(i, seen, order);
            }
        }
        group = new int[islanders];
        Arrays.fill(group, -1);
        int groups = 0;
        int[] size = new int[islanders];
        while (!order.isEmpty()) {
            int v = order.pop();
            if (group[v] < 0) {
                size[groups] = collect(v, groups);
                groups++;
            }
        }
        int c = 0;
        for (int g = 0; g < groups; g++) {
            if (size[g] >= 2) {
                c++;
            }
        }
        circles = c;
    }

    private void finish(int u, boolean[] seen, Deque<Integer> order) {
        seen[u] = true;
        for (int v : out.get(u)) {
            if (!seen[v]) {
                finish(v, seen, order);
            }
        }
        order.push(u);
    }

    private int collect(int u, int g) {
        group[u] = g;
        int n = 1;
        for (int v : in.get(u)) {
            if (group[v] < 0) {
                n += collect(v, g);
            }
        }
        return n;
    }

    /** Whether news from a reaches b (every islander reaches themself). */
    public boolean reaches(int a, int b) {
        boolean[] seen = new boolean[islanders];
        Deque<Integer> todo = new ArrayDeque<>();
        todo.add(a);
        seen[a] = true;
        while (!todo.isEmpty()) {
            int u = todo.poll();
            for (int v : out.get(u)) {
                if (!seen[v]) {
                    seen[v] = true;
                    todo.add(v);
                }
            }
        }
        return seen[b];
    }

    /** A seeded village of 1-7 islanders and 0-9 tellings. */
    public static GossipCircles seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x6055L);
        int n = 1 + rng.nextInt(7);
        int m = n < 2 ? 0 : rng.nextInt(10);
        List<int[]> t = new ArrayList<>();
        for (int i = 0; i < m; i++) {
            int a = rng.nextInt(n);
            t.add(new int[] {a, (a + 1 + rng.nextInt(n - 1)) % n});
        }
        return new GossipCircles(n, t);
    }

    public int islanders() {
        return islanders;
    }

    /** Gossip circles of two or more islanders. */
    public int circles() {
        return circles;
    }

    /** Whether a and b share a circle. */
    public boolean sameCircle(int a, int b) {
        return group[a] == group[b];
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

    /** Listens round the village: the quest's first step. */
    public void listen(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "listen", "village");
        }
    }

    /** Names how many gossip circles there are: RIGHT, WRONG, LONE or MALFORMED. */
    public Outcome count(String eventId, int guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (circles == 0) {
            last = Outcome.LONE;
            return last;
        }
        if (guess < 0) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = guess;
        last = guess == circles ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "circles");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the circles are counted. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperGossip.THANKS;
        }
        return KeeperGossip.line(this);
    }
}
