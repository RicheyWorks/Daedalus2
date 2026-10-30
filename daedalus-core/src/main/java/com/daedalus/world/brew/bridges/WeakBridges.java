// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.bridges;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;
import java.util.TreeSet;

/**
 * Chapter 75 of the Youtube Master Island story, "The Weak Bridges" (quest {@code q_weak_bridges}). Islets 0..n-1 and
 * rope bridges {a, b} (two bridges may join the same islets); {@link #weak()} is the set of bridges whose loss would
 * cut some islet off, found by Tarjan's bridge-finding (discovery times and low links, skipping only the bridge we came
 * by). Naming exactly that set earns credit; MISSED or WRONG sets, or islets already SCATTERED, earn none.
 */
public final class WeakBridges {
    public static final String QUEST_ID = "q_weak_bridges";

    public enum Outcome { EXACT, MISSED, WRONG, SCATTERED, MALFORMED, DUPLICATE, IGNORED }

    private final int islets;
    private final List<int[]> bridges;
    private final boolean joined;
    private final Set<Integer> weak = new TreeSet<>();
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("cross", "islets", 1),
            new QuestProgress.Step("mark", "bridges", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private Outcome last;
    private int named;

    /** Islets 0..n-1 and bridges {a, b} between two different islets. */
    public WeakBridges(int islets, List<int[]> bridges) {
        if (islets <= 0 || bridges == null) {
            throw new IllegalArgumentException("at least one islet");
        }
        this.islets = islets;
        this.bridges = new ArrayList<>();
        for (int[] b : bridges) {
            if (b.length != 2 || b[0] < 0 || b[1] < 0 || b[0] >= islets || b[1] >= islets || b[0] == b[1]) {
                throw new IllegalArgumentException("a bridge joins two different real islets");
            }
            this.bridges.add(b.clone());
        }
        List<List<Integer>> adj = new ArrayList<>();
        for (int i = 0; i < islets; i++) {
            adj.add(new ArrayList<>());
        }
        for (int e = 0; e < this.bridges.size(); e++) {
            adj.get(this.bridges.get(e)[0]).add(e);
            adj.get(this.bridges.get(e)[1]).add(e);
        }
        int[] disc = new int[islets];
        int[] low = new int[islets];
        int[] clock = {0};
        tarjan(0, -1, adj, disc, low, clock);
        joined = clock[0] == islets;
    }

    private void tarjan(int u, int via, List<List<Integer>> adj, int[] disc, int[] low, int[] clock) {
        disc[u] = ++clock[0];
        low[u] = disc[u];
        for (int e : adj.get(u)) {
            if (e == via) {
                continue;
            }
            int v = bridges.get(e)[0] == u ? bridges.get(e)[1] : bridges.get(e)[0];
            if (disc[v] == 0) {
                tarjan(v, e, adj, disc, low, clock);
                low[u] = Math.min(low[u], low[v]);
                if (low[v] > disc[u]) {
                    weak.add(e);
                }
            } else {
                low[u] = Math.min(low[u], disc[v]);
            }
        }
    }

    /** Whether every islet can be reached using all bridges except the one at index skip (-1 for none). */
    public boolean connectedWithout(int skip) {
        int[] parent = new int[islets];
        for (int i = 0; i < islets; i++) {
            parent[i] = i;
        }
        int groups = islets;
        for (int e = 0; e < bridges.size(); e++) {
            if (e != skip) {
                int a = root(parent, bridges.get(e)[0]);
                int b = root(parent, bridges.get(e)[1]);
                if (a != b) {
                    parent[a] = b;
                    groups--;
                }
            }
        }
        return groups == 1;
    }

    private static int root(int[] p, int x) {
        while (p[x] != x) {
            x = p[x];
        }
        return x;
    }

    /** A seeded archipelago of 1-6 islets and 0-8 bridges. */
    public static WeakBridges seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xB81D6L);
        int n = 1 + rng.nextInt(6);
        int m = n < 2 ? 0 : rng.nextInt(9);
        List<int[]> b = new ArrayList<>();
        for (int i = 0; i < m; i++) {
            int a = rng.nextInt(n);
            b.add(new int[] {a, (a + 1 + rng.nextInt(n - 1)) % n});
        }
        return new WeakBridges(n, b);
    }

    public int islets() {
        return islets;
    }

    public int bridgeCount() {
        return bridges.size();
    }

    /** Whether every islet is reachable at all. */
    public boolean joined() {
        return joined;
    }

    /** Indexes of the weak bridges (empty when the islets are scattered). */
    public Set<Integer> weak() {
        return joined ? Set.copyOf(weak) : Set.of();
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

    /** Crosses every bridge once to look: the quest's first step. */
    public void cross(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "cross", "islets");
        }
    }

    /** Marks bridges as weak: EXACT, MISSED (only some), WRONG (marks a safe one), SCATTERED or MALFORMED. */
    public Outcome mark(String eventId, List<Integer> picks) {
        if (eventId == null || eventId.isBlank() || picks == null) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (!joined) {
            last = Outcome.SCATTERED;
            return last;
        }
        Set<Integer> chosen = new HashSet<>();
        for (Integer p : picks) {
            if (p == null || p < 0 || p >= bridges.size() || !chosen.add(p)) {
                last = Outcome.MALFORMED;
                return last;
            }
        }
        named = chosen.size();
        last = !weak.containsAll(chosen) ? Outcome.WRONG : chosen.size() == weak.size() ? Outcome.EXACT : Outcome.MISSED;
        if (last == Outcome.EXACT) {
            quest.apply(eventId, "mark", "bridges");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the weak bridges are marked. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperWeakBridges.THANKS;
        }
        return KeeperWeakBridges.line(this);
    }
}
