// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.ringdance;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 80 of the Youtube Master Island story, "The Ring Dance" (quest {@code q_ring_dance}). Dancers stand in a
 * ring, each in a shell (S) or feather (F) crown; every dancer holds one ribbon with one partner wearing the other
 * crown, and no two ribbons may cross. {@link #ways()} counts such pairings by the Catalan interval recurrence
 * (dancer i pairs with some k; the dancers between and after are counted separately). Naming the count earns credit;
 * a WRONG count or a ring with NO_WAY earns none.
 */
public final class RingDance {
    public static final String QUEST_ID = "q_ring_dance";

    public enum Outcome { RIGHT, WRONG, NO_WAY, MALFORMED, DUPLICATE, IGNORED }

    private final String crowns;
    private final long ways;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("form", "ring", 1),
            new QuestProgress.Step("count", "pairings", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private long named = -1;
    private Outcome last;

    /** Crowns round the ring, S or F, an even number of dancers (at least two). */
    public RingDance(String crowns) {
        if (crowns == null || crowns.isEmpty() || crowns.length() % 2 != 0 || !crowns.matches("[SF]+")) {
            throw new IllegalArgumentException("an even ring of S and F crowns");
        }
        this.crowns = crowns;
        int n = crowns.length();
        long[][] f = new long[n + 1][n + 1];
        for (int i = n; i >= 0; i--) {
            for (int j = i; j <= n; j++) {
                if (j == i) {
                    f[i][j] = 1;
                    continue;
                }
                long s = 0;
                for (int k = i + 1; k < j; k += 2) {
                    if (crowns.charAt(i) != crowns.charAt(k)) {
                        s += f[i + 1][k] * f[k + 1][j];
                    }
                }
                f[i][j] = s;
            }
        }
        ways = f[0][n];
    }

    /** A seeded ring of 2-10 dancers. */
    public static RingDance seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x219DL);
        int n = 2 * (1 + rng.nextInt(5));
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < n; i++) {
            sb.append(rng.nextBoolean() ? 'S' : 'F');
        }
        return new RingDance(sb.toString());
    }

    public String crowns() {
        return crowns;
    }

    public int dancers() {
        return crowns.length();
    }

    /** Non-crossing pairings, each ribbon joining a shell crown to a feather crown. */
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

    /** Forms the ring: the quest's first step. */
    public void form(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "form", "ring");
        }
    }

    /** Names how many pairings there are: RIGHT, WRONG, NO_WAY or MALFORMED. */
    public Outcome count(String eventId, long guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (ways == 0) {
            last = Outcome.NO_WAY;
            return last;
        }
        if (guess < 0) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = guess;
        last = guess == ways ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "pairings");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the pairings are counted. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperRingDance.THANKS;
        }
        return KeeperRingDance.line(this);
    }
}
