// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.week;

import static org.assertj.core.api.Assertions.assertThat;

import com.daedalus.world.colony.PlotState;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * C++ = Java, line for line (G62 native binding): engines/unreal/core-test/first_week_parity.txt is written by
 * first_week_core_test.cpp --write from DaedalusFirstWeekCore.h. The same scripted week runs here on the real
 * {@link Larder}, {@link FirstWeek} and {@link PlotState}.
 */
class FirstWeekParityTest {

    private static final Path PARITY = Path.of("..", "engines", "unreal", "core-test", "first_week_parity.txt");

    static PlotState stocked() {
        PlotState p = new PlotState();
        Object[][] s = {{"water", 6}, {"raw_water", 16}, {FirstWeek.DESERT_THIRST_TONIC, 1}, {"Bacon", 4}, {"Spudlet", 4},
            {"Egg", 8}, {"Fasage", 4}, {"Pumplet", 2}, {"Groat", 10}, {"Milk", 4}, {"Gloryroot", 1}, {"Kelpweed", 1},
            {"Bitroot", 1}, {"Clover", 1}, {"Mimint", 1}, {"Moonbean", 1}};
        for (Object[] x : s) {
            p.add((String) x[0], (Integer) x[1]);
        }
        return p;
    }

    static String day(FirstWeek.Day d) {
        if (d == null) {
            return "null";
        }
        return d.day() + "," + d.thirst() + "," + d.hunger() + "," + d.health() + "," + (d.sick() ? "1" : "0") + ","
                + (d.tonic() ? "1" : "0") + "," + (d.survived() ? "1" : "0");
    }

    static List<String> run(long seed) {
        List<String> out = new ArrayList<>();
        FirstWeek w = new FirstWeek(seed);
        PlotState p = stocked();
        List<String> recipes = new ArrayList<>(Larder.RECIPES.keySet());
        out.add("start s=" + seed + " line=" + WickLines.line(w));
        for (int d = 1; d <= 9; d++) {
            String ev = "w" + d;
            FirstWeek.Water k = (d + seed) % 3 == 0 ? FirstWeek.Water.CLEAN : FirstWeek.Water.RAW;
            FirstWeek.Outcome wo = w.drink(ev, k, p);
            FirstWeek.Outcome vo = w.drink("v" + d, FirstWeek.Water.RAW, p);
            String extra = "-";
            if (d == 1) {
                extra = w.drink(ev, FirstWeek.Water.RAW, p).toString();
            }
            if (d == 2) {
                extra = w.drink("s2", FirstWeek.Water.SALT, p).toString();
            }
            String r = recipes.get((int) ((seed + d) % 8));
            boolean cooked = Larder.cook(r, p);
            FirstWeek.Outcome eo = w.eat("e" + d, Larder.cooked(r), p);
            String tn = "-";
            if (d == 4) {
                FirstWeek.Outcome t1 = w.tonic("t4", p);
                FirstWeek.Outcome t2 = w.tonic("t4b", p);
                tn = t1 + "/" + t2;
            }
            String mid = WickLines.line(w);
            FirstWeek.Day dy = w.endDay();
            String said = "-";
            var due = w.quest().currentStep();
            if (due != null && due.type().equals("talk")) {
                said = w.talk("k" + d);
            }
            out.add("d s=" + seed + " d=" + d + " w=" + (k == FirstWeek.Water.CLEAN ? "CLEAN:" : "RAW:") + wo + " v=" + vo + " extra=" + extra
                    + " cook=" + r + ":" + (cooked ? "1" : "0") + " eat=" + eo + " tonic=" + tn + " mid=" + mid + " day=" + day(dy)
                    + " q=" + w.quest().stepIndex() + "/" + w.quest().stepCount() + " said=" + said + " line=" + WickLines.line(w)
                    + " water=" + (int) p.count("water") + " raw=" + (int) p.count("raw_water"));
        }
        FirstWeek.Outcome z = w.drink("z", FirstWeek.Water.CLEAN, p);
        out.add("end s=" + seed + " late=" + z + " lost=" + (w.lost() ? "1" : "0") + " health=" + w.health() + " done="
                + (w.quest().complete() ? "1" : "0"));
        return out;
    }

    static List<String> expected() {
        List<String> out = new ArrayList<>();
        for (long s = 0; s < 20; s++) {
            out.addAll(run(s));
        }
        return out;
    }

    @Test
    void javaMatchesTheCppParityFileLineForLine() throws Exception {
        List<String> lines = Files.readAllLines(PARITY);
        assertThat(lines.get(0)).startsWith("# first_week_core_test.cpp --write");
        assertThat(lines.subList(1, lines.size())).containsExactlyElementsOf(expected());
    }
}