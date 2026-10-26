// SPDX-License-Identifier: MIT

package com.daedalus.world.brew;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

/** Replays herbcombo.py's brew() for 1935 kettles (melody-parity.tsv from brew_parity.py). */
class MelodyBrewParityTest {

    static String j(List<?> xs) {
        if (xs.isEmpty()) {
            return "-";
        }
        List<String> s = new ArrayList<>();
        xs.forEach(x -> s.add(String.valueOf(x)));
        return String.join("|", s);
    }

    @Test
    void javaBrewMatchesPythonForEveryFixtureKettle() throws Exception {
        int rows = 0;
        int cadences = 0;
        try (var in = getClass().getResourceAsStream("melody-parity.tsv")) {
            var r = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8));
            for (String line = r.readLine(); line != null; line = r.readLine()) {
                if (line.startsWith("#")) {
                    continue;
                }
                String[] c = line.split("\t", -1);
                List<MelodyBrew.Ingredient> items = new ArrayList<>();
                String[] herbs = c[0].split("\\|");
                String[] stages = c[1].split("\\|");
                for (int i = 0; i < herbs.length; i++) {
                    items.add(new MelodyBrew.Ingredient(herbs[i], Integer.parseInt(stages[i])));
                }
                MelodyBrew.Tonic t = MelodyBrew.brew(items);
                String where = c[0] + " " + c[1];
                assertEquals(c[2], t.tonic(), where);
                assertEquals(c[3], t.melody(), where);
                assertEquals(c[4], t.effect(), where);
                assertEquals(c[5].equals("1"), t.purifiesWater(), where);
                assertEquals(Integer.parseInt(c[6]), t.tier(), where);
                assertEquals(Integer.parseInt(c[7]), t.magnitude(), where);
                assertEquals(Integer.parseInt(c[8]), t.durationS(), where);
                if (!t.noise() || herbs.length >= 3) {
                    assertEquals(c[9], j(t.notes()), where);
                }
                if (!t.noise()) {
                    assertEquals(c[10], j(t.steps()), where);
                }
                cadences += t.purifiesWater() ? 1 : 0;
                rows++;
            }
        }
        assertEquals(1935, rows);
        assertTrue(cadences > 50, "fixture exercises many cadences: " + cadences);
    }
}
