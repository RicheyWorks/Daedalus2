// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.wishes;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 85 of the Youtube Master Island story, "The Lantern Wishes" (quest {@code q_lantern_wishes}). Lanterns
 * 0..n-1 are lit or dark; each villager makes a wish of two parts {a, b}, where a positive number k means "lantern k-1
 * lit" and -k means "lantern k-1 dark", and is happy if either part comes true. {@link #possible()} says whether every
 * villager can be happy at once, by 2-SAT (each wish gives two "if not this, then that" arrows; Kosaraju groups; no
 * lantern may share a group with its own opposite). Lighting lanterns that make everyone happy earns credit; an
 * UNHAPPY lighting or wishes that are IMPOSSIBLE together earn none.
 */
public final class LanternWishes {
    public static final String QUEST_ID = "q_lantern_wishes";

    public enum Outcome { GRANTED, UNHAPPY, IMPOSSIBLE, MALFORMED, DUPLICATE, IGNORED }

    private final int lanterns;
    private final List<int[]> wishes;
    private final boolean possible;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("hear", "wishes", 1),
            new QuestProgress.Step("light", "lanterns", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int unhappy = -1;
    private Outcome last;

    /** Lanterns 0..n-1 and wishes {a, b} with 1 <= |a|, |b| <= n. */
    public LanternWishes(int lanterns, List<int[]> wishes) {
        if (lanterns <= 0 || wishes == null) {
            throw new IllegalArgumentException("at least one lantern");
        }
        this.lanterns = lanterns;
        this.wishes = new ArrayList<>();
        for (int[] w : wishes) {
            if (w.length != 2 || w[0] == 0 || w[1] == 0 || Math.abs(w[0]) > lanterns || Math.abs(w[1]) > lanterns) {
                throw new IllegalArgumentException("a wish names two real lanterns");
            }
            this.wishes.add(w.clone());
        }
        int nodes = 2 * lanterns;
        List<List<Integer>> out = new ArrayList<>();
        List<List<Integer>> in = new ArrayList<>();
        for (int i = 0; i < nodes; i++) {
            out.add(new ArrayList<>());
            in.add(new ArrayList<>());
        }
        for (int[] w : this.wishes) {
            arrow(node(-w[0]), node(w[1]), out, in);
            arrow(node(-w[1]), node(w[0]), out, in);
        }
        boolean[] seen = new boolean[nodes];
        List<Integer> order = new ArrayList<>();
        for (int i = 0; i < nodes; i++) {
            if (!seen[i]) {
                finish(i, out, seen, order);
            }
        }
        int[] group = new int[nodes];
        Arrays.fill(group, -1);
        int g = 0;
        for (int k = order.size() - 1; k >= 0; k--) {
            if (group[order.get(k)] < 0) {
                collect(order.get(k), g++, in, group);
            }
        }
        boolean ok = true;
        for (int i = 0; i < lanterns; i++) {
            if (group[2 * i] == group[2 * i + 1]) {
                ok = false;
            }
        }
        possible = ok;
    }

    /** Node 2i means lantern i lit, 2i+1 dark. */
    private static int node(int lit) {
        return lit > 0 ? 2 * (lit - 1) : 2 * (-lit - 1) + 1;
    }

    private static void arrow(int a, int b, List<List<Integer>> out, List<List<Integer>> in) {
        out.get(a).add(b);
        in.get(b).add(a);
    }

    private static void finish(int u, List<List<Integer>> out, boolean[] seen, List<Integer> order) {
        seen[u] = true;
        for (int v : out.get(u)) {
            if (!seen[v]) {
                finish(v, out, seen, order);
            }
        }
        order.add(u);
    }

    private static void collect(int u, int g, List<List<Integer>> in, int[] group) {
        group[u] = g;
        for (int v : in.get(u)) {
            if (group[v] < 0) {
                collect(v, g, in, group);
            }
        }
    }

    /** Villagers left unhappy by this lighting (lit.get(i) for lantern i). */
    public int unhappyUnder(List<Boolean> lit) {
        int n = 0;
        for (int[] w : wishes) {
            if (!holds(w[0], lit) && !holds(w[1], lit)) {
                n++;
            }
        }
        return n;
    }

    private static boolean holds(int part, List<Boolean> lit) {
        return part > 0 ? lit.get(part - 1) : !lit.get(-part - 1);
    }

    /** A seeded festival of 1-6 lanterns and 0-9 wishes. */
    public static LanternWishes seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x2547L);
        int n = 1 + rng.nextInt(6);
        int m = rng.nextInt(10);
        List<int[]> w = new ArrayList<>();
        for (int i = 0; i < m; i++) {
            w.add(new int[] {part(rng, n), part(rng, n)});
        }
        return new LanternWishes(n, w);
    }

    private static int part(SplittableRandom rng, int n) {
        int k = 1 + rng.nextInt(n);
        return rng.nextBoolean() ? k : -k;
    }

    public int lanterns() {
        return lanterns;
    }

    public int wishCount() {
        return wishes.size();
    }

    /** Whether every villager can be happy at once. */
    public boolean possible() {
        return possible;
    }

    public int unhappy() {
        return unhappy;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Hears every wish: the quest's first step. */
    public void hear(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "hear", "wishes");
        }
    }

    /** Lights the lanterns: GRANTED, UNHAPPY, IMPOSSIBLE or MALFORMED. */
    public Outcome light(String eventId, List<Boolean> lit) {
        if (eventId == null || eventId.isBlank() || lit == null) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (!possible) {
            last = Outcome.IMPOSSIBLE;
            return last;
        }
        if (lit.size() != lanterns || lit.stream().anyMatch(b -> b == null)) {
            last = Outcome.MALFORMED;
            return last;
        }
        unhappy = unhappyUnder(lit);
        last = unhappy == 0 ? Outcome.GRANTED : Outcome.UNHAPPY;
        if (last == Outcome.GRANTED) {
            quest.apply(eventId, "light", "lanterns");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once every wish is granted. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperLanternWishes.THANKS;
        }
        return KeeperLanternWishes.line(this);
    }
}
