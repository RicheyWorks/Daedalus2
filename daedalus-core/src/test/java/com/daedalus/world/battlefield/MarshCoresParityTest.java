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
 * Java = C++ golden vectors for the marsh-lane ecology cores (G570 port of G202 DroughtOdds, G583 port of G200
 * CraneSpread; later ecology ports add a method here). Each engines/unreal/core-test/marsh_*_parity.txt is written from this class (run with
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

    static List<String> craneSpread() {
        double[][] tunings = {{1.5, 1.0, 0.25, 100}, {1.2, 0.8, 0.2, 60}, {2.0, 1.5, 0.5, 150}, {0.9, 1.0, 0.25, 100},
            {1.05, 2.0, 0.5, 80}, {3.0, 0.5, 0.25, 40}};
        List<String> out = new ArrayList<>();
        long seed = 11;
        for (double[] k : tunings) {
            CraneSpread m = CraneSpread.marsh(new CraneSpread.Settings(k[0], k[1], k[2], k[3], 40), 1);
            out.add("lambda=" + k[0] + " dispersal=" + k[1] + " cell=" + k[2] + " capacity=" + k[3] + " years=40"
                    + " mgf=" + m.mgf(0.3 / k[1]) + " cstar=" + m.spreadingSpeed());
            for (int noisy = 0; noisy < 2; noisy++) {
                CraneSpread.Report r = noisy == 0 ? m.run() : m.run(seed);
                StringBuilder s = new StringBuilder(noisy == 0 ? "run=det" : "run=noisy seed=" + seed);
                s.append(" speed=").append(r.speed()).append(" reach5=").append(r.yearReached(5.0));
                for (CraneSpread.Year y : r.years()) {
                    if (y.index() % 5 == 0) {
                        s.append(" front").append(y.index()).append('=').append(y.front())
                                .append(" birds").append(y.index()).append('=').append(y.birds());
                    }
                }
                out.add(s.toString());
            }
            seed += 7;
        }
        return out;
    }

    @Test
    void craneSpreadMatchesCpp() throws IOException {
        check("marsh_crane_spread_parity.txt", "G200 CraneSpread", MarshCoresParityTest::craneSpread);
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
            body.add("# " + game + " golden vectors: written by MarshCoresParityTest.java, replayed by "
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
