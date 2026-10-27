// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.casks;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;
import java.util.TreeSet;

/**
 * Chapter 21 of the Youtube Master Island story, "The Water Casks" (quest {@code q_water_casks}). At the landfall
 * spring the boat's tank takes an exact {@link #measure()}; the casks come in a few fixed sizes and any number of each
 * may be poured. The filling is neat when it hits the measure with the fewest casks; {@link #fewest()} is exact
 * unbounded coin-change DP, and {@link #bestPour()} walks it back.
 */
public final class WaterCasks {
    public static final String QUEST_ID = "q_water_casks";
    public static final int CASKS_TO_POUR = 4;

    public enum Outcome { POURED, EMPTIED, NOT_POURED, UNKNOWN, NEAT, WASTEFUL, SHORT, OVER, NO_FILL, DUPLICATE,
        IGNORED }

    private final List<Integer> sizes;
    private final int measure;
    private final int[] fewest;
    private final int[] lastCask;
    private final List<Integer> poured = new ArrayList<>();
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("pour", "cask", CASKS_TO_POUR),
            new QuestProgress.Step("seal", "neat", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private Outcome last;

    public WaterCasks(int measure, List<Integer> caskSizes) {
        if (measure <= 0 || caskSizes.isEmpty()) {
            throw new IllegalArgumentException("need a measure and casks");
        }
        TreeSet<Integer> set = new TreeSet<>();
        for (int s : caskSizes) {
            if (s <= 0 || !set.add(s)) {
                throw new IllegalArgumentException("bad cask size " + s);
            }
        }
        this.sizes = List.copyOf(set);
        this.measure = measure;
        fewest = new int[measure + 1];
        lastCask = new int[measure + 1];
        for (int v = 1; v <= measure; v++) {
            fewest[v] = -1;
            for (int s : sizes) {
                if (s <= v && fewest[v - s] >= 0 && (fewest[v] < 0 || fewest[v - s] + 1 < fewest[v])) {
                    fewest[v] = fewest[v - s] + 1;
                    lastCask[v] = s;
                }
            }
        }
    }

    /** A seeded spring: 2-4 cask sizes from 2-11 and a measure of 10-40. */
    public static WaterCasks seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xCA5C5L);
        TreeSet<Integer> set = new TreeSet<>();
        int n = 2 + rng.nextInt(3);
        while (set.size() < n) {
            set.add(2 + rng.nextInt(10));
        }
        return new WaterCasks(10 + rng.nextInt(31), new ArrayList<>(set));
    }

    public List<Integer> sizes() {
        return sizes;
    }

    public int measure() {
        return measure;
    }

    /** The fewest casks that fill the measure exactly, or -1 when no mix can. */
    public int fewest() {
        return fewest[measure];
    }

    public boolean fillable() {
        return fewest[measure] >= 0;
    }

    /** One fewest-cask pour, largest last, or empty when the measure can't be filled. */
    public List<Integer> bestPour() {
        List<Integer> out = new ArrayList<>();
        if (!fillable()) {
            return out;
        }
        for (int v = measure; v > 0; v -= lastCask[v]) {
            out.add(0, lastCask[v]);
        }
        return out;
    }

    public List<Integer> poured() {
        return List.copyOf(poured);
    }

    public int level() {
        return poured.stream().mapToInt(Integer::intValue).sum();
    }

    public QuestProgress quest() {
        return quest;
    }

    public Outcome last() {
        return last;
    }

    private Outcome guard(String eventId, Integer size) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        return size == null || sizes.contains(size) ? null : Outcome.UNKNOWN;
    }

    /** Pours one cask of the given size into the tank. */
    public Outcome pour(String eventId, int size) {
        Outcome g = guard(eventId, size);
        if (g != null) {
            return g;
        }
        events.add(eventId);
        poured.add(size);
        last = null;
        quest.apply(eventId, "pour", "cask");
        return Outcome.POURED;
    }

    /** Bails one cask of the given size back out. */
    public Outcome empty(String eventId, int size) {
        Outcome g = guard(eventId, size);
        if (g != null) {
            return g;
        }
        if (!poured.remove(Integer.valueOf(size))) {
            return Outcome.NOT_POURED;
        }
        events.add(eventId);
        last = null;
        return Outcome.EMPTIED;
    }

    /** Seals the tank: NO_FILL (no credit) if no mix can hit the measure, SHORT/OVER if off it, else NEAT with the
     * fewest casks or WASTEFUL with more. */
    public Outcome seal(String eventId) {
        Outcome g = guard(eventId, null);
        if (g != null) {
            return g;
        }
        if (!fillable()) {
            events.add(eventId);
            last = Outcome.NO_FILL;
            return last;
        }
        if (level() != measure) {
            return level() < measure ? Outcome.SHORT : Outcome.OVER;
        }
        events.add(eventId);
        last = poured.size() == fewest() ? Outcome.NEAT : Outcome.WASTEFUL;
        if (last == Outcome.NEAT) {
            quest.apply(eventId, "seal", "neat");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once a filling was neat. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperCaskLines.THANKS;
        }
        return KeeperCaskLines.line(this);
    }
}
