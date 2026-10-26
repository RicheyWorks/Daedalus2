// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.hunt;

import static org.assertj.core.api.Assertions.assertThat;

import com.daedalus.world.colony.PlotState;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * C++ = Java, line for line (G46 native binding): engines/unreal/core-test/record_hunt_parity.txt is written by
 * record_hunt_core_test.cpp --write from DaedalusRecordHuntCore.h. The same scripted hunter runs here on the real
 * {@link FragmentMap} and {@link RecordHunt}.
 */
class RecordHuntParityTest {

    private static final Path PARITY = Path.of("..", "engines", "unreal", "core-test", "record_hunt_parity.txt");

    static List<String> records() {
        List<String> r = new ArrayList<>();
        for (int i = 0; i < 6; i++) {
            r.add("Item_YTM_Record_H" + i);
        }
        return r;
    }

    static String mapLine(long seed, int n, FragmentMap m) {
        StringBuilder s = new StringBuilder("map s=" + seed + " n=" + n + " links=");
        for (int f = 0; f < m.size(); f++) {
            s.append(f == 0 ? "" : ";").append(f).append(":");
            List<Integer> nb = m.neighbours(f);
            for (int i = 0; i < nb.size(); i++) {
                s.append(i == 0 ? "" : ",").append(nb.get(i));
            }
        }
        s.append(" home=");
        for (int f = 0; f < m.size(); f++) {
            s.append(f == 0 ? "" : ",").append(m.distance(FragmentMap.HOME, f));
        }
        return s.append(" far=").append(FragmentMap.name(m.size() - 1)).toString();
    }

    static List<String> run(long seed, int n) {
        List<String> out = new ArrayList<>();
        FragmentMap m = FragmentMap.seeded(seed * 31 + n, n);
        out.add(mapLine(seed, n, m));
        RecordHunt h = new RecordHunt(m, records(), seed, 5);
        StringBuilder w = new StringBuilder("where s=" + seed + " n=" + n);
        for (String r : records()) {
            w.append(" ").append(r.substring(16)).append("@").append(h.whereIs(r));
        }
        out.add(w.toString());
        PlotState plot = new PlotState();
        for (int t = 0; t < 80; t++) {
            String ev = "e" + t;
            String op;
            RecordHunt.Step s = null;
            String said = null;
            if (t % 11 == 5) {
                op = "bad";
                s = h.walk(ev, h.at());
            } else if (h.stamina() == 0) {
                op = "rest";
                s = h.rest(h.day() + 1);
            } else {
                RecordHunt.Hint hint = h.hint();
                if (hint == null) {
                    if (h.at() != FragmentMap.HOME) {
                        op = "home";
                        s = h.walk(ev, m.nextStep(h.at(), FragmentMap.HOME));
                    } else {
                        op = "talk";
                        said = h.talk(ev);
                    }
                } else if (hint.distance() == 0) {
                    op = "search";
                    s = h.search(ev, plot);
                } else {
                    op = "walk";
                    s = h.walk(ev, hint.toward());
                }
            }
            String line = ArchivistLines.line(h);
            StringBuilder l = new StringBuilder("h s=" + seed + " n=" + n + " t=" + t + " op=" + op);
            if (op.equals("talk")) {
                l.append(" said=").append(said);
            } else {
                l.append(" ").append(s.outcome()).append(" at=").append(s.at()).append(" st=").append(s.stamina())
                        .append(" found=").append(String.join("|", s.found()));
            }
            l.append(" day=").append(h.day()).append(" rem=").append(h.remaining()).append(" q=")
                    .append(h.quest().stepIndex()).append("/").append(h.quest().stepCount()).append(" line=").append(line);
            out.add(l.toString());
            if (op.equals("talk")) {
                break;
            }
        }
        RecordHunt.Step r = h.rest(h.day());
        RecordHunt.Step b = h.search(" ", plot);
        String again = h.talk("z");
        out.add("end s=" + seed + " n=" + n + " restAgain=" + r.outcome() + " blank=" + b.outcome() + " done="
                + (h.quest().complete() ? "1" : "0") + " talk=" + again);
        for (String rec : records()) {
            assertThat(plot.count(rec)).as("found records land in the plot store once").isEqualTo(1);
        }
        return out;
    }

    static List<String> expected() {
        List<String> out = new ArrayList<>();
        for (long s = 0; s < 10; s++) {
            for (int n : new int[] {4, 9, 16, 24}) {
                out.addAll(run(s, n));
            }
        }
        return out;
    }

    @Test
    void javaMatchesTheCppParityFileLineForLine() throws Exception {
        List<String> lines = Files.readAllLines(PARITY);
        assertThat(lines.get(0)).startsWith("# record_hunt_core_test.cpp --write");
        assertThat(lines.subList(1, lines.size())).containsExactlyElementsOf(expected());
    }
}