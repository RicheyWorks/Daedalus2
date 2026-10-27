// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.switches;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 95 of the Youtube Master Island story, "The Lantern Switches" (quest {@code q_lantern_switches}). Each switch
 * flips one harbour lantern. {@link #flips()} is the fewest flips from one pattern to another: the XOR of the two,
 * with set bits counted by clearing the lowest each step; {@link #gap()} is the trap, the patterns subtracted as
 * numbers. Naming the flips earns credit; a WRONG count, or patterns that already MATCH, earns none.
 */
public final class LanternSwitches {
    public static final String QUEST_ID = "q_lantern_switches";

    public enum Outcome { RIGHT, WRONG, MATCH, MALFORMED, DUPLICATE, IGNORED }

    private final int width;
    private final int now;
    private final int want;
    private final int flips;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("read", "lanterns", 1),
            new QuestProgress.Step("count", "flips", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** A row of 1-30 lanterns and two patterns (bit i is lantern i lit). */
    public LanternSwitches(int width, int now, int want) {
        if (width < 1 || width > 30 || now < 0 || want < 0 || now >> width != 0 || want >> width != 0) {
            throw new IllegalArgumentException("a real row and patterns");
        }
        this.width = width;
        this.now = now;
        this.want = want;
        int x = now ^ want;
        int f = 0;
        while (x != 0) {
            x &= x - 1;
            f++;
        }
        flips = f;
    }

    /** A seeded row of 1-6 lanterns and two patterns. */
    public static LanternSwitches seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x1A7EL);
        int w = 1 + rng.nextInt(6);
        return new LanternSwitches(w, rng.nextInt(1 << w), rng.nextInt(1 << w));
    }

    public int width() {
        return width;
    }

    public int now() {
        return now;
    }

    public int want() {
        return want;
    }

    /** A pattern as lanterns, highest first. */
    public String row(int pattern) {
        StringBuilder b = new StringBuilder();
        for (int i = width - 1; i >= 0; i--) {
            b.append(pattern >> i & 1);
        }
        return b.toString();
    }

    /** Fewest flips (XOR popcount). */
    public int flips() {
        return flips;
    }

    /** The gap between the patterns as numbers: the trap. */
    public int gap() {
        return Math.abs(now - want);
    }

    /** Whether the patterns already match. */
    public boolean match() {
        return now == want;
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

    /** Reads the lantern row: the quest's first step. */
    public void read(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "read", "lanterns");
        }
    }

    /** Names the answer: RIGHT, WRONG, MATCH or MALFORMED. */
    public Outcome count(String eventId, int guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (match()) {
            last = Outcome.MATCH;
            return last;
        }
        if (guess < 0) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = guess;
        last = guess == flips() ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "flips");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the answer is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperLanternSwitches.THANKS;
        }
        return KeeperLanternSwitches.line(this);
    }
}
