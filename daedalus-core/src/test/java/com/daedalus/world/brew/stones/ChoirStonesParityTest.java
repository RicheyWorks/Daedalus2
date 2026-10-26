// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.stones;

import static org.assertj.core.api.Assertions.assertThat;

import com.daedalus.world.brew.BrewBench;
import com.daedalus.world.brew.FoundTune;
import com.daedalus.world.brew.MelodyBrew;
import com.daedalus.world.brew.PitchTable;
import com.daedalus.world.brew.hunt.FragmentMap;
import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.brew.story.SpringChain;
import com.daedalus.world.colony.PlotState;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;
import org.junit.jupiter.api.Test;

/**
 * C++ = Java, line for line (G53 native binding): engines/unreal/core-test/choir_stones_parity.txt is written by
 * choir_stones_core_test.cpp --write from DaedalusChoirStonesCore.h. Records 0..2 are restored for real on a
 * {@link SeedSongSpring}; record 3 stays scratched.
 */
class ChoirStonesParityTest {

    private static final Path PARITY = Path.of("..", "engines", "unreal", "core-test", "choir_stones_parity.txt");

    static List<FoundTune> tunes() throws Exception {
        try (var in = ChoirStonesParityTest.class.getResourceAsStream("/com/daedalus/world/brew/found_tunes.csv")) {
            return FoundTune.parseCsv(new String(in.readAllBytes(), StandardCharsets.UTF_8));
        }
    }

    static SeedSongSpring songs(List<FoundTune> tunes, long seed) {
        SeedSongSpring s = new SeedSongSpring(new BrewBench(PitchTable.ISLAND_CANON, tunes), tunes, SpringChain.island(), seed);
        PlotState p = new PlotState();
        for (int i = 0; i < 3; i++) {
            FoundTune t = tunes.get(i);
            p.add(t.learnedFrom(), 1);
            t.herbs().forEach(h -> p.add(h, 1));
            s.restore("restore" + i, t.learnedFrom(), t.herbs().stream().map(h -> new MelodyBrew.Ingredient(h, 3)).toList(), p);
        }
        return s;
    }

    static String bridges(List<BridgeLedger.Bridge> v) {
        List<String> o = new ArrayList<>();
        v.forEach(b -> o.add(b.a() + "-" + b.b()));
        return String.join(",", o);
    }

    static List<String> run(List<FoundTune> tunes, long seed, int n) {
        List<String> out = new ArrayList<>();
        FragmentMap m = FragmentMap.seeded(seed * 7 + n, n);
        ChoirStones c = new ChoirStones(m, songs(tunes, seed), seed);
        PlotState plot = new PlotState();
        plot.add(ChoirStones.STONE, 2);
        plot.add(BridgeLedger.ROPE, 6);
        String[] rec = new String[4];
        for (int i = 0; i < 4; i++) {
            rec[i] = tunes.get(i).learnedFrom();
        }
        String a = c.carve("c0", n - 1, rec[0], 4, plot).toString();
        String dup = c.carve("c0", n - 1, rec[0], 4, plot).toString();
        String taken = c.carve("c1", n - 1, rec[1], 3, plot).toString();
        String used = c.carve("c2", n / 2, rec[0], 3, plot).toString();
        String scratched = c.carve("c3", 1, rec[3], 3, plot).toString();
        String unknown = c.carve("c4", 99, rec[1], 3, plot).toString();
        out.add("carve s=" + seed + " n=" + n + " a=" + a + " dup=" + dup + " taken=" + taken + " used=" + used + " scratched="
                + scratched + " unknown=" + unknown + " stones=" + c.stones().size() + " range=" + c.stones().get(0).range()
                + " line=" + MasonLines.line(c));
        for (int k = 1; k <= 12; k++) {
            String second = k == 3 ? c.carve("c5", n / 2, rec[1], 2, plot).toString() : "-";
            ChoirStones.Night ni = c.night(k);
            String re = "-";
            for (Map.Entry<BridgeLedger.Bridge, Integer> e : c.ledger().snapshot().entrySet()) {
                if (e.getValue() == 0) {
                    if (c.ledger().restring(e.getKey().a(), e.getKey().b(), plot)) {
                        re = e.getKey().a() + "-" + e.getKey().b();
                    }
                    break;
                }
            }
            String said = "-";
            var due = c.quest().currentStep();
            if (due != null && due.type().equals("talk")) {
                said = c.talk("t" + k);
            }
            List<String> cut = new ArrayList<>();
            new TreeSet<>(ni.cutOff()).forEach(f -> cut.add(String.valueOf(f)));
            out.add("night s=" + seed + " n=" + n + " k=" + k + " carve=" + second + " frayed=" + bridges(ni.frayed())
                    + " snapped=" + bridges(ni.snapped()) + " cut=" + String.join(",", cut) + " held=" + (ni.held() ? "1" : "0")
                    + " heldN=" + c.heldNights() + " re=" + re + " rope=" + (int) plot.count(BridgeLedger.ROPE) + " q="
                    + c.quest().stepIndex() + "/" + c.quest().stepCount() + " said=" + said + " line=" + MasonLines.line(c));
        }
        ChoirStones.Night again = c.night(12);
        String last = c.carve("c6", 2, rec[2], 1, plot).toString();
        out.add("end s=" + seed + " n=" + n + " again=" + (again == null ? "null" : "night") + " last=" + last + " done="
                + (c.quest().complete() ? "1" : "0"));
        return out;
    }

    static List<String> expected() throws Exception {
        List<FoundTune> tunes = tunes();
        List<String> out = new ArrayList<>();
        for (long s = 0; s < 10; s++) {
            for (int n : new int[] {9, 16, 24}) {
                out.addAll(run(tunes, s, n));
            }
        }
        return out;
    }

    @Test
    void javaMatchesTheCppParityFileLineForLine() throws Exception {
        List<String> lines = Files.readAllLines(PARITY);
        assertThat(lines.get(0)).startsWith("# choir_stones_core_test.cpp --write");
        assertThat(lines.subList(1, lines.size())).containsExactlyElementsOf(expected());
    }
}