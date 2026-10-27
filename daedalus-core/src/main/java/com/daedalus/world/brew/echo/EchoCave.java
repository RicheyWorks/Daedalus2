// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.echo;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 30 of the Youtube Master Island story, "The Echo Cave" (quest {@code q_echo_cave}). The cave wall carries a
 * row of note marks (d, r, m, f, s). The player sings a subsequence of them; the cave answers only a chant that reads
 * the same backwards. {@link #longest()} is the exact longest palindromic subsequence by interval DP. Singing a
 * palindrome of that length earns credit; a shorter echo or a chant that does not echo does not.
 */
public final class EchoCave {
    public static final String QUEST_ID = "q_echo_cave";
    static final String NOTES = "drmfs";

    public enum Outcome { WELL, SHORT, NO_ECHO, NOT_ON_WALL, DUPLICATE, IGNORED }

    private final String marks;
    private final int[][] dp;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("read", "wall", 1),
            new QuestProgress.Step("sing", "well", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private String sung = "";
    private Outcome last;

    public EchoCave(String marks) {
        if (marks == null || marks.isEmpty() || !marks.matches("[drmfs]*")) {
            throw new IllegalArgumentException("marks are d, r, m, f or s");
        }
        this.marks = marks;
        int n = marks.length();
        dp = new int[n][n];
        for (int i = n - 1; i >= 0; i--) {
            dp[i][i] = 1;
            for (int j = i + 1; j < n; j++) {
                dp[i][j] = marks.charAt(i) == marks.charAt(j) ? (i + 1 <= j - 1 ? dp[i + 1][j - 1] : 0) + 2
                        : Math.max(dp[i + 1][j], dp[i][j - 1]);
            }
        }
    }

    /** A seeded wall of 4-12 marks. */
    public static EchoCave seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xEC40L);
        StringBuilder sb = new StringBuilder();
        int n = 4 + rng.nextInt(9);
        for (int i = 0; i < n; i++) {
            sb.append(NOTES.charAt(rng.nextInt(NOTES.length())));
        }
        return new EchoCave(sb.toString());
    }

    public String marks() {
        return marks;
    }

    /** The longest echoing chant the wall holds. */
    public int longest() {
        return dp[0][marks.length() - 1];
    }

    /** One longest echoing chant, walked back from the DP. */
    public String bestChant() {
        StringBuilder left = new StringBuilder();
        String middle = "";
        int i = 0;
        int j = marks.length() - 1;
        while (i <= j) {
            if (i == j) {
                middle = String.valueOf(marks.charAt(i));
                break;
            }
            if (marks.charAt(i) == marks.charAt(j)) {
                left.append(marks.charAt(i));
                i++;
                j--;
            } else if (dp[i + 1][j] >= dp[i][j - 1]) {
                i++;
            } else {
                j--;
            }
        }
        return left + middle + new StringBuilder(left).reverse();
    }

    static boolean inOrder(String sub, String s) {
        int i = 0;
        for (int j = 0; j < s.length() && i < sub.length(); j++) {
            if (s.charAt(j) == sub.charAt(i)) {
                i++;
            }
        }
        return i == sub.length();
    }

    public String sung() {
        return sung;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Reads the wall marks aloud: the quest's first step. */
    public void read(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "read", "wall");
        }
    }

    /** Sings a chant: NOT_ON_WALL unless it follows the marks in order, then WELL, SHORT or NO_ECHO. */
    public Outcome sing(String eventId, String chant) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (chant == null || chant.isEmpty() || !inOrder(chant, marks)) {
            return Outcome.NOT_ON_WALL;
        }
        events.add(eventId);
        sung = chant;
        if (!new StringBuilder(chant).reverse().toString().equals(chant)) {
            last = Outcome.NO_ECHO;
        } else {
            last = chant.length() == longest() ? Outcome.WELL : Outcome.SHORT;
        }
        if (last == Outcome.WELL) {
            quest.apply(eventId, "sing", "well");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the cave echoed well. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperEchoLines.THANKS;
        }
        return KeeperEchoLines.line(this);
    }
}
