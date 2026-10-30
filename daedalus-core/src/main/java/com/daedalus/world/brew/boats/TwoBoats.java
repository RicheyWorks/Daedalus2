// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.boats;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 20 of the Youtube Master Island story, "The Two Boats" (quest {@code q_two_boats}). At the first landfall the
 * cargo is split between boat A and boat B. The crossing is level when the weight difference is the smallest possible;
 * {@link #bestDifference()} is found exactly by subset-sum DP, and {@link #bestSplit()} walks the table back.
 */
public final class TwoBoats {
    public static final String QUEST_ID = "q_two_boats";
    public static final int CRATES_TO_LOAD = 4;
    static final String[] NAMES = {"flour", "rope", "lamp oil", "nails", "seed", "salt fish", "tar", "linen", "kettles",
        "tools"};

    public enum Boat { A, B }

    public enum Outcome { LOADED, MOVED, UNLOADED, NOT_LOADED, UNKNOWN, LEVEL, LISTING, ASHORE, DUPLICATE, IGNORED }

    private final Map<String, Crate> cargo = new LinkedHashMap<>();
    private final Map<String, Boat> loaded = new LinkedHashMap<>();
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("load", "crate", CRATES_TO_LOAD),
            new QuestProgress.Step("cross", "level", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private final int best;
    private final List<Crate> bestSplit;
    private Outcome last;

    public TwoBoats(List<Crate> crates) {
        if (crates.isEmpty()) {
            throw new IllegalArgumentException("no cargo");
        }
        for (Crate c : crates) {
            if (cargo.put(c.name(), c) != null) {
                throw new IllegalArgumentException("duplicate crate " + c.name());
            }
        }
        List<Crate> list = List.copyOf(cargo.values());
        bestSplit = List.copyOf(split(list));
        int a = bestSplit.stream().mapToInt(Crate::weight).sum();
        best = total() - 2 * a;
    }

    /** A seeded landfall: 6-10 crates weighing 1-20 stone each. */
    public static TwoBoats seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x2B0A75L);
        int n = 6 + rng.nextInt(5);
        List<Crate> out = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            out.add(new Crate(NAMES[i], 1 + rng.nextInt(20)));
        }
        return new TwoBoats(out);
    }

    /**
     * Subset-sum DP: reach[i][s] says the first i crates can make s. The lighter boat takes the largest reachable s up
     * to half the total; walking the table back names its crates.
     */
    static List<Crate> split(List<Crate> crates) {
        int total = crates.stream().mapToInt(Crate::weight).sum();
        int half = total / 2;
        boolean[][] reach = new boolean[crates.size() + 1][half + 1];
        reach[0][0] = true;
        for (int i = 1; i <= crates.size(); i++) {
            int w = crates.get(i - 1).weight();
            for (int s = 0; s <= half; s++) {
                reach[i][s] = reach[i - 1][s] || (s >= w && reach[i - 1][s - w]);
            }
        }
        int s = half;
        while (!reach[crates.size()][s]) {
            s--;
        }
        List<Crate> out = new ArrayList<>();
        for (int i = crates.size(); i > 0; i--) {
            if (!reach[i - 1][s]) {
                Crate c = crates.get(i - 1);
                out.add(0, c);
                s -= c.weight();
            }
        }
        return out;
    }

    public List<Crate> cargo() {
        return List.copyOf(cargo.values());
    }

    public int total() {
        return cargo.values().stream().mapToInt(Crate::weight).sum();
    }

    /** The smallest possible weight difference between the boats. */
    public int bestDifference() {
        return best;
    }

    /** The crates for the lighter boat in one best split. */
    public List<Crate> bestSplit() {
        return bestSplit;
    }

    public int weight(Boat b) {
        int w = 0;
        for (Map.Entry<String, Boat> e : loaded.entrySet()) {
            if (e.getValue() == b) {
                w += cargo.get(e.getKey()).weight();
            }
        }
        return w;
    }

    public int difference() {
        return Math.abs(weight(Boat.A) - weight(Boat.B));
    }

    /** Crates still on the beach. */
    public List<Crate> ashore() {
        return cargo.values().stream().filter(c -> !loaded.containsKey(c.name())).toList();
    }

    public Map<String, Boat> loaded() {
        return Map.copyOf(loaded);
    }

    public QuestProgress quest() {
        return quest;
    }

    public Outcome last() {
        return last;
    }

    private Outcome guard(String eventId, String crate) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        return crate == null || cargo.containsKey(crate) ? null : Outcome.UNKNOWN;
    }

    /** Loads a crate onto a boat, or moves it across if it is already in the other one. */
    public Outcome load(String eventId, String crate, Boat boat) {
        Outcome g = guard(eventId, crate);
        if (g != null) {
            return g;
        }
        if (crate == null || boat == null) {
            return Outcome.UNKNOWN;
        }
        events.add(eventId);
        last = null;
        Boat was = loaded.put(crate, boat);
        if (was == null) {
            quest.apply(eventId, "load", "crate");
            return Outcome.LOADED;
        }
        return Outcome.MOVED;
    }

    /** Carries a crate back onto the beach. */
    public Outcome unload(String eventId, String crate) {
        Outcome g = guard(eventId, crate);
        if (g != null) {
            return g;
        }
        if (crate == null || loaded.remove(crate) == null) {
            return Outcome.NOT_LOADED;
        }
        events.add(eventId);
        last = null;
        return Outcome.UNLOADED;
    }

    /** Pushes off: ASHORE while crates are left, LEVEL (quest credit) at the best difference, else LISTING. */
    public Outcome cross(String eventId) {
        Outcome g = guard(eventId, null);
        if (g != null) {
            return g;
        }
        if (!ashore().isEmpty()) {
            return Outcome.ASHORE;
        }
        events.add(eventId);
        last = difference() == best ? Outcome.LEVEL : Outcome.LISTING;
        if (last == Outcome.LEVEL) {
            quest.apply(eventId, "cross", "level");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once a crossing was level. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperBoatLines.THANKS;
        }
        return KeeperBoatLines.line(this);
    }
}
