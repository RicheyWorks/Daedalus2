// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.tidemarks;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 90 of the Youtube Master Island story, "The Tide Marks" (quest {@code q_tide_marks}). The sea wall holds a
 * row of tide marks. {@link #distinct()} counts the different runs of {@code len} marks with a Rabin-Karp rolling hash,
 * checking hash matches letter by letter so collisions never merge runs; {@link #windows()} is the trap, every
 * stretch counted. Naming the runs earns credit; a WRONG count, or a wall too SHORT for the run, earns none.
 */
public final class TideMarks {
    public static final String QUEST_ID = "q_tide_marks";

    public enum Outcome { RIGHT, WRONG, SHORT, MALFORMED, DUPLICATE, IGNORED }

    private final String marks;
    private final int len;
    private final int windows;
    private final int distinct;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("read", "marks", 1),
            new QuestProgress.Step("count", "patterns", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    private static final long BASE = 131;
    private static final long MOD = 1_000_000_007L;

    /** Tide marks (letters a-z) and a run length (1+). */
    public TideMarks(String marks, int len) {
        if (marks == null || len < 1 || !marks.matches("[a-z]*")) {
            throw new IllegalArgumentException("real marks and a run length");
        }
        this.marks = marks;
        this.len = len;
        int n = marks.length();
        windows = Math.max(0, n - len + 1);
        Map<Long, List<Integer>> byHash = new HashMap<>();
        int d = 0;
        if (len <= n) {
            long pow = 1;
            for (int i = 1; i < len; i++) {
                pow = pow * BASE % MOD;
            }
            long h = 0;
            for (int i = 0; i < n; i++) {
                if (i >= len) {
                    h = (h - marks.charAt(i - len) * pow % MOD + MOD) % MOD;
                }
                h = (h * BASE + marks.charAt(i)) % MOD;
                if (i >= len - 1) {
                    int start = i - len + 1;
                    List<Integer> same = byHash.computeIfAbsent(h, k -> new ArrayList<>());
                    boolean seen = same.stream().anyMatch(s -> marks.regionMatches(s, marks, start, len));
                    if (!seen) {
                        same.add(start);
                        d++;
                    }
                }
            }
        }
        distinct = d;
    }

    /** A seeded wall of 0-12 marks from a-c and a run length 1-4. */
    public static TideMarks seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x71DEL);
        int n = rng.nextInt(13);
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < n; i++) {
            b.append((char) ('a' + rng.nextInt(3)));
        }
        return new TideMarks(b.toString(), 1 + rng.nextInt(4));
    }

    public String marks() {
        return marks;
    }

    public int len() {
        return len;
    }

    /** Different runs of {@code len} marks (Rabin-Karp). */
    public int distinct() {
        return distinct;
    }

    /** Every stretch of {@code len} marks: the trap. */
    public int windows() {
        return windows;
    }

    /** Whether the run is longer than the wall. */
    public boolean shortWall() {
        return len > marks.length();
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

    /** Reads the tide marks: the quest's first step. */
    public void read(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "read", "marks");
        }
    }

    /** Names the answer: RIGHT, WRONG, SHORT or MALFORMED. */
    public Outcome count(String eventId, int guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (shortWall()) {
            last = Outcome.SHORT;
            return last;
        }
        if (guess < 0) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = guess;
        last = guess == distinct() ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "patterns");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the answer is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperTideMarks.THANKS;
        }
        return KeeperTideMarks.line(this);
    }
}
