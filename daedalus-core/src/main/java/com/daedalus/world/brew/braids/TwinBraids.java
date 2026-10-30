// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.braids;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 73 of the Youtube Master Island story, "The Twin Braids" (quest {@code q_twin_braids}). Two bead braids
 * (strings of bead letters); {@link #longest()} is the length of their longest common subsequence, by the classic
 * LCS table. Naming a bead run found in order in both braids with that length earns credit; a SHORT run, a run
 * NOT_SHARED by both, or braids with NO_COMMON bead earn none.
 */
public final class TwinBraids {
    public static final String QUEST_ID = "q_twin_braids";
    static final String BEADS = "RGBY";

    public enum Outcome { LONGEST, SHORT, NOT_SHARED, NO_COMMON, MALFORMED, DUPLICATE, IGNORED }

    private final String left;
    private final String right;
    private final int longest;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("compare", "braids", 1),
            new QuestProgress.Step("name", "run", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** Two braids of beads R, G, B, Y (either may be empty). */
    public TwinBraids(String left, String right) {
        if (left == null || right == null || !valid(left) || !valid(right)) {
            throw new IllegalArgumentException("braids are strings of R, G, B, Y beads");
        }
        this.left = left;
        this.right = right;
        int[][] t = new int[left.length() + 1][right.length() + 1];
        for (int i = 1; i <= left.length(); i++) {
            for (int j = 1; j <= right.length(); j++) {
                t[i][j] = left.charAt(i - 1) == right.charAt(j - 1)
                        ? t[i - 1][j - 1] + 1 : Math.max(t[i - 1][j], t[i][j - 1]);
            }
        }
        longest = t[left.length()][right.length()];
    }

    static boolean valid(String s) {
        for (int i = 0; i < s.length(); i++) {
            if (BEADS.indexOf(s.charAt(i)) < 0) {
                return false;
            }
        }
        return true;
    }

    /** Whether run appears in order (not necessarily touching) in braid. */
    public static boolean within(String run, String braid) {
        int k = 0;
        for (int i = 0; i < braid.length() && k < run.length(); i++) {
            if (braid.charAt(i) == run.charAt(k)) {
                k++;
            }
        }
        return k == run.length();
    }

    /** Seeded braids of 0-7 beads each. */
    public static TwinBraids seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xB2A1DL);
        return new TwinBraids(braid(rng), braid(rng));
    }

    private static String braid(SplittableRandom rng) {
        StringBuilder sb = new StringBuilder();
        int n = rng.nextInt(8);
        for (int i = 0; i < n; i++) {
            sb.append(BEADS.charAt(rng.nextInt(BEADS.length())));
        }
        return sb.toString();
    }

    public String left() {
        return left;
    }

    public String right() {
        return right;
    }

    /** Length of the longest bead run found in order in both braids. */
    public int longest() {
        return longest;
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

    /** Lays the braids side by side: the quest's first step. */
    public void compare(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "compare", "braids");
        }
    }

    /** Names a shared run: LONGEST, SHORT, NOT_SHARED, NO_COMMON or MALFORMED. */
    public Outcome name(String eventId, String run) {
        if (eventId == null || eventId.isBlank() || run == null) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (longest == 0) {
            last = Outcome.NO_COMMON;
            return last;
        }
        if (run.isEmpty() || !valid(run)) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = run.length();
        last = !within(run, left) || !within(run, right) ? Outcome.NOT_SHARED
                : run.length() == longest ? Outcome.LONGEST : Outcome.SHORT;
        if (last == Outcome.LONGEST) {
            quest.apply(eventId, "name", "run");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the longest run is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperTwinBraids.THANKS;
        }
        return KeeperTwinBraids.line(this);
    }
}
