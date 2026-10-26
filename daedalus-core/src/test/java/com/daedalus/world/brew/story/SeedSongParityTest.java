// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.story;

import static org.assertj.core.api.Assertions.assertThat;

import com.daedalus.world.brew.BrewBench;
import com.daedalus.world.brew.FoundTune;
import com.daedalus.world.brew.MelodyBrew;
import com.daedalus.world.brew.PitchTable;
import com.daedalus.world.colony.PlotState;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * C++ = Java, line for line (G33 native binding): engines/unreal/core-test/seed_song_parity.txt is written by
 * seed_song_core_test.cpp --write from DaedalusSeedSongCore.h. Here the same lines come from the real chapter on a real
 * {@link BrewBench}; every brew is stocked, so the bench reports BREWED as the C++ scenario assumes.
 */
class SeedSongParityTest {

    private static final Path PARITY = Path.of("..", "engines", "unreal", "core-test", "seed_song_parity.txt");

    static List<FoundTune> tunes() throws Exception {
        try (var in = SeedSongParityTest.class.getResourceAsStream("/com/daedalus/world/brew/found_tunes.csv")) {
            return FoundTune.parseCsv(new String(in.readAllBytes(), StandardCharsets.UTF_8));
        }
    }

    static List<MelodyBrew.Ingredient> kettle(List<String> herbs) {
        return herbs.stream().map(h -> new MelodyBrew.Ingredient(h, 3)).toList();
    }

    static void herbs(PlotState plot, List<String> herbs) {
        herbs.forEach(h -> plot.add(h, 1));
    }

    static String tally(SeedSongSpring c) {
        SeedSongSpring.Tally t = c.tally();
        return t.restored() + "," + t.skipped() + "," + t.springsPurified() + "," + t.cleanDraws() + " q="
                + c.quest().stepIndex() + "/" + c.quest().stepCount();
    }

    static String draw(SpringChain.Draw d) {
        return d.outcome() + ":" + (d.item() == null ? "" : d.item()) + ":" + d.amount();
    }

    static List<String> scenario(List<FoundTune> tunes, long seed) {
        List<String> out = new ArrayList<>();
        BrewBench bench = new BrewBench(PitchTable.ISLAND_CANON, tunes);
        SeedSongSpring c = new SeedSongSpring(bench, tunes, SpringChain.island(), seed);
        PlotState plot = new PlotState();
        tunes.forEach(t -> plot.add(t.learnedFrom(), 1));
        for (int i = 0; i < tunes.size(); i++) {
            FoundTune t = tunes.get(i);
            StringBuilder l = new StringBuilder("run s=" + seed + " i=" + i + " a=");
            if (i % 3 == 1) {
                List<String> rev = new ArrayList<>(t.herbs());
                Collections.reverse(rev);
                herbs(plot, rev);
                l.append(c.restore("r" + i + "a", t.learnedFrom(), kettle(rev), plot).outcome());
            } else {
                l.append("-");
            }
            herbs(plot, t.herbs());
            SeedSongSpring.Restore r = c.restore("r" + i + "b", t.learnedFrom(), kettle(t.herbs()), plot);
            l.append(" b=").append(r.outcome()).append(" spring=").append(r.spring() == null ? "-" : r.spring().id())
                    .append(" tally=").append(tally(c));
            if (i == 2 || i == 7) {
                SpringChain.Draw d = c.draw("d" + i, "spring_1", plot);
                SpringChain.Draw d2 = c.draw("d" + i + "x", "spring_12", plot);
                l.append(" draw=").append(draw(d)).append(" far=").append(draw(d2));
                l.append(" talk=").append(c.talk("k" + i)).append(" | tally=").append(tally(c));
            }
            out.add(l + " keeper=" + KeeperLines.line(c));
        }
        FoundTune t0 = tunes.get(0);
        herbs(plot, t0.herbs());
        String dup = c.restore("r0b", t0.learnedFrom(), kettle(t0.herbs()), plot).outcome().toString();
        String unknown = c.restore("e1", "Item_YTM_Record_Nope", kettle(t0.herbs()), plot).outcome().toString();
        String already = c.restore("e2", t0.learnedFrom(), kettle(t0.herbs()), plot).outcome().toString();
        String blank = c.restore(" ", t0.learnedFrom(), kettle(t0.herbs()), plot).outcome().toString();
        out.add("edge s=" + seed + " dup=" + dup + " unknown=" + unknown + " already=" + already + " blank=" + blank
                + " unknownSpring=" + c.draw("e3", "spring_99", plot).outcome() + " drawDup="
                + c.draw("d2", "spring_1", plot).outcome() + " questDone=" + (c.quest().complete() ? "1" : "0"));
        SeedSongSpring f = new SeedSongSpring(new BrewBench(PitchTable.ISLAND_CANON, tunes), tunes, SpringChain.island(), seed);
        PlotState empty = new PlotState();
        String noRecord = f.restore("f1", t0.learnedFrom(), kettle(t0.herbs()), empty).outcome().toString();
        empty.add(t0.learnedFrom(), 1);
        String missing = f.restore("f2", t0.learnedFrom(), kettle(t0.herbs()), empty).outcome().toString();
        String cloudy = f.draw("f3", "spring_1", empty).outcome().toString();
        String keeper = KeeperLines.line(f);
        out.add("fresh s=" + seed + " noRecord=" + noRecord + " missingHerbs=" + missing + " cloudy=" + cloudy + " keeper="
                + keeper + " talk=" + f.talk("f4"));
        return out;
    }

    static List<String> expected() throws Exception {
        List<FoundTune> tunes = tunes();
        List<String> out = new ArrayList<>();
        for (long s = 0; s < 20; s++) {
            for (int i = 0; i < tunes.size(); i++) {
                ScratchedRecord r = ScratchedRecord.of(tunes.get(i), s);
                out.add("rec s=" + s + " t=" + i + " missing=" + r.missing() + " heard=" + String.join("|", r.heard())
                        + " home=" + (r.comesHome() ? "1" : "0") + " | " + KeeperLines.hint(r));
            }
        }
        for (SpringChain.Spring sp : SpringChain.island().springs()) {
            out.add("spring " + sp.id() + " " + sp.name() + " " + sp.yield());
        }
        for (long s = 0; s < 10; s++) {
            out.addAll(scenario(tunes, s));
        }
        return out;
    }

    @Test
    void javaMatchesTheCppParityFileLineForLine() throws Exception {
        List<String> lines = Files.readAllLines(PARITY);
        assertThat(lines.get(0)).startsWith("# seed_song_core_test.cpp --write");
        assertThat(lines.subList(1, lines.size())).containsExactlyElementsOf(expected());
    }
}