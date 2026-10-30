// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.flags;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 28 of the Youtube Master Island story, "The Island Flags" (quest {@code q_island_flags}). Each isle flies a
 * flag, and isles that share a shore must fly different colours. {@link #fewest()} is the exact chromatic number by
 * dynamic programming over subsets of isles (each colour class an independent set). Raising a proper set at that
 * count earns credit; a clash or a wasteful set does not.
 */
public final class IslandFlags {
    public static final String QUEST_ID = "q_island_flags";
    public static final int UNFLAGGED = -1;

    public enum Outcome { DYED, NOT_THERE, BAD_COLOUR, UNFINISHED, WELL, WASTEFUL, CLASH, DUPLICATE, IGNORED }

    private final boolean[][] shore;
    private final int fewest;
    private final int[] colour;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("dye", "flag", 1),
            new QuestProgress.Step("raise", "well", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private Outcome last;
    private int[] clash;

    /** @param shore symmetric adjacency: true where two isles share a shore */
    public IslandFlags(boolean[][] shore) {
        if (shore == null || shore.length < 1 || shore.length > 12) {
            throw new IllegalArgumentException("1 to 12 isles");
        }
        int n = shore.length;
        this.shore = new boolean[n][];
        for (int i = 0; i < n; i++) {
            if (shore[i].length != n || shore[i][i]) {
                throw new IllegalArgumentException("square map, no isle borders itself");
            }
            for (int j = 0; j < n; j++) {
                if (shore[i][j] != shore[j][i]) {
                    throw new IllegalArgumentException("shores run both ways");
                }
            }
            this.shore[i] = shore[i].clone();
        }
        colour = new int[n];
        Arrays.fill(colour, UNFLAGGED);
        fewest = chromatic();
    }

    /** A seeded map of 4-8 isles, each pair sharing a shore with probability one half. */
    public static IslandFlags seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xF1A6L);
        int n = 4 + rng.nextInt(5);
        boolean[][] s = new boolean[n][n];
        for (int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                s[i][j] = rng.nextBoolean();
                s[j][i] = s[i][j];
            }
        }
        return new IslandFlags(s);
    }

    private int chromatic() {
        int n = shore.length;
        int full = (1 << n) - 1;
        boolean[] independent = new boolean[1 << n];
        independent[0] = true;
        for (int m = 1; m <= full; m++) {
            int v = Integer.numberOfTrailingZeros(m);
            int rest = m & (m - 1);
            boolean ok = independent[rest];
            for (int u = 0; ok && u < n; u++) {
                if ((rest >> u & 1) == 1 && shore[v][u]) {
                    ok = false;
                }
            }
            independent[m] = ok;
        }
        int[] dp = new int[1 << n];
        Arrays.fill(dp, Integer.MAX_VALUE);
        dp[0] = 0;
        for (int m = 1; m <= full; m++) {
            int low = m & -m;
            for (int s = m; s > 0; s = (s - 1) & m) {
                if ((s & low) != 0 && independent[s] && dp[m ^ s] != Integer.MAX_VALUE) {
                    dp[m] = Math.min(dp[m], dp[m ^ s] + 1);
                }
            }
        }
        return dp[full];
    }

    public int isles() {
        return shore.length;
    }

    public boolean shore(int a, int b) {
        return shore[a][b];
    }

    /** The fewest colours any proper flag set needs. */
    public int fewest() {
        return fewest;
    }

    public int colour(int isle) {
        return colour[isle];
    }

    public int flagged() {
        int k = 0;
        for (int c : colour) {
            if (c != UNFLAGGED) {
                k++;
            }
        }
        return k;
    }

    public int coloursUsed() {
        return (int) Arrays.stream(colour).filter(c -> c != UNFLAGGED).distinct().count();
    }

    /** The clashing pair from the last raise, or null. */
    public int[] clash() {
        return clash == null ? null : clash.clone();
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    private Outcome guard(String eventId) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        return events.contains(eventId) ? Outcome.DUPLICATE : null;
    }

    /** Dyes an isle's flag a colour (0 up to one less than the number of isles); re-dyeing is allowed. */
    public Outcome dye(String eventId, int isle, int c) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (isle < 0 || isle >= shore.length) {
            return Outcome.NOT_THERE;
        }
        if (c < 0 || c >= shore.length) {
            return Outcome.BAD_COLOUR;
        }
        events.add(eventId);
        colour[isle] = c;
        last = null;
        clash = null;
        quest.apply(eventId, "dye", "flag");
        return Outcome.DYED;
    }

    /** Raises every flag: CLASH if neighbours match, WELL at the fewest colours, else WASTEFUL. */
    public Outcome raise(String eventId) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (flagged() < shore.length) {
            return Outcome.UNFINISHED;
        }
        events.add(eventId);
        clash = null;
        for (int i = 0; i < shore.length && clash == null; i++) {
            for (int j = i + 1; j < shore.length; j++) {
                if (shore[i][j] && colour[i] == colour[j]) {
                    clash = new int[] {i, j};
                    break;
                }
            }
        }
        if (clash != null) {
            last = Outcome.CLASH;
        } else {
            last = coloursUsed() == fewest ? Outcome.WELL : Outcome.WASTEFUL;
        }
        if (last == Outcome.WELL) {
            quest.apply(eventId, "raise", "well");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the flags flew well. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperFlagLines.THANKS;
        }
        return KeeperFlagLines.line(this);
    }
}
