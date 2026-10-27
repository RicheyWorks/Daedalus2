// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.shells;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;
import java.util.TreeSet;

/**
 * Chapter 26 of the Youtube Master Island story, "The Shell Strings" (quest {@code q_shell_strings}). Two children each
 * have a string of shells (c cowrie, w whelk, s scallop, p periwinkle). Shells may be taken off but never reordered.
 * The strings match well when they end identical and as long as possible; {@link #longest()} is exact
 * longest-common-subsequence DP and {@link #bestMatch()} walks it back.
 */
public final class ShellStrings {
    public static final String QUEST_ID = "q_shell_strings";
    public static final int SHELLS_TO_TAKE = 3;
    static final String KINDS = "cwsp";

    public enum Side { LEFT, RIGHT }

    public enum Outcome { TAKEN, PUT_BACK, NOT_THERE, ALREADY_OFF, WELL, SHORT, DIFFERENT, DUPLICATE, IGNORED }

    private final String left;
    private final String right;
    private final int[][] dp;
    private final Set<Integer> offLeft = new TreeSet<>();
    private final Set<Integer> offRight = new TreeSet<>();
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("take", "shell", SHELLS_TO_TAKE),
            new QuestProgress.Step("compare", "well", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private Outcome last;

    public ShellStrings(String left, String right) {
        if (left == null || right == null || !left.matches("[cwsp]*") || !right.matches("[cwsp]*")) {
            throw new IllegalArgumentException("shells are c, w, s or p");
        }
        this.left = left;
        this.right = right;
        dp = new int[left.length() + 1][right.length() + 1];
        for (int i = left.length() - 1; i >= 0; i--) {
            for (int j = right.length() - 1; j >= 0; j--) {
                dp[i][j] = left.charAt(i) == right.charAt(j) ? dp[i + 1][j + 1] + 1
                        : Math.max(dp[i + 1][j], dp[i][j + 1]);
            }
        }
    }

    /** Two seeded strings of 4-10 shells each. */
    public static ShellStrings seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x5E115L);
        return new ShellStrings(string(rng), string(rng));
    }

    private static String string(SplittableRandom rng) {
        StringBuilder sb = new StringBuilder();
        int n = 4 + rng.nextInt(7);
        for (int i = 0; i < n; i++) {
            sb.append(KINDS.charAt(rng.nextInt(KINDS.length())));
        }
        return sb.toString();
    }

    public String left() {
        return left;
    }

    public String right() {
        return right;
    }

    /** The longest pair of matching strings either child can keep. */
    public int longest() {
        return dp[0][0];
    }

    /** One longest matching string. */
    public String bestMatch() {
        StringBuilder sb = new StringBuilder();
        int i = 0;
        int j = 0;
        while (i < left.length() && j < right.length()) {
            if (left.charAt(i) == right.charAt(j)) {
                sb.append(left.charAt(i));
                i++;
                j++;
            } else if (dp[i + 1][j] >= dp[i][j + 1]) {
                i++;
            } else {
                j++;
            }
        }
        return sb.toString();
    }

    /** What a child still has on their string. */
    public String kept(Side side) {
        String s = side == Side.LEFT ? left : right;
        Set<Integer> off = side == Side.LEFT ? offLeft : offRight;
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < s.length(); i++) {
            if (!off.contains(i)) {
                sb.append(s.charAt(i));
            }
        }
        return sb.toString();
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

    /** Takes the shell at a position (in the original string) off one child's string. */
    public Outcome take(String eventId, Side side, int pos) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        int len = side == Side.LEFT ? left.length() : right.length();
        if (side == null || pos < 0 || pos >= len) {
            return Outcome.NOT_THERE;
        }
        if (!(side == Side.LEFT ? offLeft : offRight).add(pos)) {
            return Outcome.ALREADY_OFF;
        }
        events.add(eventId);
        last = null;
        quest.apply(eventId, "take", "shell");
        return Outcome.TAKEN;
    }

    /** Threads a taken shell back on in its old place. */
    public Outcome putBack(String eventId, Side side, int pos) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (side == null || !(side == Side.LEFT ? offLeft : offRight).remove(pos)) {
            return Outcome.NOT_THERE;
        }
        events.add(eventId);
        last = null;
        return Outcome.PUT_BACK;
    }

    /** Holds the strings side by side: DIFFERENT until they match, WELL at the longest, else SHORT. */
    public Outcome compare(String eventId) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (!kept(Side.LEFT).equals(kept(Side.RIGHT))) {
            return Outcome.DIFFERENT;
        }
        events.add(eventId);
        last = kept(Side.LEFT).length() == longest() ? Outcome.WELL : Outcome.SHORT;
        if (last == Outcome.WELL) {
            quest.apply(eventId, "compare", "well");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the strings matched well. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperShellLines.THANKS;
        }
        return KeeperShellLines.line(this);
    }
}
