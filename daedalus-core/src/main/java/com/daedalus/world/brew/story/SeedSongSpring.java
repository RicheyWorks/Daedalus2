// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.story;

import com.daedalus.world.brew.BrewBench;
import com.daedalus.world.brew.FoundTune;
import com.daedalus.world.brew.MelodyBrew;
import com.daedalus.world.colony.PlotState;
import com.daedalus.world.colony.QuestProgress;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Chapter 2 of the Youtube Master Island story, "The Seed-Song Spring" (quest {@code q_seed_song_spring}).
 *
 * <p>The arks' seed-song records are scratched. Holding a record, the player brews its whole tune on the
 * {@link BrewBench} (the heard opening plus the missing cadence, in order). The right order restores the record:
 * the jukebox learns its tune ({@link BrewBench#playRecord}) and the restored tune purifies the next cloudy spring
 * of the {@link SpringChain}. A wrong order still brews (the herbs are spent) but the needle skips and the record
 * stays scratched. Quest steps run on the PORT09-twin {@link QuestProgress}:
 * restore three records, draw clean water once, then tell Keeper Oriel.
 */
public final class SeedSongSpring {
    public static final String QUEST_ID = "q_seed_song_spring";
    public static final String KEEPER = "keeper_oriel";
    public static final int RECORDS_FOR_QUEST = 3;

    public enum Outcome { RESTORED, NEEDLE_SKIPS, NO_RECORD, ALREADY_RESTORED, UNKNOWN_RECORD, MISSING_HERBS, DUPLICATE,
        IGNORED }

    /** Result of a restoration attempt; {@code brew} is the bench result, {@code spring} the spring it purified. */
    public record Restore(Outcome outcome, BrewBench.Brew brew, ScratchedRecord record, SpringChain.Spring spring) {
    }

    /** Running totals for the G12 adapter (a companion who brews with you). */
    public record Tally(int restored, int skipped, int springsPurified, int cleanDraws) {
    }

    private final BrewBench bench;
    private final SpringChain chain;
    private final Map<String, ScratchedRecord> records = new LinkedHashMap<>();
    private final Set<String> restored = new HashSet<>();
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("restore", "seed_song_record", RECORDS_FOR_QUEST),
            new QuestProgress.Step("draw_clean", "spring", 1),
            new QuestProgress.Step("talk", KEEPER, 1)));
    private int skipped;
    private int cleanDraws;

    /** One chapter on one homestead: every tune's record is scratched with a seeded scratch. */
    public SeedSongSpring(BrewBench bench, List<FoundTune> tunes, SpringChain chain, long seed) {
        this.bench = bench;
        this.chain = chain;
        for (FoundTune t : tunes) {
            records.put(t.learnedFrom(), ScratchedRecord.of(t, seed));
        }
    }

    public ScratchedRecord record(String item) {
        return records.get(item);
    }

    public List<ScratchedRecord> records() {
        return List.copyOf(records.values());
    }

    public boolean isRestored(String item) {
        return restored.contains(item);
    }

    public SpringChain chain() {
        return chain;
    }

    public QuestProgress quest() {
        return quest;
    }

    public Tally tally() {
        return new Tally(restored.size(), skipped, chain.cleanCount(), cleanDraws);
    }

    /** Tries to restore a held record by brewing {@code items} on the bench from {@code plot}'s store. */
    public Restore restore(String eventId, String recordItem, List<MelodyBrew.Ingredient> items, PlotState plot) {
        if (eventId == null || eventId.isBlank() || eventId.length() > 128 || items == null || plot == null) {
            return new Restore(Outcome.IGNORED, null, null, null);
        }
        if (events.contains(eventId)) {
            return new Restore(Outcome.DUPLICATE, null, null, null);
        }
        ScratchedRecord r = records.get(recordItem);
        if (r == null) {
            return new Restore(Outcome.UNKNOWN_RECORD, null, null, null);
        }
        if (restored.contains(recordItem)) {
            return new Restore(Outcome.ALREADY_RESTORED, null, r, null);
        }
        if (plot.count(recordItem) < 1) {
            return new Restore(Outcome.NO_RECORD, null, r, null);
        }
        BrewBench.Brew b = bench.brew(eventId, items, plot);
        switch (b.outcome()) {
            case MISSING_HERBS:
                return new Restore(Outcome.MISSING_HERBS, b, r, null);
            case DUPLICATE:
                return new Restore(Outcome.DUPLICATE, b, r, null);
            case IGNORED:
                return new Restore(Outcome.IGNORED, b, r, null);
            default:
                break;
        }
        events.add(eventId);
        if (!r.restoredBy(items)) {
            skipped++;
            return new Restore(Outcome.NEEDLE_SKIPS, b, r, null);
        }
        restored.add(recordItem);
        bench.playRecord(recordItem);
        SpringChain.Spring s = chain.purifyNext(r.tune().name());
        quest.apply(eventId, "restore", "seed_song_record");
        return new Restore(Outcome.RESTORED, b, r, s);
    }

    /** Draws at a spring; a clean draw counts for the quest. */
    public SpringChain.Draw draw(String eventId, String springId, PlotState plot) {
        SpringChain.Draw d = chain.draw(eventId, springId, plot);
        if (d.outcome() == SpringChain.Outcome.CLEAN) {
            cleanDraws++;
            quest.apply(eventId, "draw_clean", "spring");
        }
        return d;
    }

    /** Talks to Keeper Oriel: returns her line for the current state (and counts the talk step when it is due). */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", KEEPER);
            return KeeperLines.THANKS;
        }
        return KeeperLines.line(this);
    }
}
