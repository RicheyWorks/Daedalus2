// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.lanes;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 25 of the Youtube Master Island story, "The Market Lanes" (quest {@code q_market_lanes}). The children walk
 * from the harbour gate (top-left) to the inn (bottom-right), only east or south, through squares with a crowd each.
 * The walk is easy when the crowd passed is the least possible; {@link #least()} is exact min-path-sum DP and
 * {@link #bestPath()} walks it back.
 */
public final class MarketLanes {
    public static final String QUEST_ID = "q_market_lanes";
    public static final int STEPS_TO_TAKE = 3;

    public enum Dir { EAST, SOUTH }

    public enum Outcome { STEPPED, BACKED, BLOCKED, AT_GATE, EASY, JOSTLED, NOT_THERE, DUPLICATE, IGNORED }

    private final int[][] crowd;
    private final int rows;
    private final int cols;
    private final int[][] dp;
    private final Deque<Dir> walked = new ArrayDeque<>();
    private int r;
    private int c;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("step", "lane", STEPS_TO_TAKE),
            new QuestProgress.Step("arrive", "easy", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private Outcome last;

    public MarketLanes(int[][] grid) {
        if (grid.length == 0 || grid[0].length == 0) {
            throw new IllegalArgumentException("empty market");
        }
        rows = grid.length;
        cols = grid[0].length;
        crowd = new int[rows][];
        for (int i = 0; i < rows; i++) {
            if (grid[i].length != cols) {
                throw new IllegalArgumentException("ragged market");
            }
            for (int v : grid[i]) {
                if (v < 0) {
                    throw new IllegalArgumentException("negative crowd");
                }
            }
            crowd[i] = grid[i].clone();
        }
        dp = new int[rows][cols];
        for (int i = rows - 1; i >= 0; i--) {
            for (int j = cols - 1; j >= 0; j--) {
                int east = j + 1 < cols ? dp[i][j + 1] : Integer.MAX_VALUE;
                int south = i + 1 < rows ? dp[i + 1][j] : Integer.MAX_VALUE;
                int rest = Math.min(east, south);
                dp[i][j] = crowd[i][j] + (rest == Integer.MAX_VALUE ? 0 : rest);
            }
        }
    }

    /** A seeded market: 3-6 by 3-6 squares with a crowd of 0-9 each. */
    public static MarketLanes seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x1A4E5L);
        int rs = 3 + rng.nextInt(4);
        int cs = 3 + rng.nextInt(4);
        int[][] g = new int[rs][cs];
        for (int i = 0; i < rs; i++) {
            for (int j = 0; j < cs; j++) {
                g[i][j] = rng.nextInt(10);
            }
        }
        return new MarketLanes(g);
    }

    public int rows() {
        return rows;
    }

    public int cols() {
        return cols;
    }

    public int crowd(int row, int col) {
        return crowd[row][col];
    }

    /** The least crowd passed from gate to inn, both squares included. */
    public int least() {
        return dp[0][0];
    }

    /** One least-crowded walk. */
    public List<Dir> bestPath() {
        List<Dir> out = new ArrayList<>();
        int i = 0;
        int j = 0;
        while (i < rows - 1 || j < cols - 1) {
            boolean east = j + 1 < cols && (i + 1 >= rows || dp[i][j + 1] <= dp[i + 1][j]);
            out.add(east ? Dir.EAST : Dir.SOUTH);
            if (east) {
                j++;
            } else {
                i++;
            }
        }
        return out;
    }

    /** The crowd passed so far, the gate included. */
    public int passed() {
        int i = 0;
        int j = 0;
        int sum = crowd[0][0];
        for (Dir d : walked) {
            if (d == Dir.EAST) {
                j++;
            } else {
                i++;
            }
            sum += crowd[i][j];
        }
        return sum;
    }

    public int row() {
        return r;
    }

    public int col() {
        return c;
    }

    public boolean atInn() {
        return r == rows - 1 && c == cols - 1;
    }

    public QuestProgress quest() {
        return quest;
    }

    public Outcome last() {
        return last;
    }

    private Outcome guard(String eventId) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        return events.contains(eventId) ? Outcome.DUPLICATE : null;
    }

    /** Steps one square east or south. */
    public Outcome step(String eventId, Dir d) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (d == null || (d == Dir.EAST && c + 1 >= cols) || (d == Dir.SOUTH && r + 1 >= rows)) {
            return Outcome.BLOCKED;
        }
        events.add(eventId);
        walked.addLast(d);
        if (d == Dir.EAST) {
            c++;
        } else {
            r++;
        }
        last = null;
        quest.apply(eventId, "step", "lane");
        return Outcome.STEPPED;
    }

    /** Backs up one square. */
    public Outcome back(String eventId) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (walked.isEmpty()) {
            return Outcome.AT_GATE;
        }
        events.add(eventId);
        if (walked.removeLast() == Dir.EAST) {
            c--;
        } else {
            r--;
        }
        last = null;
        return Outcome.BACKED;
    }

    /** Knocks at the inn: NOT_THERE until the walk reaches it, EASY at the least crowd, else JOSTLED. */
    public Outcome arrive(String eventId) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (!atInn()) {
            return Outcome.NOT_THERE;
        }
        events.add(eventId);
        last = passed() == least() ? Outcome.EASY : Outcome.JOSTLED;
        if (last == Outcome.EASY) {
            quest.apply(eventId, "arrive", "easy");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once a walk was easy. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperLaneLines.THANKS;
        }
        return KeeperLaneLines.line(this);
    }
}
