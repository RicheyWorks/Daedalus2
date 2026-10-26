// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.exchange;

import static org.assertj.core.api.Assertions.assertThat;

import com.daedalus.world.brew.BrewBench;
import com.daedalus.world.brew.FoundTune;
import com.daedalus.world.brew.MelodyBrew;
import com.daedalus.world.brew.PitchTable;
import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.brew.story.SpringChain;
import com.daedalus.world.colony.PlotState;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * C++ = Java, line for line (G66 native binding): engines/unreal/core-test/record_exchange_parity.txt is written by
 * record_exchange_core_test.cpp --write from DaedalusRecordExchangeCore.h. Here the same lines come from the real
 * {@link RecordExchange} over a real {@link SeedSongSpring}; every restore is stocked, so the bench brews.
 */
class RecordExchangeParityTest {

    private static final Path PARITY = Path.of("..", "engines", "unreal", "core-test", "record_exchange_parity.txt");

    static List<FoundTune> tunes() throws Exception {
        try (var in = RecordExchangeParityTest.class.getResourceAsStream("/com/daedalus/world/brew/found_tunes.csv")) {
            return FoundTune.parseCsv(new String(in.readAllBytes(), StandardCharsets.UTF_8));
        }
    }

    static int idx(List<FoundTune> tunes, String record) {
        for (int i = 0; i < tunes.size(); i++) {
            if (tunes.get(i).learnedFrom().equals(record)) {
                return i;
            }
        }
        return -1;
    }

    static String sell(RecordExchange x, String event, String trader, String record, PlotState plot) {
        RecordExchange.Trade t = x.trade(event, trader, record, plot);
        return t.outcome() + ":" + (t.good() == null ? "" : t.good()) + ":" + t.amount() + ":" + (t.wanted() ? "1" : "0");
    }

    static String quest(RecordExchange x) {
        return x.quest().stepIndex() + "/" + x.quest().stepCount();
    }

    static List<String> scenario(List<FoundTune> tunes, long seed) {
        List<String> out = new ArrayList<>();
        SeedSongSpring songs = new SeedSongSpring(new BrewBench(PitchTable.ISLAND_CANON, tunes), tunes,
                SpringChain.island(), seed);
        PlotState plot = new PlotState();
        StringBuilder l = new StringBuilder("restore s=" + seed);
        for (int i = 0; i < tunes.size(); i++) {
            if (i % 4 != 3) {
                FoundTune t = tunes.get(i);
                plot.add(t.learnedFrom(), 1);
                t.herbs().forEach(h -> plot.add(h, 1));
                List<MelodyBrew.Ingredient> kettle = t.herbs().stream().map(h -> new MelodyBrew.Ingredient(h, 3)).toList();
                l.append(" ").append(i).append("=").append(songs.restore("r" + i, t.learnedFrom(), kettle, plot).outcome());
            }
        }
        out.add(l.toString());
        RecordExchange x = new RecordExchange(songs, tunes, Trader.island(), seed);
        for (int d = 1; d <= 5; d++) {
            StringBuilder w = new StringBuilder("day s=" + seed + " d=" + d + " day=" + x.day() + " wants=");
            for (Trader t : x.traders()) {
                w.append(t.id()).append(":");
                x.wantsToday(t.id()).forEach(r -> w.append(idx(tunes, r)).append("|"));
                w.append(";");
            }
            w.append(" press=");
            for (int i = 0; i < tunes.size(); i++) {
                w.append(x.press("p" + d + "_" + i, tunes.get(i).learnedFrom(), plot)).append(",");
            }
            if (d == 1) {
                w.append(" again=").append(x.press("p1_0", tunes.get(0).learnedFrom(), plot)).append(",")
                        .append(x.press("p1_0x", tunes.get(0).learnedFrom(), plot));
            }
            out.add(w.toString());
            StringBuilder s = new StringBuilder("sell s=" + seed + " d=" + d);
            for (Trader t : x.traders()) {
                int k = 0;
                for (String r : x.wantsToday(t.id())) {
                    s.append(" ").append(t.id()).append("#").append(idx(tunes, r)).append("=")
                            .append(sell(x, "t" + d + t.id() + k, t.id(), r, plot));
                    k++;
                }
            }
            String r0 = tunes.get(0).learnedFrom();
            int dov = x.price("dov", r0);
            s.append(" dovPrice=").append(dov).append(" dov=").append(sell(x, "y" + d, "dov", r0, plot));
            s.append(" pell=").append(sell(x, "x" + d, "pell", tunes.get(d % tunes.size()).learnedFrom(), plot));
            s.append(" q=").append(quest(x));
            String said = x.talk("k" + d);
            s.append(" talk=").append(said).append(" | q=").append(quest(x)).append(" goods=")
                    .append((int) plot.count("rope")).append(",").append((int) plot.count("choir_stone_blank"))
                    .append(",").append((int) plot.count("Egg")).append(",").append((int) plot.count("fish"));
            s.append(" line=").append(TraderLines.line(x));
            out.add(s.toString());
            x.nextDay();
        }
        String r0 = tunes.get(0).learnedFrom();
        out.add("edge s=" + seed + " zed=" + sell(x, "e1", "zed", r0, plot)
                + " nope=" + sell(x, "e2", "pell", "Item_YTM_Record_Nope", plot)
                + " nocopy=" + sell(x, "e3", "pell", tunes.get(3).learnedFrom(), plot)
                + " blank=" + sell(x, " ", "pell", r0, plot)
                + " dup=" + sell(x, "x1", "pell", r0, plot)
                + " pressNope=" + x.press("e4", "Item_YTM_Record_Nope", plot)
                + " pressRaw=" + x.press("e5", tunes.get(3).learnedFrom(), plot)
                + " priceZed=" + x.price("zed", r0) + " copy=" + RecordExchange.copyOf(r0)
                + " done=" + (x.quest().complete() ? "1" : "0"));
        return out;
    }

    @Test
    void cppCoreMatchesJavaExchangeLineForLine() throws Exception {
        List<FoundTune> tunes = tunes();
        List<String> want = new ArrayList<>();
        for (long s = 0; s < 10; s++) {
            want.addAll(scenario(tunes, s));
        }
        List<String> got = Files.readAllLines(PARITY, StandardCharsets.UTF_8).stream()
                .filter(l -> !l.startsWith("#")).toList();
        assertThat(got).containsExactlyElementsOf(want);
    }
}