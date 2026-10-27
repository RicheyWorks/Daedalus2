// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.plots;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 61 of the Youtube Master Island story, "The Berry Patch" (quest {@code q_berry_patch}). A grid of bushes
 * with berry counts; {@link #sum(int, int, int, int)} is any rectangle's berries from a 2D prefix sum table in constant
 * time, and {@link #richest()} the most berries in any side-by-side square. Picking a richest square earns credit; a
 * POOR square earns none.
 */
public final class BerryPatch {
    public static final String QUEST_ID = "q_berry_patch";

    public enum Outcome { RICHEST, POOR, NOT_THERE, DUPLICATE, IGNORED }

    private final int[][] berries;
    private final long[][] pre;
    private final int side;
    private final long richest;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("count", "bushes", 1),
            new QuestProgress.Step("pick", "richest", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private long picked = -1;
    private Outcome last;

    /** A rectangular grid of non-negative berry counts and a square side that fits. */
    public BerryPatch(int[][] berries, int side) {
        if (berries == null || berries.length == 0 || berries[0].length == 0) {
            throw new IllegalArgumentException("a patch of bushes");
        }
        int r = berries.length;
        int c = berries[0].length;
        if (side <= 0 || side > Math.min(r, c)) {
            throw new IllegalArgumentException("the square fits in the patch");
        }
        this.berries = new int[r][];
        pre = new long[r + 1][c + 1];
        for (int i = 0; i < r; i++) {
            if (berries[i].length != c) {
                throw new IllegalArgumentException("the patch is rectangular");
            }
            this.berries[i] = berries[i].clone();
            for (int j = 0; j < c; j++) {
                if (berries[i][j] < 0) {
                    throw new IllegalArgumentException("no negative berries");
                }
                pre[i + 1][j + 1] = pre[i][j + 1] + pre[i + 1][j] - pre[i][j] + berries[i][j];
            }
        }
        this.side = side;
        long best = 0;
        for (int i = 0; i + side <= r; i++) {
            for (int j = 0; j + side <= c; j++) {
                best = Math.max(best, sum(i, j, i + side, j + side));
            }
        }
        richest = best;
    }

    /** A seeded patch of 1-7 by 1-7 bushes with 0-9 berries and a side of 1 up to the short edge. */
    public static BerryPatch seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xBE77L);
        int r = 1 + rng.nextInt(7);
        int c = 1 + rng.nextInt(7);
        int[][] g = new int[r][c];
        for (int i = 0; i < r; i++) {
            for (int j = 0; j < c; j++) {
                g[i][j] = rng.nextInt(10);
            }
        }
        return new BerryPatch(g, 1 + rng.nextInt(Math.min(r, c)));
    }

    /** Berries in rows r0..r1-1 and columns c0..c1-1. */
    public long sum(int r0, int c0, int r1, int c1) {
        return pre[r1][c1] - pre[r0][c1] - pre[r1][c0] + pre[r0][c0];
    }

    public int rows() {
        return berries.length;
    }

    public int cols() {
        return berries[0].length;
    }

    public int berries(int r, int c) {
        return berries[r][c];
    }

    public int side() {
        return side;
    }

    public long richest() {
        return richest;
    }

    public long picked() {
        return picked;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Counts the bushes: the quest's first step. */
    public void count(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "count", "bushes");
        }
    }

    /** Picks the square with top-left bush (r, c): RICHEST if no square has more, else POOR. */
    public Outcome pick(String eventId, int r, int c) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (r < 0 || c < 0 || r + side > rows() || c + side > cols()) {
            return Outcome.NOT_THERE;
        }
        events.add(eventId);
        picked = sum(r, c, r + side, c + side);
        last = picked == richest ? Outcome.RICHEST : Outcome.POOR;
        if (last == Outcome.RICHEST) {
            quest.apply(eventId, "pick", "richest");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the richest square is picked. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperBerryLines.THANKS;
        }
        return KeeperBerryLines.line(this);
    }
}
