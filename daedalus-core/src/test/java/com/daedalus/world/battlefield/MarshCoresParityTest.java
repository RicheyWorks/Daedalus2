// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Supplier;
import org.junit.jupiter.api.Test;

/**
 * Java = C++ golden vectors for the marsh-lane ecology cores (G570 port of G202 DroughtOdds; later ecology ports add
 * a method here). Each engines/unreal/core-test/marsh_*_parity.txt is written from this class (run with
 * -Dmarsh.parity.write=true) and replayed by the matching marsh_*_core_test.cpp against its DaedalusMarsh*Core.h.
 * Doubles are printed with Double.toString (shortest round-trip form), so C++ can compare them with a tolerance.
 */
class MarshCoresParityTest {

    private static final Path CORE_TEST = Path.of("..", "engines", "unreal", "core-test");

    static List<String> droughtOdds() {
        double[] mus = {-0.02, 0.0, Math.log(1.029), 0.03};
        double[] sigmas = {0.1, 0.2, 0.3};
        int[][] flocks = {{40, 10}, {30, 10}, {80, 20}, {12, 10}};
        List<String> out = new ArrayList<>();
        long seed = 1;
        for (double mu : mus) {
            for (double sigma : sigmas) {
                for (int[] f : flocks) {
                    DroughtOdds o = DroughtOdds.of(new DroughtOdds.Settings(mu, sigma, f[0], f[1]));
                    int runs = 300;
                    int years = 30;
                    int substeps = 4;
                    long hits = Math.round(o.simulate(runs, years, substeps, seed) * runs);
                    double t = 10 + 5 * (seed % 9);
                    out.add("mu=" + mu + " sigma=" + sigma + " start=" + f[0] + " threshold=" + f[1] + " within T=" + t
                            + " within=" + o.within(t) + " ultimate=" + o.ultimate() + " median=" + o.medianYears()
                            + " runs=" + runs + " years=" + years + " substeps=" + substeps + " seed=" + seed
                            + " hits=" + hits);
                    seed++;
                }
            }
        }
        return out;
    }

    @Test
    void droughtOddsMatchesCpp() throws IOException {
        check("marsh_drought_odds_parity.txt", "G202 DroughtOdds", MarshCoresParityTest::droughtOdds);
    }

    private static void check(String file, String game, Supplier<List<String>> lines) throws IOException {
        Path path = CORE_TEST.resolve(file);
        List<String> actual = lines.get();
        if (Boolean.getBoolean("marsh.parity.write")) {
            List<String> body = new ArrayList<>();
            body.add("# " + game + " golden vectors (G570): written by MarshCoresParityTest.java, replayed by "
                    + file.replace("_parity.txt", "_core_test.cpp") + ".");
            body.addAll(actual);
            Files.write(path, body, StandardCharsets.UTF_8);
        }
        List<String> expected = Files.readAllLines(path, StandardCharsets.UTF_8).stream()
                .filter(l -> !l.startsWith("#") && !l.isBlank()).toList();
        assertEquals(actual.size(), expected.size(), file);
        for (int i = 0; i < actual.size(); i++) {
            assertEquals(expected.get(i), actual.get(i), file + " line " + i);
        }
    }
}
