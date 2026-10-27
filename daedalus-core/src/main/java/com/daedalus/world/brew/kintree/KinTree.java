// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.kintree;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 94 of the Youtube Master Island story, "The Kin Tree" (quest {@code q_kin_tree}). Every islander but the
 * founder has one parent. {@link #steps()} is how many steps apart two islanders are, through their lowest common
 * ancestor found by binary lifting; {@link #viaFounder()} is the trap, climbing both to the founder. Naming the steps
 * earns credit; a WRONG count, or the SAME islander named twice, earns none.
 */
public final class KinTree {
    public static final String QUEST_ID = "q_kin_tree";

    public enum Outcome { RIGHT, WRONG, SAME, MALFORMED, DUPLICATE, IGNORED }

    private final List<Integer> parents;
    private final int a;
    private final int b;
    private final int[] depth;
    private final int steps;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("read", "tree", 1),
            new QuestProgress.Step("count", "steps", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** Parents (-1 for the founder at 0, otherwise an earlier islander) and two islanders. */
    public KinTree(List<Integer> parents, int a, int b) {
        if (parents == null || parents.isEmpty() || parents.get(0) == null || parents.get(0) != -1
                || a < 0 || b < 0 || a >= parents.size() || b >= parents.size()) {
            throw new IllegalArgumentException("a real tree and islanders");
        }
        for (int i = 1; i < parents.size(); i++) {
            Integer p = parents.get(i);
            if (p == null || p < 0 || p >= i) {
                throw new IllegalArgumentException("parents come earlier");
            }
        }
        this.parents = List.copyOf(parents);
        this.a = a;
        this.b = b;
        int n = parents.size();
        int logN = 1;
        while ((1 << logN) < n) {
            logN++;
        }
        int[][] up = new int[logN + 1][n];
        depth = new int[n];
        for (int i = 0; i < n; i++) {
            up[0][i] = i == 0 ? 0 : parents.get(i);
            depth[i] = i == 0 ? 0 : depth[parents.get(i)] + 1;
        }
        for (int k = 1; k <= logN; k++) {
            for (int i = 0; i < n; i++) {
                up[k][i] = up[k - 1][up[k - 1][i]];
            }
        }
        int x = depth[a] >= depth[b] ? a : b;
        int y = x == a ? b : a;
        int diff = depth[x] - depth[y];
        for (int k = 0; k <= logN; k++) {
            if ((diff >> k & 1) == 1) {
                x = up[k][x];
            }
        }
        if (x != y) {
            for (int k = logN; k >= 0; k--) {
                if (up[k][x] != up[k][y]) {
                    x = up[k][x];
                    y = up[k][y];
                }
            }
            x = up[0][x];
        }
        steps = depth[a] + depth[b] - 2 * depth[x];
    }

    /** A seeded tree of 1-8 islanders and two names. */
    public static KinTree seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x41A7L);
        int n = 1 + rng.nextInt(8);
        List<Integer> p = new ArrayList<>();
        p.add(-1);
        for (int i = 1; i < n; i++) {
            p.add(rng.nextInt(i));
        }
        return new KinTree(p, rng.nextInt(n), rng.nextInt(n));
    }

    public List<Integer> parents() {
        return parents;
    }

    public int a() {
        return a;
    }

    public int b() {
        return b;
    }

    /** Steps apart on the tree (via the lowest common ancestor, binary lifting). */
    public int steps() {
        return steps;
    }

    /** Both walked up to the founder: the trap. */
    public int viaFounder() {
        return depth[a] + depth[b];
    }

    /** Whether the same islander is named twice. */
    public boolean same() {
        return a == b;
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

    /** Reads the kin tree: the quest's first step. */
    public void read(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "read", "tree");
        }
    }

    /** Names the answer: RIGHT, WRONG, SAME or MALFORMED. */
    public Outcome count(String eventId, int guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (same()) {
            last = Outcome.SAME;
            return last;
        }
        if (guess < 0) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = guess;
        last = guess == steps() ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "steps");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the answer is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperKinTree.THANKS;
        }
        return KeeperKinTree.line(this);
    }
}
