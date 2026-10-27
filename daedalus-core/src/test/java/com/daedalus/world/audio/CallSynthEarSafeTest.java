// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

/** The additive ear-safe path: whole-octave drops under the ear rule, with PCS 1 design output unchanged. */
class CallSynthEarSafeTest {
    private static final int SEEDS = 300;

    @Test
    void everySpeciesAndSeedLandsUnderTheEarRuleByWholeOctaves() {
        for (Species s : Species.values()) {
            for (long seed = 0; seed < SEEDS; seed++) {
                CallSpec raw = CallSynth.design(s, CallSynthTest.genome(seed));
                CallSpec safe = CallSynth.designEarSafe(s, CallSynthTest.genome(seed));
                String at = s + " seed " + seed;
                assertThat(EarRule.ok(safe.baseHz())).as(at).isTrue();
                double octaves = Math.log(raw.baseHz() / safe.baseHz()) / Math.log(2);
                assertThat(Math.abs(octaves - Math.rint(octaves))).as(at).isLessThan(1e-4);
                assertThat(Math.rint(octaves)).as(at).isGreaterThanOrEqualTo(0);
                if (EarRule.ok(raw.baseHz())) {
                    assertThat(safe).as(at).isEqualTo(raw);
                } else {
                    assertThat(safe.baseHz() * 2).as(at + " is the highest octave under the rule")
                            .isGreaterThanOrEqualTo(EarRule.MAX_FUNDAMENTAL_HZ - 0.01);
                }
                assertThat(new CallSpec(raw.baseHz(), safe.sweep(), safe.harmonics(), safe.brightness(), safe.pulses(),
                        safe.pulseMs(), safe.gapMs(), safe.vibratoHz(), safe.vibratoDepth(), safe.breath())).as(at).isEqualTo(raw);
                assertThat(CallSpec.parse(safe.toLine())).isEqualTo(safe);
            }
        }
    }

    @Test
    void designAndItsContractLineAreUntouched() {
        Genome g = Genome.ofHex("ff808080808080808080");
        CallSpec raw = CallSynth.design(Species.SONGBIRD, g);
        assertThat(raw.baseHz()).isEqualTo(5200.0);
        assertThat(raw.toLine()).startsWith("PCS 1 hz=5200.000 ");
        assertThat(CallSynth.earSafe(raw).baseHz()).isEqualTo(650.0);
        assertThat(CallSynth.design(Species.SONGBIRD, g)).isEqualTo(raw);
    }

    @Test
    void boundaryAndLowCallsBehave() {
        CallSpec at800 = new CallSpec(800, 0, 1, 0, 1, 100, 0, 3, 0, 0);
        assertThat(CallSynth.earSafe(at800).baseHz()).isEqualTo(400.0);
        CallSpec low = new CallSpec(799.999, 0, 1, 0, 1, 100, 0, 3, 0, 0);
        assertThat(CallSynth.earSafe(low)).isSameAs(low);
        CallSpec bass = new CallSpec(70, 0, 1, 0, 1, 100, 0, 3, 0, 0);
        assertThat(CallSynth.earSafe(bass)).isSameAs(bass);
    }
}
