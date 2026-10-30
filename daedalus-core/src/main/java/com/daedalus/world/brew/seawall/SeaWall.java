// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.seawall;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 38 of the Youtube Master Island story, "The Sea Wall" (quest {@code q_sea_wall}). Unit-wide stones of
 * different heights stand in a row. A storm board covers a run of stones up to a height no taller than the lowest
 * stone in the run. {@link #largest()} is the exact largest rectangle in the histogram by a monotonic stack. Fitting a
 * board of that area earns credit; a smaller board does not, and a board that overhangs a stone is refused credit.
 */
public final class SeaWall {
    public static final String QUEST_ID = "q_sea_wall";

    public enum Outcome { WELL, SMALL, OVERHANG, NOT_THERE, DUPLICATE, IGNORED }

    private final int[] height;
    private final int largest;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("measure", "wall", 1),
            new QuestProgress.Step("fit", "well", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int from = -1;
    private int to = -1;
    private int boardHeight;
    private int lowStone = -1;
    private Outcome last;

    public SeaWall(int... height) {
        if (height == null || height.length == 0) {
            throw new IllegalArgumentException("at least one stone");
        }
        for (int h : height) {
            if (h <= 0) {
                throw new IllegalArgumentException("stones stand above the sand");
            }
        }
        this.height = height.clone();
        int n = height.length;
        int best = 0;
        Deque<Integer> stack = new ArrayDeque<>();
        for (int i = 0; i <= n; i++) {
            int h = i == n ? 0 : height[i];
            while (!stack.isEmpty() && height[stack.peek()] >= h) {
                int top = stack.pop();
                int left = stack.isEmpty() ? -1 : stack.peek();
                best = Math.max(best, height[top] * (i - left - 1));
            }
            stack.push(i);
        }
        largest = best;
    }

    /** A seeded wall of 3-14 stones, 1-9 high. */
    public static SeaWall seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x5EA3L);
        int[] h = new int[3 + rng.nextInt(12)];
        for (int i = 0; i < h.length; i++) {
            h[i] = 1 + rng.nextInt(9);
        }
        return new SeaWall(h);
    }

    public int stones() {
        return height.length;
    }

    public int height(int stone) {
        return height[stone];
    }

    /** The largest board area that sits flush on the wall. */
    public int largest() {
        return largest;
    }

    public int from() {
        return from;
    }

    public int to() {
        return to;
    }

    public int boardHeight() {
        return boardHeight;
    }

    public int boardArea() {
        return from < 0 ? 0 : (to - from + 1) * boardHeight;
    }

    /** The first stone the last board overhung, or -1. */
    public int lowStone() {
        return lowStone;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Walks the wall measuring the stones: the quest's first step. */
    public void measure(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "measure", "wall");
        }
    }

    /** Fits a board over stones {@code a..b} at height {@code h}: OVERHANG, WELL at the largest area, else SMALL. */
    public Outcome fit(String eventId, int a, int b, int h) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (a < 0 || b >= height.length || a > b || h <= 0) {
            return Outcome.NOT_THERE;
        }
        events.add(eventId);
        from = a;
        to = b;
        boardHeight = h;
        lowStone = -1;
        for (int i = a; i <= b; i++) {
            if (height[i] < h) {
                lowStone = i;
                break;
            }
        }
        if (lowStone >= 0) {
            last = Outcome.OVERHANG;
        } else {
            last = boardArea() == largest ? Outcome.WELL : Outcome.SMALL;
        }
        if (last == Outcome.WELL) {
            quest.apply(eventId, "fit", "well");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the board fitted well. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperWallLines.THANKS;
        }
        return KeeperWallLines.line(this);
    }
}
