// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

/** The audible peak (glide plus vibrato) of ear-safe calls stays under the ear rule, by formula and by measurement. */
class CallSynthPeakTest {
    private static final int SEEDS = 300;
    private static final int RATE = 48_000;

    @Test
    void peakFormulaUsesTheRenderParameters() {
        CallSpec c = new CallSpec(400, 0.5, 1, 0, 1, 100, 0, 6, 0.6, 0);
        assertThat(CallSynth.peakHz(c)).isCloseTo(400 * Math.pow(2, 0.5 + 0.05), org.assertj.core.data.Offset.offset(1e-9));
        CallSpec falling = new CallSpec(400, -0.4, 1, 0, 1, 100, 0, 6, 0, 0);
        assertThat(CallSynth.peakHz(falling)).isEqualTo(400.0);
    }

    @Test
    void earSafePeakDropsWholeOctavesAndKeepsTheCallsCharacter() {
        for (Species s : Species.values()) {
            for (long seed = 0; seed < SEEDS; seed++) {
                CallSpec base = CallSynth.designEarSafe(s, CallSynthTest.genome(seed));
                CallSpec peak = CallSynth.designEarSafePeak(s, CallSynthTest.genome(seed));
                String at = s + " seed " + seed;
                assertThat(EarRule.ok(CallSynth.peakHz(peak))).as(at).isTrue();
                assertThat(EarRule.ok(peak.baseHz())).as(at).isTrue();
                double octaves = Math.log(base.baseHz() / peak.baseHz()) / Math.log(2);
                assertThat(Math.abs(octaves - Math.rint(octaves))).as(at).isLessThan(1e-4);
                if (EarRule.ok(CallSynth.peakHz(base))) {
                    assertThat(peak).as(at).isEqualTo(base);
                } else {
                    assertThat(CallSynth.peakHz(peak) * 2).as(at + " highest octave whose peak fits")
                            .isGreaterThanOrEqualTo(EarRule.MAX_FUNDAMENTAL_HZ - 0.01);
                }
                assertThat(peak.sweep()).isEqualTo(base.sweep());
                assertThat(peak.vibratoDepth()).isEqualTo(base.vibratoDepth());
                assertThat(peak.vibratoHz()).isEqualTo(base.vibratoHz());
                assertThat(peak.pulseMs()).isEqualTo(base.pulseMs());
                assertThat(CallSpec.parse(peak.toLine())).isEqualTo(peak);
            }
        }
    }

    @Test
    void renderedFundamentalNeverExceedsThePeakOrTheEarRule() {
        for (Species s : Species.values()) {
            for (long seed = 0; seed < 12; seed++) {
                CallSpec c = CallSynth.designEarSafePeak(s, CallSynthTest.genome(seed));
                CallSpec tone = new CallSpec(c.baseHz(), c.sweep(), 1, c.brightness(), 1, c.pulseMs(), 0,
                        c.vibratoHz(), c.vibratoDepth(), 0);
                double measured = maxInstantHz(CallSynth.render(tone, RATE, 0));
                String at = s + " seed " + seed + " " + c.toLine();
                assertThat(measured).as(at).isLessThan(EarRule.MAX_FUNDAMENTAL_HZ);
                assertThat(measured).as(at).isLessThanOrEqualTo(CallSynth.peakHz(c) * 1.03);
                assertThat(measured).as(at).isGreaterThan(c.baseHz() * Math.pow(2, Math.min(0, c.sweep())) * 0.9);
            }
        }
    }

    @Test
    void measurementCatchesTheGapThatBaseOnlyChecksMiss() {
        CallSpec risky = new CallSpec(700, 0.4, 1, 0, 1, 300, 0, 6, 0.8, 0);
        assertThat(EarRule.ok(risky.baseHz())).isTrue();
        assertThat(maxInstantHz(CallSynth.render(risky, RATE, 0))).isGreaterThan(EarRule.MAX_FUNDAMENTAL_HZ);
        CallSpec fixed = CallSynth.earSafePeak(risky);
        assertThat(fixed.baseHz()).isEqualTo(350.0);
        assertThat(maxInstantHz(CallSynth.render(fixed, RATE, 0))).isLessThan(EarRule.MAX_FUNDAMENTAL_HZ);
    }

    /** Highest instantaneous frequency from interpolated zero crossings, ignoring the faded 5% at each end. */
    static double maxInstantHz(short[] pcm) {
        int lo = pcm.length / 20;
        int hi = pcm.length - lo;
        double prev = -1;
        double best = 0;
        for (int i = lo; i < hi - 1; i++) {
            int a = pcm[i];
            int b = pcm[i + 1];
            if ((a < 0 && b >= 0) || (a >= 0 && b < 0)) {
                double x = i + (double) a / (a - b);
                if (prev >= 0) {
                    best = Math.max(best, RATE / (2 * (x - prev)));
                }
                prev = x;
            }
        }
        return best;
    }
}
