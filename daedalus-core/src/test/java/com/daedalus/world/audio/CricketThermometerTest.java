// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.OptionalDouble;
import org.junit.jupiter.api.Test;

class CricketThermometerTest {
    private static final int SEEDS = 300;

    @Test void dolbearLawMatchesTheFahrenheitForm() {
        // F = 40 + N15 and chirps/min = 7.2 C - 32 are the same law.
        for (int c = 13; c <= 30; c++) {
            double n15 = CricketThermometer.chirpsPerMinute(c) / 4.0;
            assertThat(40 + n15).isCloseTo(c * 1.8 + 32, within(1e-9));
        }
        assertThat(CricketThermometer.celsiusFromCount(28)).isCloseTo(20.0, within(1e-9));
        assertThat(CricketThermometer.chirpsPerMinute(20)).isCloseTo(112.0, within(1e-9));
    }

    @Test void deterministicPerSeed() {
        for (long s = 0; s < 50; s++) {
            CricketThermometer a = CricketThermometer.seeded(s);
            CricketThermometer b = CricketThermometer.seeded(s);
            assertThat(a.tempC()).isEqualTo(b.tempC());
            assertThat(a.voices()).isEqualTo(b.voices());
            assertThat(a.solve()).isEqualTo(b.solve());
        }
        assertThat(CricketThermometer.seeded(1).voices()).isNotEqualTo(CricketThermometer.seeded(2).voices());
    }

    @Test void solverReadsEverySeedWithinTolerance() {
        int silent = 0;
        for (long s = 0; s < SEEDS; s++) {
            CricketThermometer c = CricketThermometer.seeded(s);
            CricketThermometer.Reading r = c.solve();
            boolean cold = c.tempC() < CricketThermometer.SILENT_BELOW_C;
            assertThat(r.silent()).as("seed %d", s).isEqualTo(cold);
            if (cold) {
                silent++;
                assertThat(c.judge(OptionalDouble.empty()).score()).isEqualTo(100);
            } else {
                assertThat(Math.abs(r.celsius() - c.tempC())).as("seed %d", s).isLessThanOrEqualTo(CricketThermometer.TOLERANCE_C);
                assertThat(c.judge(OptionalDouble.of(r.celsius())).score()).isEqualTo(100);
                assertThat(c.steadiest().hz()).isEqualTo(CricketThermometer.SNOWY_HZ);
            }
        }
        assertThat(silent).isBetween(1, SEEDS / 2);
    }

    @Test void solverMatchesBruteForceOverTemperatureGrid() {
        for (long s = 0; s < SEEDS; s++) {
            CricketThermometer c = CricketThermometer.seeded(s);
            CricketThermometer.Reading r = c.solve();
            if (r.silent()) {
                continue;
            }
            // Brute force: the 0.01 C grid temperature (0-40 C, wider than the seeded range) whose Dolbear 15 s count is nearest the count heard.
            double best = Double.NaN;
            double bestD = Double.POSITIVE_INFINITY;
            for (int k = 0; k <= 4000; k++) {
                double t = k / 100.0;
                double d = Math.abs(CricketThermometer.chirpsPerMinute(t) / 4.0 - r.count());
                if (d < bestD) {
                    bestD = d;
                    best = t;
                }
            }
            assertThat(r.celsius()).as("seed %d", s).isCloseTo(best, within(0.006));
        }
    }

    @Test void jitterOffCountIsExactToOneChirp() {
        for (int k = 130; k <= 300; k += 3) {
            for (int p = 0; p < 10; p++) {
                double t = k / 10.0;
                CricketThermometer c = CricketThermometer.of(t, p / 10.0, 0.0, k * 31L + p);
                double expected = CricketThermometer.chirpsPerMinute(t) / 4.0;
                int n = c.solve().count();
                assertThat(n).isBetween((int) Math.floor(expected), (int) Math.ceil(expected));
            }
        }
        // Half-interval phase and a whole-number count (28 at 20 C): no chirp sits on a window edge.
        CricketThermometer c = CricketThermometer.of(20.0, 0.5, 0.0, 7);
        assertThat(c.solve().count()).isEqualTo(28);
        assertThat(c.solve().celsius()).isCloseTo(20.0, within(1e-9));
        assertThatThrownBy(() -> CricketThermometer.of(20, 0, 0.5, 1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test void tooColdRoundsExistAndJudgeAcceptsOnlyTooCold() {
        int cold = 0;
        for (long s = 0; s < SEEDS; s++) {
            CricketThermometer c = CricketThermometer.seeded(s);
            if (c.tempC() >= CricketThermometer.SILENT_BELOW_C) {
                continue;
            }
            cold++;
            assertThat(c.solve().silent()).as("seed %d", s).isTrue();
            assertThat(c.voices().stream().filter(v -> v.hz() == CricketThermometer.SNOWY_HZ).findFirst().orElseThrow()
                .onsets()).isEmpty();
            CricketThermometer.Verdict tooCold = c.judge(OptionalDouble.empty());
            assertThat(tooCold.correct()).isTrue();
            assertThat(tooCold.score()).isEqualTo(100);
            for (double g : new double[] {c.tempC(), CricketThermometer.SILENT_BELOW_C, 20.0}) {
                CricketThermometer.Verdict v = c.judge(OptionalDouble.of(g));
                assertThat(v.correct()).as("seed %d guess %.1f", s, g).isFalse();
                assertThat(v.score()).isZero();
            }
        }
        assertThat(cold).as("too-cold rounds in %d seeds", SEEDS).isGreaterThanOrEqualTo(10);
    }

    @Test void steadyCutOffPinnedAgainstNearRegularDistractors() {
        // Over many seeds, find the most regular field crickets and the least regular snowy tree crickets.
        int n = 2000;
        List<double[]> field = new ArrayList<>(); // {cv, seed}
        List<double[]> snowy = new ArrayList<>();
        for (long s = 0; s < n; s++) {
            for (CricketThermometer.Voice v : CricketThermometer.seeded(s).voices()) {
                if (v.onsets().isEmpty()) {
                    continue;
                }
                (v.hz() == CricketThermometer.SNOWY_HZ ? snowy : field).add(new double[] {v.intervalCv(), s});
            }
        }
        field.sort(Comparator.comparingDouble(x -> x[0]));
        snowy.sort(Comparator.comparingDouble(x -> -x[0]));
        double cut = CricketThermometer.STEADY_CV_MAX;
        for (double[] f : field.subList(0, 10)) {
            long s = (long) f[1];
            assertThat(f[0] - cut).as("near-regular distractor seed %d cv %.4f", s, f[0]).isGreaterThanOrEqualTo(0.03);
            CricketThermometer c = CricketThermometer.seeded(s);
            CricketThermometer.Reading r = c.solve();
            if (c.tempC() < CricketThermometer.SILENT_BELOW_C) {
                assertThat(r.silent()).as("seed %d: distractor alone must not be read", s).isTrue();
            } else {
                assertThat(c.steadiest().hz()).isEqualTo(CricketThermometer.SNOWY_HZ);
                assertThat(Math.abs(r.celsius() - c.tempC())).isLessThanOrEqualTo(CricketThermometer.TOLERANCE_C);
            }
        }
        for (double[] w : snowy.subList(0, 10)) {
            long s = (long) w[1];
            assertThat(cut - w[0]).as("least-steady snowy seed %d cv %.4f", s, w[0]).isGreaterThanOrEqualTo(0.03);
            assertThat(CricketThermometer.seeded(s).solve().silent()).isFalse();
        }
    }

    @Test void judgeScoresSpeedOfSoundAndEarRule() {
        CricketThermometer c = CricketThermometer.of(20.0, 0.0, 0.0, 7);
        assertThat(c.judge(OptionalDouble.of(21.0)).score()).isEqualTo(100);
        assertThat(c.judge(OptionalDouble.of(23.5)).score()).isEqualTo(60);
        assertThat(c.judge(OptionalDouble.empty()).score()).isZero();
        assertThat(c.speedOfSoundMps()).isCloseTo(343.42, within(1e-9));
        CricketThermometer cold = CricketThermometer.of(11.0, 0.0, 0.0, 7);
        assertThat(cold.judge(OptionalDouble.of(11.0)).score()).isZero();
        List<CricketThermometer.Chirp> sc = c.soundscape();
        assertThat(sc).isNotEmpty();
        for (int i = 1; i < sc.size(); i++) {
            assertThat(sc.get(i).t()).isGreaterThanOrEqualTo(sc.get(i - 1).t());
        }
        sc.forEach(ch -> {
            assertThat(EarRule.ok(ch.hz())).isTrue();
            assertThat(ch.level()).isLessThanOrEqualTo(0.5);
        });
    }
}
