// SPDX-License-Identifier: MIT

package com.daedalus.world.brew;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.colony.PlotState;
import java.nio.charset.StandardCharsets;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class BrewBenchTest {
    List<FoundTune> tunes;
    BrewBench bench;
    PlotState plot;

    @BeforeEach
    void setUp() throws Exception {
        try (var in = getClass().getResourceAsStream("found_tunes.csv")) {
            tunes = FoundTune.parseCsv(new String(in.readAllBytes(), StandardCharsets.UTF_8));
        }
        bench = new BrewBench(PitchTable.ISLAND_CANON, tunes);
        plot = new PlotState();
    }

    @Test
    void theRealTuneListParsesAndEveryTuneBrewsAsWritten() {
        assertEquals(12, tunes.size());
        for (FoundTune t : tunes) {
            List<MelodyBrew.Ingredient> items = t.herbs().stream().map(h -> new MelodyBrew.Ingredient(h, 3)).toList();
            var r = MelodyBrew.brew(items);
            assertEquals(t.baseMelody(), r.melody(), t.name());
            assertEquals(t.baseEffect(), r.effect(), t.name());
            assertEquals(t.notes(), r.notes(), t.name());
        }
    }

    @Test
    void brewingSpendsHerbsFromTheStoreAndPurifiesWater() {
        plot.add("Doleaf", 2);
        plot.add("Mimint", 1);
        plot.add(BrewBench.RAW_WATER, 40);
        var b = bench.brew("brew:1", MelodyBrewTest.k(3, "Doleaf", "Mimint", "Doleaf"), plot);
        assertEquals(BrewBench.Outcome.BREWED, b.outcome());
        assertEquals(15, b.purified(), "5 x tier 3");
        assertEquals(15.0, plot.count(BrewBench.WATER));
        assertEquals(25.0, plot.count(BrewBench.RAW_WATER));
        assertEquals(0.0, plot.count("Doleaf"));
        assertEquals(1.0, plot.count("Item_YTM_Tonic_Seventh_T3"));
        assertEquals(BrewBench.Outcome.DUPLICATE, bench.brew("brew:1", MelodyBrewTest.k(3, "Doleaf", "Mimint", "Doleaf"), plot).outcome());
    }

    @Test
    void missingHerbsSpendNothing() {
        plot.add("Doleaf", 1);
        plot.add("Mimint", 1);
        var b = bench.brew("brew:2", MelodyBrewTest.k(2, "Doleaf", "Mimint", "Doleaf"), plot);
        assertEquals(BrewBench.Outcome.MISSING_HERBS, b.outcome());
        assertEquals(1.0, plot.count("Doleaf"));
        assertEquals(BrewBench.Outcome.IGNORED, bench.brew("", MelodyBrewTest.k(2, "Doleaf"), plot).outcome());
    }

    @Test
    void aFoundTuneNeedsItsRecordPlayedFirst() {
        FoundTune desert = tunes.stream().filter(t -> t.name().equals("Tune_desert_thirst")).findFirst().orElseThrow();
        var items = desert.herbs().stream().map(h -> new MelodyBrew.Ingredient(h, 2)).toList();
        desert.herbs().forEach(h -> plot.add(h, 2));
        var plain = bench.brew("a", items, plot);
        assertNull(plain.tune(), "not learned yet: plain tonic");
        assertTrue(plain.item().startsWith("Item_YTM_Tonic_Seventh"));
        assertNotNull(bench.playRecord(desert.learnedFrom()));
        assertNull(bench.playRecord("Item_YTM_Record_Unknown"));
        assertTrue(bench.learned().contains("Tune_desert_thirst"));
        var found = bench.brew("b", items, plot);
        assertEquals(desert, found.tune());
        assertEquals(desert.tonic(), found.item());
        assertEquals(1.0, plot.count(desert.tonic()));
    }

    @Test
    void badCsvIsRejected() {
        assertThrows(IllegalArgumentException.class, () -> FoundTune.parseCsv("h\nonly,three,cols\n"));
        assertEquals(0, FoundTune.parseCsv("header\n\n").size());
    }
}
