// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.bakehouse;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 35 of the Youtube Master Island story, "The Bakehouse" (quest {@code q_bakehouse}). Every loaf is kneaded
 * on the one table, then baked in the one oven, and both keep the same loaf order. {@link #soonest()} is the exact
 * least finishing hour by Johnson's rule for the two-stage flow shop. Baking in an order that finishes then earns
 * credit; a later finish does not, and baking before every loaf is queued is {@link Outcome#UNFINISHED}.
 */
public final class Bakehouse {
    public static final String QUEST_ID = "q_bakehouse";

    public enum Outcome { QUEUED, ALREADY, NOT_THERE, UNFINISHED, WELL, LATE, DUPLICATE, IGNORED }

    private final int[] knead;
    private final int[] bake;
    private final int soonest;
    private final List<Integer> order = new ArrayList<>();
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("queue", "loaf", 1),
            new QuestProgress.Step("bake", "well", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private Outcome last;

    public Bakehouse(int[] knead, int[] bake) {
        if (knead == null || bake == null || knead.length == 0 || knead.length != bake.length) {
            throw new IllegalArgumentException("one knead and one bake time per loaf");
        }
        for (int i = 0; i < knead.length; i++) {
            if (knead[i] <= 0 || bake[i] <= 0) {
                throw new IllegalArgumentException("times are positive hours");
            }
        }
        this.knead = knead.clone();
        this.bake = bake.clone();
        soonest = finish(johnson());
    }

    /** A seeded batch of 3-7 loaves, 1-9 hours to knead and to bake. */
    public static Bakehouse seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xBA4EL);
        int n = 3 + rng.nextInt(5);
        int[] k = new int[n];
        int[] b = new int[n];
        for (int i = 0; i < n; i++) {
            k[i] = 1 + rng.nextInt(9);
            b[i] = 1 + rng.nextInt(9);
        }
        return new Bakehouse(k, b);
    }

    /** Johnson's rule: loaves quicker to knead than bake go first by knead time, the rest last by bake time. */
    List<Integer> johnson() {
        List<Integer> front = new ArrayList<>();
        List<Integer> back = new ArrayList<>();
        for (int i = 0; i < knead.length; i++) {
            (knead[i] <= bake[i] ? front : back).add(i);
        }
        front.sort((a, b) -> Integer.compare(knead[a], knead[b]));
        back.sort((a, b) -> Integer.compare(bake[b], bake[a]));
        front.addAll(back);
        return front;
    }

    /** The hour the last loaf leaves the oven for this order. */
    public int finish(List<Integer> loafOrder) {
        int table = 0;
        int oven = 0;
        for (int i : loafOrder) {
            table += knead[i];
            oven = Math.max(oven, table) + bake[i];
        }
        return oven;
    }

    public int loaves() {
        return knead.length;
    }

    /** The soonest hour every loaf can be out of the oven. */
    public int soonest() {
        return soonest;
    }

    public int queued() {
        return order.size();
    }

    /** The finishing hour of the queued order. */
    public int finish() {
        return finish(order);
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    private Outcome guard(String eventId) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        return events.contains(eventId) ? Outcome.DUPLICATE : null;
    }

    /** Puts a loaf next in the queue. */
    public Outcome queue(String eventId, int loaf) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (loaf < 0 || loaf >= knead.length) {
            return Outcome.NOT_THERE;
        }
        if (order.contains(loaf)) {
            return Outcome.ALREADY;
        }
        events.add(eventId);
        order.add(loaf);
        last = null;
        quest.apply(eventId, "queue", "loaf");
        return Outcome.QUEUED;
    }

    /** Clears the queue to plan again. */
    public void restart() {
        order.clear();
        last = null;
    }

    /** Fires the oven: UNFINISHED until every loaf is queued, then WELL at the soonest hour, else LATE. */
    public Outcome bake(String eventId) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (order.size() < knead.length) {
            return Outcome.UNFINISHED;
        }
        events.add(eventId);
        last = finish() == soonest ? Outcome.WELL : Outcome.LATE;
        if (last == Outcome.WELL) {
            quest.apply(eventId, "bake", "well");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the loaves baked well. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperBakeLines.THANKS;
        }
        return KeeperBakeLines.line(this);
    }
}
