// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.audio.BrookBabble.Bubble;
import java.util.List;
import org.junit.jupiter.api.Test;

class BrookBabbleTest {
    private static final int SEEDS = 300;

    @Test void minnaertMatchesKnownValues() {
        // A 1 mm bubble at the surface rings near 3.3 kHz (Minnaert's classic ~3.26 m Hz product); 6 mm near 550 Hz.
        assertThat(BrookBabble.frequency(0.001, 0) * 0.001).isCloseTo(3.28, within(0.01));
        assertThat(BrookBabble.frequency(0.006, 0)).isCloseTo(547, within(2.0));
        assertThat(BrookBabble.frequency(0.006, 0.4)).isGreaterThan(BrookBabble.frequency(0.006, 0));
        assertThat(BrookBabble.volumeMl(0.01)).isCloseTo(4.18879, within(1e-4));
    }

    @Test void sizesAreRadiiNotDiameters() {
        // f R ~ 3.28 m Hz: 6 mm RADIUS ~ 550 Hz, 4.5 mm radius ~ 730 Hz, but a 6 mm DIAMETER (3 mm radius) ~ 1.1 kHz.
        assertThat(BrookBabble.frequency(0.006, 0)).isBetween(540.0, 555.0);
        assertThat(BrookBabble.frequency(0.0045, 0)).isBetween(725.0, 735.0);
        assertThat(BrookBabble.frequency(0.006 / 2, 0)).isBetween(1090.0, 1100.0);
        Bubble b = BrookBabble.seeded(4).riffles().get(0).get(0);
        assertThat(b.radiusMm()).isCloseTo(b.radiusM() * 1000, within(1e-12));
        assertThat(b.radiusMm()).isBetween(4.5, 10.0);
        assertThat(BrookBabble.radius(b.heardHz(), b.depthM())).isCloseTo(b.radiusM(), within(b.radiusM() * 1e-3));
    }

    @Test void voicingBoundaryIsPinned() {
        assertThat(BrookBabble.voiced(BrookBabble.MIN_R_M)).isTrue();
        assertThat(BrookBabble.voiced(BrookBabble.MIN_R_M - BrookBabble.R_STEP_M)).isFalse();
        assertThat(BrookBabble.voiced(450 / 1e5)).isTrue();
        assertThat(BrookBabble.voiced(449 / 1e5)).isFalse();
        // Every voiced size at every depth on the grid rings below 800 Hz (the 4.5 mm floor leaves headroom).
        for (int k = 450; k <= 1000; k++) {
            for (int h = 0; h <= 400; h += 20) {
                assertThat(BrookBabble.frequency(k / 1e5, h / 1000.0)).isLessThan(EarRule.MAX_FUNDAMENTAL_HZ);
            }
        }
        // Hydrostatic term: 4.5 mm reaches 800 Hz only near 2.1 m depth; riffles are clamped far shallower.
        assertThat(BrookBabble.maxVoicedDepthM()).isBetween(2.0, 2.2);
        assertThat(BrookBabble.frequency(BrookBabble.MIN_R_M, BrookBabble.maxVoicedDepthM())).isCloseTo(800.0, within(1e-6));
        assertThat(BrookBabble.MAX_DEPTH_M).isLessThan(BrookBabble.maxVoicedDepthM());
        int smallest = Integer.MAX_VALUE;
        double deepest = 0;
        for (long s = 0; s < SEEDS; s++) {
            for (List<Bubble> r : BrookBabble.seeded(s).riffles()) {
                for (Bubble x : r) {
                    assertThat(BrookBabble.voiced(x.radiusM())).isTrue();
                    smallest = Math.min(smallest, (int) Math.round(x.radiusM() * 1e5));
                    deepest = Math.max(deepest, x.depthM());
                }
            }
        }
        assertThat(smallest).isEqualTo(450);
        assertThat(deepest).isLessThanOrEqualTo(BrookBabble.MAX_DEPTH_M);
    }

    @Test void tiesKeepTheLowestRiffle() {
        assertThat(BrookBabble.argmax(List.of(2.0, 5.0, 5.0))).isEqualTo(1);
        assertThat(BrookBabble.argmax(List.of(5.0, 5.0, 5.0))).isZero();
        assertThat(BrookBabble.argmax(List.of(1.0, 2.0, 3.0))).isEqualTo(2);
        assertThat(BrookBabble.margin(List.of(2.0, 5.0, 5.0))).isZero();
        assertThat(BrookBabble.AERATION_LABEL).contains("illustrative");
    }

    @Test void deterministicPerSeed() {
        for (long s = 0; s < 50; s++) {
            assertThat(BrookBabble.seeded(s).riffles()).isEqualTo(BrookBabble.seeded(s).riffles());
            assertThat(BrookBabble.seeded(s).solve()).isEqualTo(BrookBabble.seeded(s).solve());
            assertThat(BrookBabble.seeded(s).soundscape(0)).isEqualTo(BrookBabble.seeded(s).soundscape(0));
        }
        assertThat(BrookBabble.seeded(1).riffles()).isNotEqualTo(BrookBabble.seeded(2).riffles());
    }

    @Test void inversionRoundTripsExactly() {
        for (int k = 0; k <= 55; k++) {
            double r = BrookBabble.MIN_R_M + k * 1e-4;
            for (double h : new double[] {0, 0.13, BrookBabble.MAX_DEPTH_M}) {
                assertThat(BrookBabble.radius(BrookBabble.frequency(r, h), h)).isCloseTo(r, within(1e-15));
            }
        }
    }

    @Test void solverSizesEveryBubbleAndPicksTheRiffle() {
        for (long s = 0; s < SEEDS; s++) {
            BrookBabble b = BrookBabble.seeded(s);
            BrookBabble.Reading r = b.solve();
            BrookBabble.Verdict v = b.judge(r.radiiM(), r.best());
            assertThat(v.sizesRight()).as("seed %d", s).isEqualTo(v.sizes());
            assertThat(v.pickRight()).isTrue();
            assertThat(v.score()).isEqualTo(100);
            for (int i = 0; i < BrookBabble.RIFFLES; i++) {
                assertThat(r.airMl().get(i)).isCloseTo(b.airMl().get(i), within(b.airMl().get(i) * 0.002));
            }
        }
    }

    @Test void solverMatchesBruteForceRadius() {
        for (long s = 0; s < 40; s++) {
            BrookBabble b = BrookBabble.seeded(s);
            BrookBabble.Reading r = b.solve();
            for (int i = 0; i < BrookBabble.RIFFLES; i++) {
                List<Bubble> bs = b.riffles().get(i);
                for (int j = 0; j < bs.size(); j++) {
                    Bubble x = bs.get(j);
                    // Brute force: every radius on a 1 micrometre grid, keep the closest predicted pitch.
                    double best = Double.NaN;
                    double bestE = Double.POSITIVE_INFINITY;
                    for (int k = 4000; k <= 10500; k++) {
                        double e = Math.abs(BrookBabble.frequency(k * 1e-6, x.depthM()) - x.heardHz());
                        if (e < bestE) {
                            bestE = e;
                            best = k * 1e-6;
                        }
                    }
                    assertThat(r.radiiM().get(i).get(j)).as("seed %d", s).isCloseTo(best, within(1e-6));
                }
            }
        }
    }

    @Test void depthCorrectionMatters() {
        int deep = 0;
        for (long s = 0; s < SEEDS; s++) {
            BrookBabble b = BrookBabble.seeded(s);
            BrookBabble.Reading blind = b.solveIgnoringDepth();
            for (int i = 0; i < BrookBabble.RIFFLES; i++) {
                List<Bubble> bs = b.riffles().get(i);
                for (int j = 0; j < bs.size(); j++) {
                    if (bs.get(j).depthM() > 0.25) {
                        deep++;
                        double tr = bs.get(j).radiusM();
                        assertThat(Math.abs(blind.radiiM().get(i).get(j) - tr)).isGreaterThan(BrookBabble.SIZE_TOL * tr);
                    }
                }
            }
        }
        assertThat(deep).isGreaterThan(100);
    }

    @Test void bestRiffleHasMarginAndEarRuleHolds() {
        for (long s = 0; s < SEEDS; s++) {
            BrookBabble b = BrookBabble.seeded(s);
            assertThat(BrookBabble.margin(b.airMl())).as("seed %d", s).isGreaterThanOrEqualTo(BrookBabble.PICK_MARGIN);
            // The solver's own air totals keep the lead well clear of the reading error (< 0.2%).
            assertThat(BrookBabble.margin(b.solve().airMl())).isGreaterThan(BrookBabble.PICK_MARGIN - 0.01);
            for (int i = 0; i < BrookBabble.RIFFLES; i++) {
                b.soundscape(i).forEach(x -> {
                    assertThat(EarRule.ok(x.hz())).isTrue();
                    assertThat(x.level()).isLessThanOrEqualTo(0.5);
                });
            }
        }
        // Worst case: smallest voiced bubble at the deepest point still rings below 800 Hz.
        assertThat(BrookBabble.frequency(BrookBabble.MIN_R_M, BrookBabble.MAX_DEPTH_M)).isLessThan(EarRule.MAX_FUNDAMENTAL_HZ);
    }
}
