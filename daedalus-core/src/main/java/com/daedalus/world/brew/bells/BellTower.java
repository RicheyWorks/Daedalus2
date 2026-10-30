// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.bells;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 57 of the Youtube Master Island story, "The Bell Tower" (quest {@code q_bell_tower}). Each bell rings every
 * few beats and they all rang together on beat 0; {@link #together()} is the next beat they all ring, the least common
 * multiple of their periods via Euclid's gcd. Naming that beat earns credit; an OFFBEAT or LATE beat earns none.
 */
public final class BellTower {
    public static final String QUEST_ID = "q_bell_tower";

    public enum Outcome { TOGETHER, OFFBEAT, LATE, DUPLICATE, IGNORED }

    private final List<Integer> periods;
    private final long together;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("listen", "bells", 1),
            new QuestProgress.Step("name", "beat", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private long named;
    private Outcome last;

    /** Bell periods, each 1 or more beats. */
    public BellTower(List<Integer> periods) {
        if (periods == null || periods.isEmpty()) {
            throw new IllegalArgumentException("at least one bell");
        }
        long l = 1;
        for (Integer p : periods) {
            if (p == null || p <= 0) {
                throw new IllegalArgumentException("a bell rings every 1 or more beats");
            }
            l = l / gcd(l, p) * p;
        }
        this.periods = List.copyOf(periods);
        this.together = l;
    }

    /** Euclid's greatest common divisor. */
    static long gcd(long a, long b) {
        while (b != 0) {
            long t = a % b;
            a = b;
            b = t;
        }
        return a;
    }

    /** A seeded tower of 1-4 bells with periods 1-9. */
    public static BellTower seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xBE11L);
        int n = 1 + rng.nextInt(4);
        List<Integer> p = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            p.add(1 + rng.nextInt(9));
        }
        return new BellTower(p);
    }

    public List<Integer> periods() {
        return periods;
    }

    /** The next beat after 0 when every bell rings. */
    public long together() {
        return together;
    }

    /** Whether every bell rings on this beat. */
    public boolean allRing(long beat) {
        for (int p : periods) {
            if (beat % p != 0) {
                return false;
            }
        }
        return true;
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

    /** Listens to the bells: the quest's first step. */
    public void listen(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "listen", "bells");
        }
    }

    /** Names a beat: TOGETHER if it is the next shared beat, LATE if a later shared beat, else OFFBEAT. */
    public Outcome name(String eventId, long beat) {
        if (eventId == null || eventId.isBlank() || beat <= 0) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        named = beat;
        last = beat == together ? Outcome.TOGETHER : allRing(beat) ? Outcome.LATE : Outcome.OFFBEAT;
        if (last == Outcome.TOGETHER) {
            quest.apply(eventId, "name", "beat");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the beat is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperBellLines.THANKS;
        }
        return KeeperBellLines.line(this);
    }
}
