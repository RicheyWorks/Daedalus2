// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.gauge;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 68 of the Youtube Master Island story, "The Tide Gauge" (quest {@code q_tide_gauge}). Hourly water levels;
 * {@link #low(int, int)} is the lowest level over hours a..b inclusive in constant time from a sparse table (minima of
 * every power-of-two run). Naming the low for the boat's trip {@link #from()}..{@link #to()} earns credit; a WRONG low
 * earns none.
 */
public final class TideGauge {
    public static final String QUEST_ID = "q_tide_gauge";

    public enum Outcome { RIGHT, WRONG, DUPLICATE, IGNORED }

    private final List<Integer> levels;
    private final int[][] table;
    private final int from;
    private final int to;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("read", "gauge", 1),
            new QuestProgress.Step("name", "low", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named;
    private Outcome last;

    /** Hourly levels and the boat's trip from..to (inclusive). */
    public TideGauge(List<Integer> levels, int from, int to) {
        if (levels == null || levels.isEmpty() || from < 0 || from > to || to >= levels.size()) {
            throw new IllegalArgumentException("a log and a trip inside it");
        }
        for (Integer l : levels) {
            if (l == null) {
                throw new IllegalArgumentException("every hour has a level");
            }
        }
        this.levels = List.copyOf(levels);
        this.from = from;
        this.to = to;
        int n = levels.size();
        int k = 32 - Integer.numberOfLeadingZeros(n);
        table = new int[k][];
        table[0] = new int[n];
        for (int i = 0; i < n; i++) {
            table[0][i] = levels.get(i);
        }
        for (int j = 1; j < k; j++) {
            int len = 1 << j;
            table[j] = new int[n - len + 1];
            for (int i = 0; i + len <= n; i++) {
                table[j][i] = Math.min(table[j - 1][i], table[j - 1][i + len / 2]);
            }
        }
    }

    /** A seeded log of 1-20 hours with levels -5..9 and a trip inside it. */
    public static TideGauge seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x6A06L);
        int n = 1 + rng.nextInt(20);
        List<Integer> l = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            l.add(rng.nextInt(15) - 5);
        }
        int a = rng.nextInt(n);
        return new TideGauge(l, a, a + rng.nextInt(n - a));
    }

    /** The lowest level over hours a..b inclusive. */
    public int low(int a, int b) {
        if (a < 0 || a > b || b >= levels.size()) {
            throw new IllegalArgumentException("hours inside the log");
        }
        int j = 31 - Integer.numberOfLeadingZeros(b - a + 1);
        return Math.min(table[j][a], table[j][b - (1 << j) + 1]);
    }

    public List<Integer> levels() {
        return levels;
    }

    public int hours() {
        return levels.size();
    }

    public int from() {
        return from;
    }

    public int to() {
        return to;
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

    /** Reads the gauge: the quest's first step. */
    public void read(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "read", "gauge");
        }
    }

    /** Names the low for the trip: RIGHT or WRONG. */
    public Outcome name(String eventId, int level) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        named = level;
        last = level == low(from, to) ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "name", "low");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the low is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperGaugeLines.THANKS;
        }
        return KeeperGaugeLines.line(this);
    }
}
