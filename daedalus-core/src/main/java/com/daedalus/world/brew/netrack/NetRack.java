// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.netrack;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 87 of the Youtube Master Island story, "The Net Rack" (quest {@code q_net_rack}). The jetty rack holds
 * {@code slots} nets; fishers ask for nets in a known order, and a net not on the rack means a trip to the shed (and,
 * if the rack is full, carrying one net back). {@link #fewest()} is the fewest trips, by Belady's rule (send back the
 * net needed furthest in the future); {@link #lruTrips()} is what "send back the net unused longest" (LRU) costs.
 * Naming the fewest earns credit; a WRONG count, or a rack ROOMY enough to hold every net, earns none.
 */
public final class NetRack {
    public static final String QUEST_ID = "q_net_rack";

    public enum Outcome { RIGHT, WRONG, ROOMY, MALFORMED, DUPLICATE, IGNORED }

    private final int slots;
    private final List<Integer> asks;
    private final int fewest;
    private final int lru;
    private final int kinds;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("read", "asks", 1),
            new QuestProgress.Step("count", "trips", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** A rack of 1+ slots and net asks (net numbers 0+). */
    public NetRack(int slots, List<Integer> asks) {
        if (slots < 1 || asks == null || asks.stream().anyMatch(a -> a == null || a < 0)) {
            throw new IllegalArgumentException("a rack and real nets");
        }
        this.slots = slots;
        this.asks = List.copyOf(asks);
        kinds = new HashSet<>(this.asks).size();
        int trips = 0;
        List<Integer> rack = new ArrayList<>();
        for (int i = 0; i < this.asks.size(); i++) {
            int net = this.asks.get(i);
            if (rack.contains(net)) {
                continue;
            }
            trips++;
            if (rack.size() == slots) {
                int far = -1;
                int pick = 0;
                for (int r = 0; r < rack.size(); r++) {
                    int next = nextUse(rack.get(r), i + 1);
                    if (next > far) {
                        far = next;
                        pick = r;
                    }
                }
                rack.remove(pick);
            }
            rack.add(net);
        }
        fewest = trips;
        int t = 0;
        List<Integer> recent = new ArrayList<>();
        for (int net : this.asks) {
            if (recent.remove(Integer.valueOf(net))) {
                recent.add(net);
                continue;
            }
            t++;
            if (recent.size() == slots) {
                recent.remove(0);
            }
            recent.add(net);
        }
        lru = t;
    }

    private int nextUse(int net, int from) {
        for (int j = from; j < asks.size(); j++) {
            if (asks.get(j) == net) {
                return j;
            }
        }
        return Integer.MAX_VALUE;
    }

    /** A seeded rack of 1-3 slots and 0-10 asks for nets 0-4. */
    public static NetRack seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x9E7AL);
        int k = 1 + rng.nextInt(3);
        int n = rng.nextInt(11);
        List<Integer> a = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            a.add(rng.nextInt(5));
        }
        return new NetRack(k, a);
    }

    public int slots() {
        return slots;
    }

    public List<Integer> asks() {
        return asks;
    }

    /** Fewest shed trips (Belady). */
    public int fewest() {
        return fewest;
    }

    /** Shed trips when the net unused longest goes back (LRU). */
    public int lruTrips() {
        return lru;
    }

    /** Whether the rack can hold every kind of net asked for. */
    public boolean roomy() {
        return kinds <= slots;
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

    /** Reads the day's asks: the quest's first step. */
    public void read(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "read", "asks");
        }
    }

    /** Names the fewest trips: RIGHT, WRONG, ROOMY or MALFORMED. */
    public Outcome count(String eventId, int guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (roomy()) {
            last = Outcome.ROOMY;
            return last;
        }
        if (guess < 0) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = guess;
        last = guess == fewest ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "trips");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the trips are counted. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperNetRack.THANKS;
        }
        return KeeperNetRack.line(this);
    }
}
