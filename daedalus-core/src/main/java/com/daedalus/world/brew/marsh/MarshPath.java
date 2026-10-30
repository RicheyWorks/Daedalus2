// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.marsh;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.PriorityQueue;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 92 of the Youtube Master Island story, "The Marsh Path" (quest {@code q_marsh_path}). The marsh is a grid of
 * tussocks and pools. {@link #steps()} is the fewest steps from the near corner to the far corner, by A* search with
 * the Manhattan distance as heuristic; {@link #straight()} is the trap, the straight-line count. Naming the steps earns
 * credit; a WRONG count, or a marsh that leaves Keeper Oriel SUNK, earns none.
 */
public final class MarshPath {
    public static final String QUEST_ID = "q_marsh_path";

    public enum Outcome { RIGHT, WRONG, SUNK, MALFORMED, DUPLICATE, IGNORED }

    private final List<String> rows;
    private final int steps;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("read", "marsh", 1),
            new QuestProgress.Step("count", "steps", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** Marsh rows of equal length, '.' for a tussock and '~' for a pool. */
    public MarshPath(List<String> rows) {
        if (rows == null || rows.isEmpty() || rows.stream().anyMatch(r -> r == null || r.isEmpty()
                || !r.matches("[.~]+") || r.length() != rows.get(0).length())) {
            throw new IllegalArgumentException("a real marsh");
        }
        this.rows = List.copyOf(rows);
        int h = rows.size();
        int w = rows.get(0).length();
        int[] best = new int[h * w];
        Arrays.fill(best, Integer.MAX_VALUE);
        int s = -1;
        if (firm(0, 0) && firm(h - 1, w - 1)) {
            PriorityQueue<int[]> open = new PriorityQueue<>((a, b) -> Integer.compare(a[0], b[0]));
            best[0] = 0;
            open.add(new int[] {h - 1 + w - 1, 0, 0});
            int[][] moves = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
            while (!open.isEmpty()) {
                int[] cur = open.poll();
                int at = cur[2];
                if (cur[1] > best[at]) {
                    continue;
                }
                int r = at / w;
                int c = at % w;
                if (r == h - 1 && c == w - 1) {
                    s = cur[1];
                    break;
                }
                for (int[] m : moves) {
                    int nr = r + m[0];
                    int nc = c + m[1];
                    if (nr >= 0 && nc >= 0 && nr < h && nc < w && firm(nr, nc) && cur[1] + 1 < best[nr * w + nc]) {
                        best[nr * w + nc] = cur[1] + 1;
                        open.add(new int[] {cur[1] + 1 + (h - 1 - nr) + (w - 1 - nc), cur[1] + 1, nr * w + nc});
                    }
                }
            }
        }
        steps = s;
    }

    private boolean firm(int r, int c) {
        return rows.get(r).charAt(c) == '.';
    }

    /** A seeded marsh of 2-3 rows and 2-4 columns, about a quarter pools, corners firm. */
    public static MarshPath seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x3A25L);
        int h = 2 + rng.nextInt(2);
        int w = 2 + rng.nextInt(3);
        List<String> rs = new ArrayList<>();
        for (int r = 0; r < h; r++) {
            StringBuilder b = new StringBuilder();
            for (int c = 0; c < w; c++) {
                boolean corner = r == 0 && c == 0 || r == h - 1 && c == w - 1;
                b.append(!corner && rng.nextInt(4) == 0 ? '~' : '.');
            }
            rs.add(b.toString());
        }
        return new MarshPath(rs);
    }

    public List<String> rows() {
        return rows;
    }

    /** Fewest steps corner to corner (A*), or -1 if the far corner can't be reached. */
    public int steps() {
        return steps;
    }

    /** The straight-line (Manhattan) count: the trap. */
    public int straight() {
        return rows.size() - 1 + rows.get(0).length() - 1;
    }

    /** Whether the far corner can't be reached. */
    public boolean sunk() {
        return steps < 0;
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

    /** Reads the marsh: the quest's first step. */
    public void read(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "read", "marsh");
        }
    }

    /** Names the answer: RIGHT, WRONG, SUNK or MALFORMED. */
    public Outcome count(String eventId, int guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (sunk()) {
            last = Outcome.SUNK;
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
            return KeeperMarshPath.THANKS;
        }
        return KeeperMarshPath.line(this);
    }
}
