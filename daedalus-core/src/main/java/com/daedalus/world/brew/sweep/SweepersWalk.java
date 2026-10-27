// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.sweep;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 76 of the Youtube Master Island story, "The Sweeper's Walk" (quest {@code q_sweepers_walk}). Spots 0..n-1
 * and paths {a, b} (two paths may join the same spots); {@link #possible()} says whether one walk can sweep every path
 * exactly once, by Euler's rule (the paths are all connected and zero or two spots touch an odd number of paths).
 * Walking such a trail earns credit; a BROKEN walk, a walk that MISSED or repeats a path, or a yard with NO_WALK earn
 * none.
 */
public final class SweepersWalk {
    public static final String QUEST_ID = "q_sweepers_walk";

    public enum Outcome { SWEPT, BROKEN, MISSED, NO_WALK, MALFORMED, DUPLICATE, IGNORED }

    private final int spots;
    private final List<int[]> paths;
    private final boolean possible;
    private final int oddSpots;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("look", "yard", 1),
            new QuestProgress.Step("sweep", "paths", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private Outcome last;

    /** Spots 0..n-1 and paths {a, b} between two different spots; at least one path. */
    public SweepersWalk(int spots, List<int[]> paths) {
        if (spots <= 1 || paths == null || paths.isEmpty()) {
            throw new IllegalArgumentException("at least two spots and one path");
        }
        this.spots = spots;
        this.paths = new ArrayList<>();
        int[] degree = new int[spots];
        int[] parent = new int[spots];
        for (int i = 0; i < spots; i++) {
            parent[i] = i;
        }
        for (int[] p : paths) {
            if (p.length != 2 || p[0] < 0 || p[1] < 0 || p[0] >= spots || p[1] >= spots || p[0] == p[1]) {
                throw new IllegalArgumentException("a path joins two different real spots");
            }
            this.paths.add(p.clone());
            degree[p[0]]++;
            degree[p[1]]++;
            parent[root(parent, p[0])] = root(parent, p[1]);
        }
        int odd = 0;
        int groups = 0;
        for (int i = 0; i < spots; i++) {
            odd += degree[i] % 2;
            if (degree[i] > 0 && root(parent, i) == i) {
                groups++;
            }
        }
        oddSpots = odd;
        possible = groups == 1 && (odd == 0 || odd == 2);
    }

    private static int root(int[] p, int x) {
        while (p[x] != x) {
            x = p[x];
        }
        return x;
    }

    /** A seeded yard of 2-5 spots and 1-6 paths. */
    public static SweepersWalk seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x5EE9L);
        int n = 2 + rng.nextInt(4);
        int m = 1 + rng.nextInt(6);
        List<int[]> p = new ArrayList<>();
        for (int i = 0; i < m; i++) {
            int a = rng.nextInt(n);
            p.add(new int[] {a, (a + 1 + rng.nextInt(n - 1)) % n});
        }
        return new SweepersWalk(n, p);
    }

    /** Whether the walk (path indexes in order, starting from either end of the first) uses every path once, joined. */
    public boolean isTrail(List<Integer> walk) {
        if (walk == null || walk.size() != paths.size()) {
            return false;
        }
        Set<Integer> used = new HashSet<>();
        for (Integer w : walk) {
            if (w == null || w < 0 || w >= paths.size() || !used.add(w)) {
                return false;
            }
        }
        for (int start : paths.get(walk.get(0))) {
            int at = start;
            boolean ok = true;
            for (int w : walk) {
                int[] p = paths.get(w);
                if (p[0] == at) {
                    at = p[1];
                } else if (p[1] == at) {
                    at = p[0];
                } else {
                    ok = false;
                    break;
                }
            }
            if (ok) {
                return true;
            }
        }
        return false;
    }

    public int spots() {
        return spots;
    }

    public int pathCount() {
        return paths.size();
    }

    /** Spots touching an odd number of paths. */
    public int oddSpots() {
        return oddSpots;
    }

    /** Whether one walk can sweep every path exactly once. */
    public boolean possible() {
        return possible;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Looks over the yard: the quest's first step. */
    public void look(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "look", "yard");
        }
    }

    /** Sweeps paths in order: SWEPT, BROKEN (a jump between paths), MISSED (skips or repeats one), NO_WALK, MALFORMED. */
    public Outcome sweep(String eventId, List<Integer> walk) {
        if (eventId == null || eventId.isBlank() || walk == null) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (!possible) {
            last = Outcome.NO_WALK;
            return last;
        }
        for (Integer w : walk) {
            if (w == null || w < 0 || w >= paths.size()) {
                last = Outcome.MALFORMED;
                return last;
            }
        }
        last = walk.size() != paths.size() || new HashSet<>(walk).size() != walk.size() ? Outcome.MISSED
                : isTrail(walk) ? Outcome.SWEPT : Outcome.BROKEN;
        if (last == Outcome.SWEPT) {
            quest.apply(eventId, "sweep", "paths");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once every path is swept. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperSweepersWalk.THANKS;
        }
        return KeeperSweepersWalk.line(this);
    }
}
