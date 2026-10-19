// SPDX-License-Identifier: MIT

package com.daedalus.world.brew;

import com.daedalus.world.colony.PlotState;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * The brew bench of a homestead plot: the survival-loop side of Melody Brewing.
 *
 * <ul>
 *   <li>Brewing takes one of each herb from the plot store ({@link PlotState}, the same store the Colony Ledger day
 *       book fills) and puts the tonic in it. Herbs are only spent when every herb is there.</li>
 *   <li>A cadence tonic purifies water: up to {@link #PURIFY_PER_TIER} x tier units of {@code raw_water} become
 *       {@code water} (drinkable), the mandatory water loop of the island.</li>
 *   <li>Playing a seed-song record at the jukebox teaches its found tune once ({@link #playRecord}); brewing a learned
 *       tune's exact herb order yields that tune's named tonic and bonus. An unlearned tune brews as a plain tonic.</li>
 *   <li>Every brew has an event id and counts once; a repeat changes nothing.</li>
 * </ul>
 * Pitch classes come from a {@link PitchTable} (shared with prometheus's HerbChord, BREW_SPLIT.md).
 */
public final class BrewBench {
    public static final int PURIFY_PER_TIER = 5;
    public static final String RAW_WATER = "raw_water";
    public static final String WATER = "water";

    public enum Outcome { BREWED, DUPLICATE, MISSING_HERBS, IGNORED }

    /** Result of one brew; {@code tune} is the matched learned tune or null; {@code purified} is water units made. */
    public record Brew(Outcome outcome, MelodyBrew.Tonic tonic, FoundTune tune, String item, int purified) {
    }

    private final PitchTable table;
    private final List<FoundTune> tunes;
    private final Set<String> learned = new LinkedHashSet<>();
    private final Set<String> events = new HashSet<>();

    public BrewBench(PitchTable table, List<FoundTune> tunes) {
        this.table = table;
        this.tunes = List.copyOf(tunes);
    }

    /** Plays a record at the jukebox: learns the tune whose {@code learnedFrom} is this record. Returns it, or null. */
    public FoundTune playRecord(String recordItem) {
        for (FoundTune t : tunes) {
            if (t.learnedFrom().equals(recordItem)) {
                learned.add(t.name());
                return t;
            }
        }
        return null;
    }

    public Set<String> learned() {
        return Set.copyOf(learned);
    }

    /** The learned tune with exactly this herb order, or null. */
    public FoundTune match(List<MelodyBrew.Ingredient> items) {
        List<String> order = new ArrayList<>();
        items.forEach(i -> order.add(i.herb().toLowerCase(Locale.ROOT)));
        for (FoundTune t : tunes) {
            if (!learned.contains(t.name())) {
                continue;
            }
            List<String> want = new ArrayList<>();
            t.herbs().forEach(h -> want.add(h.toLowerCase(Locale.ROOT)));
            if (want.equals(order)) {
                return t;
            }
        }
        return null;
    }

    /** Brews at this bench on this plot. */
    public Brew brew(String eventId, List<MelodyBrew.Ingredient> items, PlotState plot) {
        if (eventId == null || eventId.isBlank() || eventId.length() > 128 || items == null) {
            return new Brew(Outcome.IGNORED, null, null, null, 0);
        }
        if (events.contains(eventId)) {
            return new Brew(Outcome.DUPLICATE, null, null, null, 0);
        }
        java.util.Map<String, Integer> need = new java.util.LinkedHashMap<>();
        items.forEach(i -> need.merge(i.herb(), 1, Integer::sum));
        for (var e : need.entrySet()) {
            if (plot.count(e.getKey()) < e.getValue()) {
                return new Brew(Outcome.MISSING_HERBS, null, null, null, 0);
            }
        }
        events.add(eventId);
        need.forEach((h, n) -> plot.take(h, n));
        MelodyBrew.Tonic t = MelodyBrew.brew(items, table);
        FoundTune tune = t.noise() ? null : match(items);
        String item = tune != null ? tune.tonic() : t.tonic();
        plot.add(item, 1);
        int purified = 0;
        if (t.purifiesWater()) {
            purified = (int) Math.min(plot.count(RAW_WATER), (double) PURIFY_PER_TIER * t.tier());
            if (purified > 0) {
                plot.take(RAW_WATER, purified);
                plot.add(WATER, purified);
            }
        }
        return new Brew(Outcome.BREWED, t, tune, item, purified);
    }
}
