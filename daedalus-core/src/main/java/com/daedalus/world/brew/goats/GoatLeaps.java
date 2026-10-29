// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.goats;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.Deque;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 49 of the Youtube Master Island story, "The Goat Leaps" (quest {@code q_goat_leaps}). A cliff goat leaps
 * like a chess knight across a grid of ledges, some crumbled. It starts at the top-left ledge and the stray kid waits
 * at the bottom-right. {@link #fewest()} is the fewest leaps by breadth-first search over knight moves, or -1. A leap
 * list that reaches the kid in that many leaps earns credit; a longer one does not, and one that lands on a crumbled
 * ledge FELL and earns none.
 */
public final class GoatLeaps {
    public static final String QUEST_ID = "q_goat_leaps";

    public enum Outcome { WELL, LONG, FELL, STRAY, NOT_THERE, DUPLICATE, IGNORED }

    static final int[][] LEAPS = {{1, 2}, {2, 1}, {-1, 2}, {-2, 1}, {1, -2}, {2, -1}, {-1, -2}, {-2, -1}};

    private final boolean[][] crumbled;
    private final int fewest;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("spot", "kid", 1),
            new QuestProgress.Step("leap", "well", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int used = -1;
    private Outcome last;

    /** {@code crumbled[r][c]}: a rectangular grid of 1-10 rows and columns; the two corners must stand. */
    public GoatLeaps(boolean[][] crumbled) {
        if (crumbled == null || crumbled.length == 0 || crumbled.length > 10) {
            throw new IllegalArgumentException("one to ten rows");
        }
        int cols = crumbled[0].length;
        if (cols == 0 || cols > 10) {
            throw new IllegalArgumentException("one to ten columns");
        }
        this.crumbled = new boolean[crumbled.length][];
        for (int r = 0; r < crumbled.length; r++) {
            if (crumbled[r].length != cols) {
                throw new IllegalArgumentException("a rectangular cliff");
            }
            this.crumbled[r] = crumbled[r].clone();
        }
        if (crumbled[0][0] || crumbled[crumbled.length - 1][cols - 1]) {
            throw new IllegalArgumentException("the goat and the kid need ledges to stand on");
        }
        int rows = crumbled.length;
        int[][] dist = new int[rows][cols];
        for (int[] row : dist) {
            Arrays.fill(row, -1);
        }
        dist[0][0] = 0;
        Deque<int[]> q = new ArrayDeque<>();
        q.add(new int[] {0, 0});
        while (!q.isEmpty()) {
            int[] s = q.poll();
            for (int[] d : LEAPS) {
                int r = s[0] + d[0];
                int c = s[1] + d[1];
                if (r >= 0 && c >= 0 && r < rows && c < cols && !crumbled[r][c] && dist[r][c] < 0) {
                    dist[r][c] = dist[s[0]][s[1]] + 1;
                    q.add(new int[] {r, c});
                }
            }
        }
        fewest = dist[rows - 1][cols - 1];
    }

    /** A seeded cliff of 3-7 by 3-7 ledges, each crumbled with chance 1/5 (corners stand). */
    public static GoatLeaps seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x6047L);
        int rows = 3 + rng.nextInt(5);
        int cols = 3 + rng.nextInt(5);
        boolean[][] g = new boolean[rows][cols];
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                g[r][c] = rng.nextInt(5) == 0;
            }
        }
        g[0][0] = false;
        g[rows - 1][cols - 1] = false;
        return new GoatLeaps(g);
    }

    public int rows() {
        return crumbled.length;
    }

    public int cols() {
        return crumbled[0].length;
    }

    public boolean crumbled(int r, int c) {
        return crumbled[r][c];
    }

    /** The fewest leaps to the kid, or -1 if it cannot be reached. */
    public int fewest() {
        return fewest;
    }

    public int used() {
        return used;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Spots the stray kid: the quest's first step. */
    public void spot(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "spot", "kid");
        }
    }

    /** Leaps through ledges {r, c} from the top-left: FELL on a crumbled ledge, STRAY short of the kid, else WELL/LONG. */
    public Outcome leap(String eventId, List<int[]> ledges) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (ledges == null) {
            return Outcome.NOT_THERE;
        }
        int r = 0;
        int c = 0;
        for (int[] l : ledges) {
            if (l.length != 2 || l[0] < 0 || l[1] < 0 || l[0] >= rows() || l[1] >= cols()) {
                return Outcome.NOT_THERE;
            }
            int dr = Math.abs(l[0] - r);
            int dc = Math.abs(l[1] - c);
            if (!(dr == 1 && dc == 2 || dr == 2 && dc == 1)) {
                return Outcome.NOT_THERE;
            }
            r = l[0];
            c = l[1];
        }
        events.add(eventId);
        used = ledges.size();
        last = null;
        for (int[] l : ledges) {
            if (crumbled[l[0]][l[1]]) {
                last = Outcome.FELL;
                break;
            }
        }
        if (last == null) {
            if (r != rows() - 1 || c != cols() - 1) {
                last = Outcome.STRAY;
            } else {
                last = used == fewest ? Outcome.WELL : Outcome.LONG;
            }
        }
        if (last == Outcome.WELL) {
            quest.apply(eventId, "leap", "well");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the goat reached the kid well. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperGoatLines.THANKS;
        }
        return KeeperGoatLines.line(this);
    }
}
