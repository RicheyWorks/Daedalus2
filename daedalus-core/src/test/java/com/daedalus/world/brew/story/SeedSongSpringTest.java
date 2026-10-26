// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.story;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.BrewBench;
import com.daedalus.world.brew.FoundTune;
import com.daedalus.world.brew.MelodyBrew;
import com.daedalus.world.brew.PitchTable;
import com.daedalus.world.colony.PlotState;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class SeedSongSpringTest {
    static List<FoundTune> tunes;
    BrewBench bench;
    SeedSongSpring chapter;
    PlotState plot;

    static List<FoundTune> loadTunes() throws Exception {
        try (var in = SeedSongSpringTest.class.getResourceAsStream("/com/daedalus/world/brew/found_tunes.csv")) {
            return FoundTune.parseCsv(new String(in.readAllBytes(), StandardCharsets.UTF_8));
        }
    }

    static List<MelodyBrew.Ingredient> kettle(List<String> herbs) {
        return herbs.stream().map(h -> new MelodyBrew.Ingredient(h, 3)).toList();
    }

    /** Puts a record and one of each herb of its whole tune into the store. */
    static void stock(PlotState plot, FoundTune t) {
        plot.add(t.learnedFrom(), 1);
        t.herbs().forEach(h -> plot.add(h, 1));
    }

    @BeforeEach
    void setUp() throws Exception {
        tunes = loadTunes();
        bench = new BrewBench(PitchTable.ISLAND_CANON, tunes);
        chapter = new SeedSongSpring(bench, tunes, SpringChain.island(), 2026L);
        plot = new PlotState();
    }

    @Test
    void theScratchAlwaysEatsTheCadenceAndLeavesTwoNotesToHear() {
        for (long seed = 0; seed < 64; seed++) {
            for (FoundTune t : tunes) {
                ScratchedRecord r = ScratchedRecord.of(t, seed);
                assertTrue(r.missing() >= 1 && r.missing() <= 2, t.name());
                assertTrue(r.heard().size() >= 2, t.name());
                assertEquals(t.herbs().subList(0, r.heard().size()), r.heard());
                assertEquals(t.notes().subList(0, r.heard().size()), r.heardNotes());
                assertEquals(r, ScratchedRecord.of(t, seed), "seeded scratch is stable");
            }
        }
        assertEquals(12, chapter.records().size());
        assertThrows(IllegalArgumentException.class, () -> new ScratchedRecord(tunes.get(0), 3));
        assertThrows(IllegalArgumentException.class, () -> new ScratchedRecord(tunes.get(0), 0));
        assertThrows(IllegalArgumentException.class, () -> new ScratchedRecord(null, 1));
    }

    @Test
    void brewingTheWholeTuneRestoresTheRecordAndPurifiesTheNextSpring() {
        FoundTune t = tunes.get(1);
        stock(plot, t);
        assertEquals(SpringChain.Outcome.CLOUDY, chapter.draw("d0", "spring_1", plot).outcome());
        var r = chapter.restore("brew-1", t.learnedFrom(), kettle(t.herbs()), plot);
        assertEquals(SeedSongSpring.Outcome.RESTORED, r.outcome());
        assertEquals("spring_1", r.spring().id());
        assertTrue(chapter.isRestored(t.learnedFrom()));
        assertTrue(bench.learned().contains(t.name()), "the jukebox learned the mended tune");
        assertEquals(t.name(), chapter.chain().purifiedBy("spring_1"));
        assertEquals(0, plot.count(t.herbs().get(0)), "herbs were spent on the bench");
        var clean = chapter.draw("d1", "spring_1", plot);
        assertEquals(SpringChain.Outcome.CLEAN, clean.outcome());
        assertEquals(BrewBench.WATER, clean.item());
        assertEquals(SpringChain.Outcome.CLOUDY, chapter.draw("d2", "spring_2", plot).outcome());
        assertEquals("spring_2", chapter.chain().nextCloudy().id());
        assertEquals(SeedSongSpring.Outcome.ALREADY_RESTORED,
                chapter.restore("brew-2", t.learnedFrom(), kettle(t.herbs()), plot).outcome());
    }

    @Test
    void theOpeningAloneOrAWrongOrderMakesTheNeedleSkip() {
        FoundTune t = tunes.get(0);
        stock(plot, t);
        t.herbs().forEach(h -> plot.add(h, 2));
        ScratchedRecord rec = chapter.record(t.learnedFrom());
        List<String> wrong = new ArrayList<>(t.herbs());
        java.util.Collections.reverse(wrong);
        wrong.set(0, t.herbs().get(1));
        wrong.set(1, t.herbs().get(0));
        var r = chapter.restore("skip-1", t.learnedFrom(), kettle(wrong), plot);
        assertEquals(SeedSongSpring.Outcome.NEEDLE_SKIPS, r.outcome());
        assertEquals(BrewBench.Outcome.BREWED, r.brew().outcome(), "a skip still brews and spends herbs");
        assertFalse(chapter.isRestored(t.learnedFrom()));
        assertNull(chapter.chain().purifiedBy("spring_1"));
        assertFalse(rec.restoredBy(kettle(rec.heard())));
        assertFalse(rec.restoredBy(null));
        assertEquals(1, chapter.tally().skipped());
        assertEquals(SeedSongSpring.Outcome.DUPLICATE,
                chapter.restore("skip-1", t.learnedFrom(), kettle(t.herbs()), plot).outcome());
        assertEquals(SeedSongSpring.Outcome.RESTORED,
                chapter.restore("ok-1", t.learnedFrom(), kettle(t.herbs()), plot).outcome());
    }

    @Test
    void guardsSpendNothing() {
        FoundTune t = tunes.get(2);
        t.herbs().forEach(h -> plot.add(h, 1));
        var before = new java.util.HashMap<>(plot.store());
        assertEquals(SeedSongSpring.Outcome.NO_RECORD,
                chapter.restore("g1", t.learnedFrom(), kettle(t.herbs()), plot).outcome());
        assertEquals(before, plot.store());
        assertEquals(SeedSongSpring.Outcome.UNKNOWN_RECORD,
                chapter.restore("g2", "Item_YTM_Record_Nope", kettle(t.herbs()), plot).outcome());
        assertEquals(SeedSongSpring.Outcome.IGNORED, chapter.restore("", t.learnedFrom(), kettle(t.herbs()), plot).outcome());
        assertEquals(SeedSongSpring.Outcome.IGNORED, chapter.restore("g3", t.learnedFrom(), null, plot).outcome());
        PlotState bare = new PlotState();
        bare.add(t.learnedFrom(), 1);
        assertEquals(SeedSongSpring.Outcome.MISSING_HERBS,
                chapter.restore("g4", t.learnedFrom(), kettle(t.herbs()), bare).outcome());
        assertEquals(SeedSongSpring.Outcome.MISSING_HERBS,
                chapter.restore("g5", t.learnedFrom(), kettle(List.of("Doleaf")), bare).outcome());
        assertEquals(SeedSongSpring.Outcome.IGNORED,
                chapter.restore("g6", t.learnedFrom(), kettle(t.herbs()), null).outcome());
        assertEquals(new SeedSongSpring.Tally(0, 0, 0, 0), chapter.tally());
    }

    @Test
    void questRestoreThreeDrinkCleanThenTellTheKeeper() {
        assertEquals(KeeperLines.GREETING, chapter.talk("t0"));
        for (int i = 0; i < 3; i++) {
            FoundTune t = tunes.get(i);
            stock(plot, t);
            assertEquals(SeedSongSpring.Outcome.RESTORED,
                    chapter.restore("q" + i, t.learnedFrom(), kettle(t.herbs()), plot).outcome());
            if (i == 0) {
                assertEquals(String.format(KeeperLines.PROGRESS, "Homestead Well", 1, 12), chapter.talk("t1"));
            }
        }
        assertEquals(KeeperLines.DRINK, chapter.talk("t2"));
        assertFalse(chapter.quest().complete());
        chapter.draw("cloudy", "spring_4", plot);
        assertEquals(1, chapter.quest().stepIndex(), "a cloudy draw does not count");
        chapter.draw("drink", "spring_3", plot);
        assertEquals(KeeperLines.THANKS, chapter.talk("t3"));
        assertTrue(chapter.quest().complete());
        assertTrue(chapter.quest().claimReward());
        assertFalse(chapter.quest().claimReward());
        assertEquals(new SeedSongSpring.Tally(3, 0, 3, 1), chapter.tally());
        assertEquals(String.format(KeeperLines.PROGRESS, "Ferry Steps", 3, 12), chapter.talk("t4"));
    }

    @Test
    void everyRecordMendedMakesTheWholeChainRunClean() {
        for (FoundTune t : tunes) {
            stock(plot, t);
            assertEquals(SeedSongSpring.Outcome.RESTORED,
                    chapter.restore("all-" + t.name(), t.learnedFrom(), kettle(t.herbs()), plot).outcome(), t.name());
        }
        assertNull(chapter.chain().nextCloudy());
        assertEquals(12, chapter.chain().cleanCount());
        assertEquals(KeeperLines.ALL_CLEAN, KeeperLines.line(chapter));
        assertEquals(12, bench.learned().size());
        assertNull(chapter.chain().purifyNext("extra"), "a 13th tune has no cloudy spring left");
    }

    @Test
    void keeperHintsNameWhatSheHears() {
        ScratchedRecord homey = new ScratchedRecord(tunes.get(1), 1);
        assertEquals("This is alpine. I hear Doleaf, Mimint, Solthorn, Mimint, then the scratch eats 1 note. "
                + "It wants to come home: it ends on the note it began with.", KeeperLines.hint(homey));
        FoundTune lonesome = tunes.stream().filter(t -> t.name().equals("Tune_lonesome")).findFirst().orElseThrow();
        ScratchedRecord away = new ScratchedRecord(lonesome, 2);
        assertFalse(away.comesHome());
        assertTrue(KeeperLines.hint(away).endsWith("eats 2 notes. It does not come home; it ends somewhere new."));
    }

    @Test
    void springChainValidatesAndDrawsOncePerEvent() {
        assertThrows(IllegalArgumentException.class, () -> new SpringChain(List.of()));
        assertThrows(IllegalArgumentException.class, () -> new SpringChain(null));
        var a = new SpringChain.Spring("s", "S", 1);
        assertThrows(IllegalArgumentException.class, () -> new SpringChain(List.of(a, a)));
        assertThrows(IllegalArgumentException.class, () -> new SpringChain.Spring("", "S", 1));
        assertThrows(IllegalArgumentException.class, () -> new SpringChain.Spring("x", "S", 0));
        assertThrows(IllegalArgumentException.class, () -> new SpringChain.Spring(null, "S", 1));
        assertThrows(IllegalArgumentException.class, () -> new SpringChain.Spring("x", null, 1));
        SpringChain c = new SpringChain(List.of(a));
        assertEquals(SpringChain.Outcome.UNKNOWN_SPRING, c.draw("e", "nope", plot).outcome());
        assertEquals(SpringChain.Outcome.IGNORED, c.draw(null, "s", plot).outcome());
        assertEquals(SpringChain.Outcome.IGNORED, c.draw("e", "s", null).outcome());
        assertEquals(SpringChain.Outcome.IGNORED, c.draw("x".repeat(129), "s", plot).outcome());
        assertEquals(SpringChain.Outcome.CLOUDY, c.draw("e", "s", plot).outcome());
        assertEquals(SpringChain.Outcome.DUPLICATE, c.draw("e", "s", plot).outcome());
        assertEquals(1, plot.count(BrewBench.RAW_WATER));
        assertEquals(12, SpringChain.island().springs().size());
    }
}
