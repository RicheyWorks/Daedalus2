// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.hauling;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 51 of the Youtube Master Island story, "The Hauling Days" (quest {@code q_hauling_days}). Grain sacks stand
 * in a line and must be carted up the hill in that order over {@code days} days. {@link #lightest()} is the smallest
 * possible load on the heaviest day, by binary search on that load with a greedy check. A plan whose heaviest day
 * is that light earns credit; a HEAVY plan earns none.
 */
public final class HaulingDays {
    public static final String QUEST_ID = "q_hauling_days";

    public enum Outcome { WELL, HEAVY, NOT_THERE, DUPLICATE, IGNORED }

    private final int[] sack;
    private final int days;
    private final int lightest;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("count", "sacks", 1),
            new QuestProgress.Step("plan", "well", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int heaviest = -1;
    private Outcome last;

    public HaulingDays(int days, int... sack) {
        if (sack == null || sack.length == 0 || days <= 0) {
            throw new IllegalArgumentException("sacks and at least one day");
        }
        int lo = 0;
        int hi = 0;
        for (int s : sack) {
            if (s <= 0) {
                throw new IllegalArgumentException("sacks have weight");
            }
            lo = Math.max(lo, s);
            hi += s;
        }
        this.sack = sack.clone();
        this.days = days;
        while (lo < hi) {
            int mid = (lo + hi) >>> 1;
            if (daysNeeded(mid) <= days) {
                hi = mid;
            } else {
                lo = mid + 1;
            }
        }
        lightest = lo;
    }

    private int daysNeeded(int load) {
        int need = 1;
        int cart = 0;
        for (int s : sack) {
            if (cart + s > load) {
                need++;
                cart = 0;
            }
            cart += s;
        }
        return need;
    }

    /** A seeded line of 1-9 sacks of 1-12 and 1-4 days. */
    public static HaulingDays seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x4A01L);
        int[] s = new int[1 + rng.nextInt(9)];
        for (int i = 0; i < s.length; i++) {
            s[i] = 1 + rng.nextInt(12);
        }
        return new HaulingDays(1 + rng.nextInt(4), s);
    }

    public int sacks() {
        return sack.length;
    }

    public int sack(int i) {
        return sack[i];
    }

    public int days() {
        return days;
    }

    /** The lightest possible heaviest day. */
    public int lightest() {
        return lightest;
    }

    public int heaviest() {
        return heaviest;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Counts the sacks: the quest's first step. */
    public void count(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "count", "sacks");
        }
    }

    /** Plans the day of each sack, in order (days never go back): WELL at the lightest heaviest day, else HEAVY. */
    public Outcome plan(String eventId, int... dayOf) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (dayOf == null || dayOf.length != sack.length) {
            return Outcome.NOT_THERE;
        }
        int[] load = new int[days];
        for (int i = 0; i < dayOf.length; i++) {
            if (dayOf[i] < 0 || dayOf[i] >= days || i > 0 && dayOf[i] < dayOf[i - 1]) {
                return Outcome.NOT_THERE;
            }
            load[dayOf[i]] += sack[i];
        }
        events.add(eventId);
        heaviest = 0;
        for (int l : load) {
            heaviest = Math.max(heaviest, l);
        }
        last = heaviest == lightest ? Outcome.WELL : Outcome.HEAVY;
        if (last == Outcome.WELL) {
            quest.apply(eventId, "plan", "well");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the plan is good. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperHaulLines.THANKS;
        }
        return KeeperHaulLines.line(this);
    }
}
