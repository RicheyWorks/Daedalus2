// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.exchange;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.BrewBench;
import com.daedalus.world.brew.FoundTune;
import com.daedalus.world.brew.MelodyBrew;
import com.daedalus.world.brew.PitchTable;
import com.daedalus.world.brew.hunt.FragmentMap;
import com.daedalus.world.brew.stones.BridgeLedger;
import com.daedalus.world.brew.stones.ChoirStones;
import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.brew.story.SpringChain;
import com.daedalus.world.colony.PlotState;
import java.nio.charset.StandardCharsets;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class RecordExchangeTest {
    List<FoundTune> tunes;
    SeedSongSpring songs;
    RecordExchange x;
    PlotState plot;

    String mend(int i) {
        FoundTune t = tunes.get(i);
        plot.add(t.learnedFrom(), 1);
        t.herbs().forEach(h -> plot.add(h, 1));
        assertEquals(SeedSongSpring.Outcome.RESTORED, songs.restore("mend-" + i, t.learnedFrom(),
                t.herbs().stream().map(h -> new MelodyBrew.Ingredient(h, 3)).toList(), plot).outcome());
        return t.learnedFrom();
    }

    @BeforeEach
    void setUp() throws Exception {
        try (var in = getClass().getResourceAsStream("/com/daedalus/world/brew/found_tunes.csv")) {
            tunes = FoundTune.parseCsv(new String(in.readAllBytes(), StandardCharsets.UTF_8));
        }
        songs = new SeedSongSpring(new BrewBench(PitchTable.ISLAND_CANON, tunes), tunes, SpringChain.island(), 9);
        x = new RecordExchange(songs, tunes, Trader.island(), 9);
        plot = new PlotState();
    }

    final java.util.Set<String> used = new java.util.HashSet<>();

    /** A record this trader does not want today and not used yet in the test. */
    String unwanted(String trader) {
        for (FoundTune t : tunes) {
            if (!x.wantsToday(trader).contains(t.learnedFrom()) && used.add(t.learnedFrom())) {
                return t.learnedFrom();
            }
        }
        throw new AssertionError();
    }

    @Test
    void onlyMendedRecordsPressAndOnlyOneCopyADay() {
        String rec = tunes.get(0).learnedFrom();
        assertEquals(RecordExchange.Outcome.NOT_RESTORED, x.press("p0", rec, plot));
        mend(0);
        assertEquals(RecordExchange.Outcome.PRESSED, x.press("p1", rec, plot));
        assertEquals(1, plot.count(RecordExchange.copyOf(rec)));
        assertEquals(RecordExchange.Outcome.PRESSED_TODAY, x.press("p2", rec, plot));
        assertEquals(RecordExchange.Outcome.DUPLICATE, x.press("p1", rec, plot));
        assertEquals(RecordExchange.Outcome.UNKNOWN_TUNE, x.press("p3", "Item_YTM_Record_Nope", plot));
        assertEquals(RecordExchange.Outcome.IGNORED, x.press("", rec, plot));
        assertEquals(RecordExchange.Outcome.IGNORED, x.press("p4", rec, null));
        x.nextDay();
        assertEquals(2, x.day());
        assertEquals(RecordExchange.Outcome.PRESSED, x.press("p5", rec, plot));
        assertEquals(2, plot.count(RecordExchange.copyOf(rec)));
    }

    @Test
    void priceIsNotesPlusCadenceDoubledWhenWantedHalvedPerRepeat() {
        for (FoundTune t : tunes) {
            String trader = "dov";
            List<Integer> n = t.notes();
            int base = n.size() + (n.get(0).equals(n.get(n.size() - 1)) ? 1 : 0);
            boolean wanted = x.wantsToday(trader).contains(t.learnedFrom());
            assertEquals(wanted ? 2 * base : base, x.price(trader, t.learnedFrom()), t.name());
        }
        assertEquals(0, x.price("nobody", tunes.get(0).learnedFrom()));
        assertEquals(0, x.price("dov", "Item_YTM_Record_Nope"));
        // Tune_homestead_regen: 4 notes, comes home -> 5.
        int idx = 0;
        String rec = mend(idx);
        String trader = "pell";
        while (x.wantsToday(trader).contains(rec)) {
            x.nextDay();
        }
        int[] expect = {5, 2, 1, 0};
        for (int i = 0; i < expect.length; i++) {
            assertEquals(expect[i], x.price(trader, rec), "copy " + i);
            assertEquals(RecordExchange.Outcome.PRESSED, x.press("pr" + i, rec, plot));
            var tr = x.trade("tr" + i, trader, rec, plot);
            assertEquals(expect[i] > 0 ? RecordExchange.Outcome.TRADED : RecordExchange.Outcome.REFUSED, tr.outcome());
            x.nextDay();
            while (x.wantsToday(trader).contains(rec)) {
                x.nextDay();
            }
        }
        assertEquals(8, plot.count("rope"));
        assertEquals(1, plot.count(RecordExchange.copyOf(rec)), "a refused copy stays in the store");
    }

    @Test
    void wantsAreSeededDistinctAndChangeDaily() {
        for (Trader t : Trader.island()) {
            List<String> w = x.wantsToday(t.id());
            assertEquals(t.wants(), w.size());
            assertEquals(w.size(), w.stream().distinct().count());
            assertEquals(w, new RecordExchange(songs, tunes, Trader.island(), 9).wantsToday(t.id()));
        }
        assertEquals(List.of(), x.wantsToday("nobody"));
        boolean changed = false;
        List<String> d1 = x.wantsToday("pell");
        for (int d = 0; d < 10 && !changed; d++) {
            x.nextDay();
            changed = !x.wantsToday("pell").equals(d1);
        }
        assertTrue(changed);
        assertThrows(IllegalArgumentException.class, () -> new Trader("", "x", "rope", 1));
        assertThrows(IllegalArgumentException.class, () -> new Trader("a", null, "rope", 1));
        assertThrows(IllegalArgumentException.class, () -> new Trader("a", "x", "", 1));
        assertThrows(IllegalArgumentException.class, () -> new Trader("a", "x", "rope", -1));
        assertThrows(IllegalArgumentException.class, () -> new Trader(null, "x", "rope", 1));
        assertThrows(IllegalArgumentException.class, () -> new Trader("a", "x", null, 1));
    }

    @Test
    void tradeGuards() {
        String rec = mend(1);
        assertEquals(RecordExchange.Outcome.NO_COPY, x.trade("t0", "ida", rec, plot).outcome());
        x.press("p", rec, plot);
        assertEquals(RecordExchange.Outcome.UNKNOWN_TRADER, x.trade("t1", "zed", rec, plot).outcome());
        assertEquals(RecordExchange.Outcome.UNKNOWN_TUNE, x.trade("t2", "ida", "Item_YTM_Record_Nope", plot).outcome());
        assertEquals(RecordExchange.Outcome.IGNORED, x.trade("", "ida", rec, plot).outcome());
        assertEquals(RecordExchange.Outcome.IGNORED, x.trade("t3", "ida", rec, null).outcome());
        var ok = x.trade("t4", "ida", rec, plot);
        assertEquals(RecordExchange.Outcome.TRADED, ok.outcome());
        assertEquals("choir_stone_blank", ok.good());
        assertEquals(RecordExchange.Outcome.DUPLICATE, x.trade("t4", "ida", rec, plot).outcome());
        assertEquals(4, x.traders().size());
    }

    @Test
    void questFourTradesThenTwoWantedThenPell() {
        assertEquals(TraderLines.GREETING, x.talk("hi"));
        for (int i = 0; i < 12; i++) {
            mend(i);
        }
        int trades = 0;
        int n = 0;
        for (Trader t : Trader.island()) {
            String rec = unwanted(t.id());
            x.press("q-p" + n, rec, plot);
            assertEquals(RecordExchange.Outcome.TRADED, x.trade("q-t" + n++, t.id(), rec, plot).outcome());
            trades++;
            if (trades == 1) {
                assertEquals(String.format(TraderLines.MORE, 1, ""), TraderLines.line(x));
            }
        }
        assertEquals(1, x.quest().stepIndex());
        assertEquals(String.format(TraderLines.WANTED, 2), TraderLines.line(x));
        x.nextDay();
        for (String trader : List.of("pell", "mora")) {
            String rec = x.wantsToday(trader).get(0);
            assertEquals(RecordExchange.Outcome.PRESSED, x.press("w-p" + trader, rec, plot));
            var tr = x.trade("w-t" + trader, trader, rec, plot);
            assertTrue(tr.wanted());
            assertEquals(RecordExchange.Outcome.TRADED, tr.outcome());
        }
        assertEquals(TraderLines.THANKS, x.talk("bye"));
        assertTrue(x.quest().complete());
        assertEquals(TraderLines.DONE, x.talk("again"));
        assertTrue(x.quest().claimReward());
        assertFalse(x.quest().claimReward());
        assertTrue(plot.count("rope") > 0 && plot.count("Egg") > 0 && plot.count("fish") > 0
                && plot.count(ChoirStones.STONE) > 0);
        assertNotEquals("", TraderLines.REFUSED);
    }

    @Test
    void ropeAndStonesFromTheExchangeKeepTheBridgesOfChapterFour() {
        String rec = mend(0);
        String rec2 = mend(1);
        x.press("a", rec, plot);
        x.trade("b", "ida", rec, plot);
        x.press("c", rec2, plot);
        x.trade("d", "pell", rec2, plot);
        assertTrue(plot.count(ChoirStones.STONE) >= 1);
        assertTrue(plot.count(BridgeLedger.ROPE) >= BridgeLedger.ROPE_PER_BRIDGE);
        FragmentMap line = FragmentMap.of(3, new int[][] {{0, 1}, {1, 2}});
        ChoirStones c = new ChoirStones(line, songs, 3);
        assertEquals(ChoirStones.Outcome.CARVED, c.carve("k", 1, rec, 1, plot));
        int n = 1;
        while (c.ledger().intact(0, 1) && c.ledger().intact(1, 2)) {
            c.night(n++);
            if (n > 200) {
                break;
            }
        }
        assertTrue(c.ledger().intact(0, 1) && c.ledger().intact(1, 2), "a stone on the middle fragment hums both");
    }
}
