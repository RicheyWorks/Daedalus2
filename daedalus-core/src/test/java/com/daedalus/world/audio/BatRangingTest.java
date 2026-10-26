// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.audio.BatRanging.Call;
import com.daedalus.world.audio.BatRanging.Phase;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import org.junit.jupiter.api.Test;

class BatRangingTest {
    private static final int SEEDS = 300;

    @Test void deterministicPerSeedIncludingReplay() {
        for (long s = 0; s < 50; s++) {
            BatRanging a = BatRanging.seeded(s);
            BatRanging b = BatRanging.seeded(s);
            assertThat(a.calls()).isEqualTo(b.calls());
            assertThat(a.replay()).isEqualTo(b.replay());
            assertThat(a.marks()).isEqualTo(b.marks());
            assertThat(a.solve()).isEqualTo(b.solve());
            CricketThermometer night = CricketThermometer.seeded(s);
            assertThat(BatRanging.seeded(s, night).replay()).isEqualTo(BatRanging.seeded(s, night).replay());
        }
        assertThat(BatRanging.seeded(1).replay()).isNotEqualTo(BatRanging.seeded(2).replay());
    }

    @Test void callSpacingAlwaysLongerThanEchoDelay() {
        for (long s = 0; s < SEEDS; s++) {
            BatRanging b = BatRanging.seeded(s);
            List<Call> calls = b.calls();
            for (int i = 0; i < calls.size(); i++) {
                double next = i + 1 < calls.size() ? calls.get(i + 1).t() : Double.POSITIVE_INFINITY;
                assertThat(calls.get(i).echoT()).as("seed %d call %d", s, i).isLessThan(next);
                assertThat(calls.get(i).delay()).isPositive();
            }
            assertThat(b.catchT()).isGreaterThan(calls.get(calls.size() - 1).t());
        }
    }

    @Test void solverRangesEveryMarkAndPhase() {
        for (long s = 0; s < SEEDS; s++) {
            BatRanging b = BatRanging.seeded(s);
            BatRanging.Reading r = b.solve();
            assertThat(r.closingMps()).as("seed %d", s).isCloseTo(b.closingMps(), within(0.05));
            List<Double> marks = new ArrayList<>();
            for (int k : b.marks()) {
                marks.add(r.rangesM().get(k));
            }
            for (int i = 0; i < b.calls().size(); i++) {
                assertThat(r.rangesM().get(i)).isCloseTo(b.calls().get(i).rangeM(), within(BatRanging.TOLERANCE_M));
            }
            assertThat(r.phases()).isEqualTo(b.calls().stream().map(Call::phase).toList());
            BatRanging.Verdict v = b.judge(marks, r.phases());
            assertThat(v.score()).isEqualTo(100);
            assertThat(v.rangesRight()).isEqualTo(BatRanging.MARKS);
            // Every pass has all three phases, and the buzz only happens close in.
            assertThat(r.phases()).contains(Phase.SEARCH, Phase.APPROACH, Phase.BUZZ);
            b.calls().stream().filter(c -> c.phase() == Phase.BUZZ)
                .forEach(c -> assertThat(c.rangeM()).isLessThanOrEqualTo(BatRanging.BUZZ_M));
        }
    }

    @Test void solverMatchesBruteForceClosingSpeed() {
        for (long s = 0; s < 60; s++) {
            BatRanging b = BatRanging.seeded(s);
            double c = b.soundMps();
            List<Call> calls = b.calls();
            // Brute force: every closing speed on a 1 mm/s grid; corrected ranges plus v t should be constant (d0).
            double bestV = Double.NaN;
            double bestSs = Double.POSITIVE_INFINITY;
            for (int k = 0; k <= 10000; k++) {
                double v = k / 1000.0;
                double mean = 0;
                for (Call x : calls) {
                    mean += (c + v) * x.delay() / 2 + v * x.t();
                }
                mean /= calls.size();
                double ss = 0;
                for (Call x : calls) {
                    double e = (c + v) * x.delay() / 2 + v * x.t() - mean;
                    ss += e * e;
                }
                if (ss < bestSs) {
                    bestSs = ss;
                    bestV = v;
                }
            }
            assertThat(b.solve().closingMps()).as("seed %d", s).isCloseTo(bestV, within(0.002));
        }
    }

    @Test void jitterOffRangesAreExact() {
        for (long s = 0; s < 50; s++) {
            BatRanging b = BatRanging.of(s, 343.42, 0.0);
            BatRanging.Reading r = b.solve();
            assertThat(r.closingMps()).isCloseTo(b.closingMps(), within(1e-6));
            for (int i = 0; i < b.calls().size(); i++) {
                assertThat(r.rangesM().get(i)).isCloseTo(b.calls().get(i).rangeM(), within(1e-6));
            }
        }
        // Echo meets the closing bat early: tau = 2d / (c + v), shorter than the still-bat 2d / c.
        assertThat(BatRanging.echoDelay(3.43, 343, 0)).isCloseTo(0.02, within(1e-12));
        assertThat(BatRanging.echoDelay(3.43, 343, 4)).isLessThan(0.02);
    }

    @Test void phaseSplitsPinnedAgainstNearBoundaryCalls() {
        // Constructed distractors just either side of each range boundary.
        double c = BatRanging.speedOfSound(20);
        double eps = 1e-3;
        assertThat(BatRanging.phaseFromSpacing(BatRanging.spacing(BatRanging.APPROACH_M + eps, c, 5))).isEqualTo(Phase.SEARCH);
        assertThat(BatRanging.phaseFromSpacing(BatRanging.spacing(BatRanging.APPROACH_M - eps, c, 5))).isEqualTo(Phase.APPROACH);
        assertThat(BatRanging.phaseFromSpacing(BatRanging.spacing(BatRanging.BUZZ_M + eps, c, 5))).isEqualTo(Phase.APPROACH);
        assertThat(BatRanging.phaseFromSpacing(BatRanging.spacing(BatRanging.BUZZ_M - eps, c, 5))).isEqualTo(Phase.BUZZ);
        // Seeded calls nearest each boundary over many seeds keep a spacing margin from the split on both sides.
        double margin = 0.004;
        List<double[]> near = new ArrayList<>(); // {|d - boundary|, spacing, phase ordinal}
        for (long s = 0; s < 2000; s++) {
            BatRanging b = BatRanging.seeded(s);
            List<Call> calls = b.calls();
            for (int i = 0; i < calls.size(); i++) {
                double next = i + 1 < calls.size() ? calls.get(i + 1).t() : b.catchT();
                double d = calls.get(i).rangeM();
                double gap = Math.min(Math.abs(d - BatRanging.APPROACH_M), Math.abs(d - BatRanging.BUZZ_M));
                if (i + 1 < calls.size()) {
                    near.add(new double[] {gap, next - calls.get(i).t(), calls.get(i).phase().ordinal(), d});
                }
            }
        }
        near.sort(Comparator.comparingDouble(x -> x[0]));
        int[] sides = new int[4];
        for (double[] x : near.subList(0, 400)) {
            double ipi = x[1];
            Phase p = Phase.values()[(int) x[2]];
            assertThat(BatRanging.phaseFromSpacing(ipi)).as("d %.4f ipi %.5f", x[3], ipi).isEqualTo(p);
            boolean nearSearch = Math.abs(x[3] - BatRanging.APPROACH_M) < Math.abs(x[3] - BatRanging.BUZZ_M);
            double split = nearSearch ? BatRanging.SEARCH_SPLIT_S : BatRanging.BUZZ_SPLIT_S;
            assertThat(Math.abs(ipi - split)).as("d %.4f ipi %.5f", x[3], ipi).isGreaterThanOrEqualTo(margin);
            sides[(nearSearch ? 0 : 2) + (x[3] > (nearSearch ? BatRanging.APPROACH_M : BatRanging.BUZZ_M) ? 0 : 1)]++;
        }
        assertThat(sides).as("near-boundary calls on all four sides").doesNotContain(0);
    }

    @Test void replayObeysEarRuleAndIsSoft() {
        for (long s = 0; s < SEEDS; s++) {
            List<BatRanging.Sound> r = BatRanging.seeded(s).replay();
            for (int i = 0; i < r.size(); i++) {
                BatRanging.Sound x = r.get(i);
                assertThat(EarRule.ok(x.startHz()) && EarRule.ok(x.endHz())).isTrue();
                assertThat(x.level()).isLessThanOrEqualTo(0.5);
                if (i > 0) {
                    assertThat(x.t()).isGreaterThanOrEqualTo(r.get(i - 1).t());
                }
            }
        }
        // Opt-in temperature: a warm cricket night speeds sound up; the default stays 20 C.
        assertThat(BatRanging.seeded(3).soundMps()).isCloseTo(343.42, within(1e-9));
        CricketThermometer night = CricketThermometer.seeded(5);
        assertThat(BatRanging.seeded(3, night).soundMps()).isCloseTo(night.speedOfSoundMps(), within(1e-12));
    }
}
