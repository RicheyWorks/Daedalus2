// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.flagline;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 86 of the Youtube Master Island story, "The Flag Shells" (quest {@code q_flag_shells}). A line of red,
 * white and blue shells (R, W, B) must end up as the island flag: all reds, then whites, then blues. One move swaps
 * any two shells. {@link #fewest()} is the fewest swaps, by counting misplaced shells per (place colour, shell colour):
 * pairs that can trade directly cost one swap each, and every leftover three-way cycle costs two. {@link #sorted()}
 * is the flag itself, by one Dutch national flag pass. Naming the fewest earns credit; a WRONG count, or a line
 * ALREADY_FLAG, earns none.
 */
public final class FlagShells {
    public static final String QUEST_ID = "q_flag_shells";
    static final String COLOURS = "RWB";

    public enum Outcome { RIGHT, WRONG, ALREADY_FLAG, MALFORMED, DUPLICATE, IGNORED }

    private final String line;
    private final String sorted;
    private final int fewest;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("lay", "shells", 1),
            new QuestProgress.Step("count", "swaps", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** A line of R, W and B shells (at least one). */
    public FlagShells(String line) {
        if (line == null || !line.matches("[RWB]+")) {
            throw new IllegalArgumentException("a line of R, W, B shells");
        }
        this.line = line;
        char[] a = line.toCharArray();
        int lo = 0;
        int mid = 0;
        int hi = a.length - 1;
        while (mid <= hi) {
            if (a[mid] == 'R') {
                char t = a[lo];
                a[lo++] = a[mid];
                a[mid++] = t;
            } else if (a[mid] == 'W') {
                mid++;
            } else {
                char t = a[hi];
                a[hi--] = a[mid];
                a[mid] = t;
            }
        }
        sorted = new String(a);
        int[][] m = new int[3][3];
        for (int i = 0; i < a.length; i++) {
            m[COLOURS.indexOf(sorted.charAt(i))][COLOURS.indexOf(line.charAt(i))]++;
        }
        int swaps = 0;
        int left = 0;
        for (int i = 0; i < 3; i++) {
            for (int j = i + 1; j < 3; j++) {
                int d = Math.min(m[i][j], m[j][i]);
                swaps += d;
                left += m[i][j] + m[j][i] - 2 * d;
            }
        }
        fewest = swaps + 2 * (left / 3);
    }

    /** A seeded line of 1-8 shells. */
    public static FlagShells seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xF1A6L);
        int n = 1 + rng.nextInt(8);
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < n; i++) {
            sb.append(COLOURS.charAt(rng.nextInt(3)));
        }
        return new FlagShells(sb.toString());
    }

    public String line() {
        return line;
    }

    /** The flag order: reds, whites, blues. */
    public String sorted() {
        return sorted;
    }

    /** Fewest swaps to make the flag. */
    public int fewest() {
        return fewest;
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

    /** Lays the shells out: the quest's first step. */
    public void lay(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "lay", "shells");
        }
    }

    /** Names the fewest swaps: RIGHT, WRONG, ALREADY_FLAG or MALFORMED. */
    public Outcome count(String eventId, int guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (fewest == 0) {
            last = Outcome.ALREADY_FLAG;
            return last;
        }
        if (guess < 0) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = guess;
        last = guess == fewest ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "swaps");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the swaps are counted. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperFlagShells.THANKS;
        }
        return KeeperFlagShells.line(this);
    }
}
