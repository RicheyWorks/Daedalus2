// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import java.util.List;
import org.junit.jupiter.api.Test;

class ReedHumTest {
    private static final int SEEDS = 300;

    @Test void strouhalAndReynoldsValues() {
        // 3 m/s past a 6 mm stem: Re 1200, upper band, about 100 Hz.
        assertThat(ReedHum.reynolds(3, 0.006)).isCloseTo(1200.0, within(1e-9));
        assertThat(ReedHum.frequency(3, 0.006)).isCloseTo(100.0, within(1e-9));
        // Roshko laminar fit: St(100) = 0.212 (1 - 0.212); onset St is about 0.116; 0.2 from Re 150.
        assertThat(ReedHum.strouhal(100)).isCloseTo(0.212 * (1 - 0.212), within(1e-12));
        assertThat(ReedHum.strouhal(ReedHum.RE_MIN)).isCloseTo(0.1164, within(1e-3));
        assertThat(ReedHum.strouhal(149.9)).isLessThan(ReedHum.STROUHAL);
        assertThat(ReedHum.strouhal(ReedHum.RE_LAMINAR_MAX)).isEqualTo(ReedHum.STROUHAL);
    }

    @Test void solverUsesTheSameStrouhalAsTheGenerator() {
        // Exact round trip in both bands on a grid: no hidden St mismatch between frequency() and windFrom().
        for (int k = 30; k <= 120; k += 3) {
            double d = k / 10000.0;
            for (int j = 5; j <= 85; j++) {
                double u = j / 10.0;
                if (ReedHum.reynolds(u, d) > ReedHum.RE_MIN) {
                    assertThat(ReedHum.windFrom(ReedHum.frequency(u, d), d)).as("u %.2f d %.4f", u, d).isCloseTo(u, within(1e-9));
                }
            }
        }
        // Generator pitch is frequency() of the stem's own wind, rounded to 0.1 Hz.
        for (long s = 0; s < 50; s++) {
            for (ReedHum.Stem x : ReedHum.seeded(s).stems()) {
                if (x.voiced()) {
                    assertThat(x.heardHz()).isCloseTo(ReedHum.frequency(x.localMps(), x.diameterM()), within(0.05 + 1e-9));
                }
            }
        }
    }

    @Test void deterministicPerSeed() {
        for (long s = 0; s < 50; s++) {
            assertThat(ReedHum.seeded(s).stems()).isEqualTo(ReedHum.seeded(s).stems());
            assertThat(ReedHum.seeded(s).hums()).isEqualTo(ReedHum.seeded(s).hums());
            assertThat(ReedHum.seeded(s).solve()).isEqualTo(ReedHum.seeded(s).solve());
        }
        assertThat(ReedHum.seeded(1).stems()).isNotEqualTo(ReedHum.seeded(2).stems());
    }

    @Test void solverReadsWindAndCallOnEverySeed() {
        int forage = 0;
        for (long s = 0; s < SEEDS; s++) {
            ReedHum r = ReedHum.seeded(s);
            ReedHum.Reading x = r.solve();
            assertThat(x.perStemMps().size()).isGreaterThanOrEqualTo(ReedHum.MIN_VOICED);
            assertThat(Math.abs(x.windMps() - r.windMps())).as("seed %d", s).isLessThanOrEqualTo((ReedHum.GUST + 0.002) * r.windMps());
            assertThat(x.ambiguous()).isFalse();
            ReedHum.Verdict v = r.judge(x.windMps(), x.forage());
            assertThat(v.score()).as("seed %d", s).isEqualTo(100);
            if (r.forage()) {
                forage++;
            }
        }
        assertThat(forage).isBetween(SEEDS / 5, SEEDS * 4 / 5);
    }

    @Test void solverMatchesBruteForce() {
        for (long s = 0; s < SEEDS; s++) {
            ReedHum r = ReedHum.seeded(s);
            List<Double> us = r.solve().perStemMps();
            // Brute force per stem: 1 mm/s grid wind whose predicted pitch is nearest the heard one.
            int i = 0;
            for (ReedHum.Stem x : r.stems()) {
                if (!x.voiced()) {
                    continue;
                }
                double best = Double.NaN;
                double bestE = Double.POSITIVE_INFINITY;
                for (int k = 1; k <= 10000; k++) {
                    double u = k / 1000.0;
                    if (ReedHum.reynolds(u, x.diameterM()) <= ReedHum.RE_MIN) {
                        continue;
                    }
                    double e = Math.abs(ReedHum.frequency(u, x.diameterM()) - x.heardHz());
                    if (e < bestE) {
                        bestE = e;
                        best = u;
                    }
                }
                assertThat(us.get(i++)).as("seed %d", s).isCloseTo(best, within(0.0015));
            }
            // And the median over stems: least total absolute misfit on a 1 mm/s grid.
            double bestCost = Double.POSITIVE_INFINITY;
            double lo = Double.NaN;
            double hi = Double.NaN;
            for (int k = 0; k <= 10000; k++) {
                double u = k / 1000.0;
                double cost = 0;
                for (double v : us) {
                    cost += Math.abs(u - v);
                }
                if (cost < bestCost - 1e-9) {
                    bestCost = cost;
                    lo = u;
                    hi = u;
                } else if (Math.abs(cost - bestCost) <= 1e-9) {
                    hi = u;
                }
            }
            assertThat(r.solve().windMps()).isBetween(lo - 0.001, hi + 0.001);
        }
    }

    @Test void gustOffIsExactToHumRounding() {
        for (long s = 0; s < 100; s++) {
            ReedHum r = ReedHum.of(s, 0.0);
            for (double u : r.solve().perStemMps()) {
                // 0.05 Hz rounding moves the wind by at most 0.05 x D / St_min.
                assertThat(u).isCloseTo(r.windMps(), within(0.05 * ReedHum.MAX_D_M / ReedHum.strouhal(ReedHum.RE_MIN) + 1e-12));
            }
        }
    }

    @Test void sheddingOnsetPinnedBothSides() {
        double d = 0.005;
        double uAt = ReedHum.RE_MIN * ReedHum.NU / d;
        assertThat(ReedHum.stem(d, uAt * 0.999).shedding()).isFalse();
        assertThat(ReedHum.stem(d, uAt * 0.999).voiced()).isFalse();
        assertThat(ReedHum.stem(d, uAt * 1.001).shedding()).isTrue();
        // Just past onset a 3 mm stem sheds but its hum is infrasound (under 20 Hz); by Re 100 it is heard (Roshko band).
        ReedHum.Stem nearOnset = ReedHum.stem(0.003, ReedHum.RE_MIN * ReedHum.NU / 0.003 * 1.01);
        assertThat(nearOnset.shedding()).isTrue();
        assertThat(nearOnset.voiced()).isFalse();
        ReedHum.Stem laminar100 = ReedHum.stem(0.003, 100 * ReedHum.NU / 0.003);
        assertThat(laminar100.voiced()).isTrue();
        assertThat(laminar100.heardHz()).isCloseTo(ReedHum.strouhal(100) * 0.5 / 0.003, within(0.05 + 1e-9));
        // Seeds exercise the laminar (Roshko) band, the upper band, and silent stems (infrasound), and never voice below onset.
        int laminar = 0;
        int upper = 0;
        int silent = 0;
        for (long s = 0; s < SEEDS; s++) {
            for (ReedHum.Stem x : ReedHum.seeded(s).stems()) {
                if (x.voiced()) {
                    assertThat(x.re()).isGreaterThan(ReedHum.RE_MIN);
                    assertThat(x.heardHz()).isGreaterThanOrEqualTo(ReedHum.MIN_AUDIBLE_HZ);
                    if (x.re() < ReedHum.RE_LAMINAR_MAX) {
                        laminar++;
                    } else {
                        upper++;
                    }
                } else {
                    silent++;
                }
            }
        }
        assertThat(laminar).isPositive();
        assertThat(upper).isGreaterThan(laminar);
        assertThat(silent).isPositive();
    }

    @Test void toleranceAmbiguityAndEarRule() {
        // At the forage line the 0.5 m/s tolerance is wider than an 8% gust spread (0.4 m/s) and than the 6% used.
        assertThat(ReedHum.WIND_TOL_MPS).isGreaterThan(0.08 * ReedHum.FORAGE_MAX_MPS);
        assertThat(ReedHum.WIND_TOL_MPS).isGreaterThan(ReedHum.GUST * ReedHum.FORAGE_MAX_MPS);
        // The worst reading error at the strongest wind still fits the tolerance.
        assertThat((ReedHum.GUST + 0.002) * ReedHum.MAX_WIND_MPS).isLessThan(ReedHum.WIND_TOL_MPS);
        // Ambiguity band is the gust spread at the line; seeded winds stay outside it (margin 0.6 > 0.3).
        assertThat(ReedHum.ambiguous(ReedHum.FORAGE_MAX_MPS + 0.29)).isTrue();
        assertThat(ReedHum.ambiguous(ReedHum.FORAGE_MAX_MPS - 0.31)).isFalse();
        assertThat(ReedHum.CALL_MARGIN_MPS).isGreaterThan(ReedHum.GUST * ReedHum.FORAGE_MAX_MPS + 0.25);
        assertThat(ReedHum.FORAGE_LABEL).contains("illustrative");
        for (long s = 0; s < SEEDS; s++) {
            ReedHum r = ReedHum.seeded(s);
            assertThat(Math.abs(r.windMps() - ReedHum.FORAGE_MAX_MPS)).isGreaterThanOrEqualTo(ReedHum.CALL_MARGIN_MPS);
            r.hums().forEach(h -> {
                assertThat(EarRule.ok(h.hz())).isTrue();
                assertThat(h.level()).isLessThanOrEqualTo(0.5);
            });
        }
        // Worst case: strongest gust on the thinnest stem stays below 800 Hz.
        assertThat(ReedHum.frequency(ReedHum.MAX_WIND_MPS * (1 + ReedHum.GUST), ReedHum.MIN_D_M)).isLessThan(EarRule.MAX_FUNDAMENTAL_HZ);
        assertThat(ReedHum.median(List.of(3.0, 1.0, 2.0))).isEqualTo(2.0);
        assertThat(ReedHum.median(List.of(4.0, 1.0, 2.0, 3.0))).isEqualTo(2.5);
    }
}
