// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.crabs;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 81 of the Youtube Master Island story, "The Crab Pens" (quest {@code q_crab_pens}). One crab is set loose;
 * every moon each crab becomes {@code brood} crabs, and after {@code moons} moons the crabs are shared out into pens
 * of {@code pen}. {@link #leftOver()} is {@code brood^moons mod pen}, by binary exponentiation (square the brood,
 * halve the moons) in at most about 2 log2(moons) multiplications. Naming it earns credit; a WRONG count, or a brood
 * that is WASHED_OUT (a multiple of the pen, so nothing is ever left over after the first moon), earns none.
 */
public final class CrabPens {
    public static final String QUEST_ID = "q_crab_pens";

    public enum Outcome { RIGHT, WRONG, WASHED_OUT, MALFORMED, DUPLICATE, IGNORED }

    private final long brood;
    private final long moons;
    private final long pen;
    private final long leftOver;
    private int multiplications;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("watch", "pens", 1),
            new QuestProgress.Step("count", "leftover", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private long named = -1;
    private Outcome last;

    /** brood >= 0, moons >= 1, pen 2..1_000_000. */
    public CrabPens(long brood, long moons, long pen) {
        if (brood < 0 || moons < 1 || pen < 2 || pen > 1_000_000) {
            throw new IllegalArgumentException("a brood, at least one moon and a real pen");
        }
        this.brood = brood;
        this.moons = moons;
        this.pen = pen;
        long result = 1;
        long base = brood % pen;
        long e = moons;
        while (e > 0) {
            if ((e & 1) == 1) {
                result = result * base % pen;
                multiplications++;
            }
            e >>= 1;
            if (e > 0) {
                base = base * base % pen;
                multiplications++;
            }
        }
        leftOver = result;
    }

    /** A seeded pen: brood 0-9, moons 1-40, pen 2-13. */
    public static CrabPens seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xC2AB5L);
        return new CrabPens(rng.nextInt(10), 1 + rng.nextInt(40), 2 + rng.nextInt(12));
    }

    public long brood() {
        return brood;
    }

    public long moons() {
        return moons;
    }

    public long pen() {
        return pen;
    }

    /** brood^moons mod pen. */
    public long leftOver() {
        return leftOver;
    }

    /** Multiplications binary exponentiation used. */
    public int multiplications() {
        return multiplications;
    }

    /** Whether the brood is a multiple of the pen size. */
    public boolean washedOut() {
        return brood % pen == 0;
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

    /** Watches the pens for a moon: the quest's first step. */
    public void watch(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "watch", "pens");
        }
    }

    /** Names the crabs left over: RIGHT, WRONG, WASHED_OUT or MALFORMED. */
    public Outcome count(String eventId, long guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (washedOut()) {
            last = Outcome.WASHED_OUT;
            return last;
        }
        if (guess < 0 || guess >= pen) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = guess;
        last = guess == leftOver ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "leftover");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the left-over crabs are named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperCrabPens.THANKS;
        }
        return KeeperCrabPens.line(this);
    }
}
