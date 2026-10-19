// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.hunt;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.BrewBench;
import com.daedalus.world.brew.FoundTune;
import com.daedalus.world.brew.MelodyBrew;
import com.daedalus.world.brew.PitchTable;
import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.brew.story.SpringChain;
import com.daedalus.world.colony.PlotState;
import java.nio.charset.StandardCharsets;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class RecordHuntTest {
    List<FoundTune> tunes;
    List<String> records;
    PlotState plot;

    @BeforeEach
    void setUp() throws Exception {
        try (var in = getClass().getResourceAsStream("/com/daedalus/world/brew/found_tunes.csv")) {
            tunes = FoundTune.parseCsv(new String(in.readAllBytes(), StandardCharsets.UTF_8));
        }
        records = tunes.stream().map(FoundTune::learnedFrom).toList();
        plot = new PlotState();
    }

    /** Walks the Archivist's hints until the record is underfoot, then searches; returns bridges crossed. */
    static int followHints(RecordHunt h, PlotState plot, String tag) {
        int crossed = 0;
        RecordHunt.Hint hint = h.hint();
        while (hint.distance() > 0) {
            assertEquals(RecordHunt.Outcome.WALKED, h.walk(tag + crossed, hint.toward()).outcome());
            crossed++;
            hint = h.hint();
        }
        assertEquals(RecordHunt.Outcome.FOUND, h.search(tag + "-s", plot).outcome());
        return crossed;
    }

    @Test
    void seededMapsAreConnectedStableAndLoopy() {
        for (long seed = 0; seed < 40; seed++) {
            for (int n : new int[] {4, 13, 30, 64}) {
                FragmentMap m = FragmentMap.seeded(seed, n);
                FragmentMap again = FragmentMap.seeded(seed, n);
                for (int a = 0; a < n; a++) {
                    assertEquals(m.neighbours(a), again.neighbours(a));
                    assertTrue(m.distance(FragmentMap.HOME, a) >= 0, "reachable");
                    for (int b : m.neighbours(a)) {
                        assertTrue(m.bridged(b, a), "bridges go both ways");
                    }
                }
            }
        }
        assertThrows(IllegalArgumentException.class, () -> FragmentMap.seeded(1, 3));
        assertThrows(IllegalArgumentException.class, () -> FragmentMap.seeded(1, 65));
        assertFalse(FragmentMap.seeded(1, 8).bridged(-1, 0));
    }

    @Test
    void theArchivistsBridgeAlwaysShortensTheWay() {
        for (long seed = 0; seed < 30; seed++) {
            FragmentMap m = FragmentMap.seeded(seed, 24);
            for (int a = 0; a < m.size(); a++) {
                for (int b = 0; b < m.size(); b++) {
                    int step = m.nextStep(a, b);
                    if (a == b) {
                        assertEquals(a, step);
                    } else {
                        assertTrue(m.bridged(a, step));
                        assertEquals(m.distance(a, b) - 1, m.distance(step, b));
                    }
                }
            }
        }
    }

    @Test
    void recordsScatterOverDistinctFragmentsNeverTheHomestead() {
        RecordHunt h = new RecordHunt(FragmentMap.seeded(7, 16), records, 7, 10);
        Set<Integer> spots = new HashSet<>();
        for (String r : records) {
            int f = h.whereIs(r);
            assertNotEquals(FragmentMap.HOME, f);
            assertTrue(spots.add(f), "distinct while fragments last");
        }
        RecordHunt crowded = new RecordHunt(FragmentMap.seeded(7, 5), records, 7, 10);
        records.forEach(r -> assertTrue(crowded.whereIs(r) >= 1 && crowded.whereIs(r) < 5));
        assertEquals(-1, h.whereIs("Item_YTM_Record_Nope"));
        assertThrows(IllegalArgumentException.class, () -> new RecordHunt(FragmentMap.seeded(1, 8), List.of(), 1, 5));
        assertThrows(IllegalArgumentException.class, () -> new RecordHunt(FragmentMap.seeded(1, 8), null, 1, 5));
        assertThrows(IllegalArgumentException.class, () -> new RecordHunt(FragmentMap.seeded(1, 8), records, 1, 0));
        assertThrows(IllegalArgumentException.class,
                () -> new RecordHunt(FragmentMap.seeded(1, 8), List.of("a", "a"), 1, 5));
    }

    @Test
    void followingTheHintsFindsEveryRecordInExactlyItsDistance() {
        RecordHunt h = new RecordHunt(FragmentMap.seeded(2026, 20), records, 2026, 1000);
        int i = 0;
        while (h.remaining() > 0) {
            RecordHunt.Hint hint = h.hint();
            int d = hint.distance();
            int before = h.found().size();
            assertEquals(d, followHints(h, plot, "r" + i++));
            assertTrue(h.found().size() > before);
        }
        assertNull(h.hint());
        records.forEach(r -> assertEquals(1, plot.count(r), r));
        assertEquals(ArchivistLines.EMPTY, ArchivistLines.line(h));
    }

    @Test
    void bridgesStaminaAndDaysGateTheWalk() {
        FragmentMap m = FragmentMap.of(4, new int[][] {{0, 1}, {1, 2}, {2, 3}});
        RecordHunt h = new RecordHunt(m, List.of("rec"), 1, 2);
        assertEquals(RecordHunt.Outcome.NO_BRIDGE, h.walk("w0", 2).outcome());
        assertEquals(RecordHunt.Outcome.WALKED, h.walk("w1", 1).outcome());
        assertEquals(RecordHunt.Outcome.DUPLICATE, h.walk("w1", 2).outcome());
        assertEquals(RecordHunt.Outcome.WALKED, h.walk("w2", 2).outcome());
        assertEquals(0, h.stamina());
        assertEquals(ArchivistLines.TIRED.equals(ArchivistLines.line(h)), h.whereIs("rec") != 2);
        assertEquals(RecordHunt.Outcome.TIRED, h.walk("w3", 3).outcome());
        assertEquals(RecordHunt.Outcome.TIRED, h.search("s0", plot).outcome());
        assertEquals(RecordHunt.Outcome.RESTED, h.rest(1).outcome());
        assertEquals(RecordHunt.Outcome.DUPLICATE, h.rest(1).outcome());
        assertEquals(2, h.stamina());
        assertEquals(1, h.day());
        assertEquals(RecordHunt.Outcome.IGNORED, h.walk("", 1).outcome());
        assertEquals(RecordHunt.Outcome.IGNORED, h.search("x".repeat(129), plot).outcome());
        assertEquals(RecordHunt.Outcome.IGNORED, h.search("s1", null).outcome());
        var s = h.search("s2", plot);
        assertEquals(h.whereIs("rec") == 2 ? RecordHunt.Outcome.FOUND : RecordHunt.Outcome.NOTHING_HERE, s.outcome());
        assertEquals(RecordHunt.Outcome.DUPLICATE, h.search("s2", plot).outcome());
        assertThrows(IllegalArgumentException.class, () -> FragmentMap.of(3, new int[][] {{0, 1}}));
        assertThrows(IllegalArgumentException.class, () -> FragmentMap.of(3, new int[][] {{0, 0}}));
        assertThrows(IllegalArgumentException.class, () -> FragmentMap.of(3, new int[][] {{0, 5}}));
        assertThrows(IllegalArgumentException.class, () -> FragmentMap.of(3, new int[][] {{0}}));
        assertThrows(IllegalArgumentException.class, () -> FragmentMap.of(0, new int[][] {}));
        assertThrows(IllegalArgumentException.class, () -> FragmentMap.of(2, new int[][] {{-1, 0}}));
    }

    @Test
    void archivistHumsByDistance() {
        FragmentMap line = FragmentMap.of(7, new int[][] {{0, 1}, {1, 2}, {2, 3}, {3, 4}, {4, 5}, {5, 6}});
        // one record, placed by seed; find a seed that puts it at the far end
        long seed = 0;
        while (new RecordHunt(line, List.of("rec"), seed, 50).whereIs("rec") != 6) {
            seed++;
        }
        RecordHunt h = new RecordHunt(line, List.of("rec"), seed, 50);
        assertEquals(String.format(ArchivistLines.FAINT, 6, "Reed Shelf"), ArchivistLines.line(h));
        for (int f = 1; f <= 3; f++) {
            h.walk("w" + f, f);
        }
        assertEquals(String.format(ArchivistLines.WARMER, 3, "Bell Ledge"), ArchivistLines.line(h));
        h.walk("w4", 4);
        h.walk("w5", 5);
        assertEquals(String.format(ArchivistLines.ONE_BRIDGE, "Lantern Isle"), ArchivistLines.line(h));
        h.walk("w6", 6);
        assertEquals(ArchivistLines.UNDERFOOT, h.talk("t-far"));
        assertEquals("Homestead", FragmentMap.name(0));
        assertEquals("Reed Shelf 2", FragmentMap.name(16));
    }

    @Test
    void questFindThreeCarryThemHomeAndTellTheArchivistThenMendThem() {
        RecordHunt h = new RecordHunt(FragmentMap.seeded(11, 12), records, 11, 1000);
        for (int i = 0; h.found().size() < RecordHunt.RECORDS_FOR_QUEST; i++) {
            followHints(h, plot, "q" + i);
        }
        assertEquals(1, h.quest().stepIndex(), "three found: carry them home");
        assertNotEquals(ArchivistLines.THANKS, h.talk("early"));
        FragmentMap m = h.map();
        int k = 0;
        while (h.at() != FragmentMap.HOME) {
            h.walk("home" + k++, m.nextStep(h.at(), FragmentMap.HOME));
        }
        assertEquals(2, h.quest().stepIndex());
        assertEquals(ArchivistLines.THANKS, h.talk("t1"));
        assertTrue(h.quest().complete());
        assertTrue(h.quest().claimReward());
        assertFalse(h.quest().claimReward());

        // Daedalus tie-in: the records found by the hunt are the ones the G33 Seed-Song Spring mends.
        BrewBench bench = new BrewBench(PitchTable.ISLAND_CANON, tunes);
        SeedSongSpring chapter2 = new SeedSongSpring(bench, tunes, SpringChain.island(), 11);
        int mended = 0;
        for (FoundTune t : tunes) {
            if (!h.found().contains(t.learnedFrom())) {
                continue;
            }
            t.herbs().forEach(x -> plot.add(x, 1));
            var r = chapter2.restore("mend-" + t.name(), t.learnedFrom(),
                    t.herbs().stream().map(x -> new MelodyBrew.Ingredient(x, 3)).toList(), plot);
            assertEquals(SeedSongSpring.Outcome.RESTORED, r.outcome(), t.name());
            mended++;
        }
        assertEquals(h.found().size(), mended);
        assertEquals(mended, chapter2.chain().cleanCount());
    }
}
