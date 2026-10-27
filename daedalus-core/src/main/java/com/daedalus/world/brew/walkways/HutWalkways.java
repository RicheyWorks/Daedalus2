// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.walkways;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 46 of the Youtube Master Island story, "The Hut Walkways" (quest {@code q_hut_walkways}). Stilt huts stand
 * over the marsh, and a plank walkway between any two huts costs some planks. {@link #cheapest()} is the weight of the
 * minimum spanning tree by Prim's algorithm. Laying walkways that join every hut at that cost earns credit; a dearer
 * network does not, and a network that leaves a hut cut off is BROKEN and earns none.
 */
public final class HutWalkways {
    public static final String QUEST_ID = "q_hut_walkways";

    public enum Outcome { WELL, DEAR, BROKEN, NOT_THERE, DUPLICATE, IGNORED }

    private final int[][] planks;
    private final int cheapest;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("survey", "marsh", 1),
            new QuestProgress.Step("lay", "well", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int laid = -1;
    private Outcome last;

    /** {@code planks[a][b]}: symmetric, positive off the diagonal; 2-10 huts. */
    public HutWalkways(int[][] planks) {
        if (planks == null || planks.length < 2 || planks.length > 10) {
            throw new IllegalArgumentException("two to ten huts");
        }
        int n = planks.length;
        this.planks = new int[n][];
        for (int a = 0; a < n; a++) {
            if (planks[a] == null || planks[a].length != n) {
                throw new IllegalArgumentException("a square plank table");
            }
            this.planks[a] = planks[a].clone();
        }
        for (int a = 0; a < n; a++) {
            for (int b = 0; b < n; b++) {
                if (a != b && (planks[a][b] <= 0 || planks[a][b] != planks[b][a])) {
                    throw new IllegalArgumentException("walkways cost the same both ways and at least one plank");
                }
            }
        }
        boolean[] in = new boolean[n];
        int[] near = new int[n];
        Arrays.fill(near, Integer.MAX_VALUE);
        near[0] = 0;
        int total = 0;
        for (int step = 0; step < n; step++) {
            int pick = -1;
            for (int h = 0; h < n; h++) {
                if (!in[h] && (pick < 0 || near[h] < near[pick])) {
                    pick = h;
                }
            }
            in[pick] = true;
            total += near[pick];
            for (int h = 0; h < n; h++) {
                if (!in[h]) {
                    near[h] = Math.min(near[h], this.planks[pick][h]);
                }
            }
        }
        cheapest = total;
    }

    /** A seeded marsh of 3-6 huts, walkways of 1-9 planks. */
    public static HutWalkways seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x3A1CL);
        int n = 3 + rng.nextInt(4);
        int[][] p = new int[n][n];
        for (int a = 0; a < n; a++) {
            for (int b = a + 1; b < n; b++) {
                p[a][b] = 1 + rng.nextInt(9);
                p[b][a] = p[a][b];
            }
        }
        return new HutWalkways(p);
    }

    public int huts() {
        return planks.length;
    }

    public int planks(int a, int b) {
        return planks[a][b];
    }

    /** The fewest planks for walkways joining every hut. */
    public int cheapest() {
        return cheapest;
    }

    /** Planks in the last network laid, or -1. */
    public int laid() {
        return laid;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Surveys the marsh: the quest's first step. */
    public void survey(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "survey", "marsh");
        }
    }

    /** Lays walkways as {a, b} pairs: BROKEN if a hut is cut off, WELL at the cheapest planks, else DEAR. */
    public Outcome lay(String eventId, List<int[]> walkways) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        int n = planks.length;
        if (walkways == null) {
            return Outcome.NOT_THERE;
        }
        for (int[] w : walkways) {
            if (w.length != 2 || w[0] < 0 || w[1] < 0 || w[0] >= n || w[1] >= n || w[0] == w[1]) {
                return Outcome.NOT_THERE;
            }
        }
        events.add(eventId);
        int[] parent = new int[n];
        for (int i = 0; i < n; i++) {
            parent[i] = i;
        }
        int total = 0;
        int groups = n;
        for (int[] w : walkways) {
            total += planks[w[0]][w[1]];
            int a = root(parent, w[0]);
            int b = root(parent, w[1]);
            if (a != b) {
                parent[a] = b;
                groups--;
            }
        }
        laid = total;
        if (groups > 1) {
            last = Outcome.BROKEN;
        } else {
            last = total == cheapest ? Outcome.WELL : Outcome.DEAR;
        }
        if (last == Outcome.WELL) {
            quest.apply(eventId, "lay", "well");
        }
        return last;
    }

    private static int root(int[] parent, int x) {
        while (parent[x] != x) {
            x = parent[x];
        }
        return x;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the walkways are laid well. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperWalkwayLines.THANKS;
        }
        return KeeperWalkwayLines.line(this);
    }
}
