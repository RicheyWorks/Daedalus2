// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.hutfloor;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 82 of the Youtube Master Island story, "The Hut Floor" (quest {@code q_hut_floor}). A hut floor of rows
 * (strings of '.' for floor and '#' for a post); reed mats cover two neighbouring floor squares. {@link #ways()} counts
 * the ways to cover every floor square exactly once, by broken-profile bitmask DP (row by row, the mask holds the
 * squares already covered from the row above). Naming the count earns credit; a WRONG count or a floor with NO_FIT
 * earns none.
 */
public final class HutFloor {
    public static final String QUEST_ID = "q_hut_floor";

    public enum Outcome { RIGHT, WRONG, NO_FIT, MALFORMED, DUPLICATE, IGNORED }

    private final List<String> rows;
    private final int width;
    private final long ways;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("sweep", "floor", 1),
            new QuestProgress.Step("count", "layouts", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private long named = -1;
    private Outcome last;

    /** Rows of equal width 1-6 made of '.' and '#'. */
    public HutFloor(List<String> rows) {
        if (rows == null || rows.isEmpty() || rows.get(0) == null) {
            throw new IllegalArgumentException("at least one row");
        }
        width = rows.get(0).length();
        if (width < 1 || width > 6) {
            throw new IllegalArgumentException("a floor 1-6 squares wide");
        }
        for (String r : rows) {
            if (r == null || r.length() != width || !r.matches("[.#]+")) {
                throw new IllegalArgumentException("rows of . and # all the same width");
            }
        }
        this.rows = List.copyOf(rows);
        long[] dp = new long[1 << width];
        dp[0] = 1;
        for (String row : this.rows) {
            long[] next = new long[1 << width];
            for (int mask = 0; mask < 1 << width; mask++) {
                if (dp[mask] != 0) {
                    fill(row, 0, mask, 0, dp[mask], next);
                }
            }
            dp = next;
        }
        ways = dp[0];
    }

    /** Fills row square col onward; mask = squares covered from above, out = squares this row pushes down. */
    private void fill(String row, int col, int mask, int out, long count, long[] next) {
        if (col == width) {
            next[out] += count;
            return;
        }
        boolean covered = (mask >> col & 1) == 1;
        if (row.charAt(col) == '#') {
            if (!covered) {
                fill(row, col + 1, mask, out, count, next);
            }
            return;
        }
        if (covered) {
            fill(row, col + 1, mask, out, count, next);
            return;
        }
        fill(row, col + 1, mask, out | 1 << col, count, next);
        if (col + 1 < width && row.charAt(col + 1) == '.' && (mask >> (col + 1) & 1) == 0) {
            fill(row, col + 2, mask, out, count, next);
        }
    }

    /** A seeded floor of 1-5 rows, 1-4 wide, about one square in six a post. */
    public static HutFloor seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x4F10L);
        int h = 1 + rng.nextInt(5);
        int w = 1 + rng.nextInt(4);
        List<String> r = new ArrayList<>();
        for (int i = 0; i < h; i++) {
            StringBuilder sb = new StringBuilder();
            for (int j = 0; j < w; j++) {
                sb.append(rng.nextInt(6) == 0 ? '#' : '.');
            }
            r.add(sb.toString());
        }
        return new HutFloor(r);
    }

    public List<String> rows() {
        return rows;
    }

    public int width() {
        return width;
    }

    /** Ways to cover every floor square with mats. */
    public long ways() {
        return ways;
    }

    public long named() {
        return named;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Sweeps the floor bare: the quest's first step. */
    public void sweep(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "sweep", "floor");
        }
    }

    /** Names how many mat layouts there are: RIGHT, WRONG, NO_FIT or MALFORMED. */
    public Outcome count(String eventId, long guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (ways == 0) {
            last = Outcome.NO_FIT;
            return last;
        }
        if (guess < 0) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = guess;
        last = guess == ways ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "layouts");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the layouts are counted. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperHutFloor.THANKS;
        }
        return KeeperHutFloor.line(this);
    }
}
