// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.HashSet;
import java.util.Set;
import org.junit.jupiter.api.Test;

/** 300-seed property sweep of the creature-call designer, renderer and PCS 1 contract line. */
class CallSynthTest {
    private static final int SEEDS = 300;

    static Genome genome(long seed) {
        Rng r = new Rng(seed);
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < 12; i++) {
            sb.append(String.format("%02x", (int) (r.nextLong() & 0xff)));
        }
        return Genome.ofHex(sb.toString());
    }

    @Test
    void everyCallIsDeterministicAndInsideItsSpeciesEnvelope() {
        for (Species s : Species.values()) {
            for (long seed = 0; seed < SEEDS; seed++) {
                Genome g = genome(seed);
                CallSpec c = CallSynth.design(s, g);
                assertThat(CallSynth.design(s, genome(seed))).isEqualTo(c);
                String at = s + " seed " + seed;
                assertThat(c.baseHz()).as(at).isBetween(s.lowHz() - 0.001, s.highHz() + 0.001);
                assertThat(c.harmonics()).as(at).isBetween(1, 8);
                assertThat(c.pulses()).as(at).isBetween(1, s == Species.SONGBIRD ? 8 : 4);
                assertThat(c.pulseMs()).as(at).isBetween(60, 900);
                assertThat(c.gapMs()).as(at).isBetween(c.pulses() == 1 ? 0 : 30, c.pulses() == 1 ? 0 : 230);
                double sweepMax = s == Species.SONGBIRD ? 1.0 : 0.4;
                assertThat(Math.abs(c.sweep())).as(at).isLessThanOrEqualTo(sweepMax);
                assertThat(c.brightness()).as(at).isBetween(0.0, 1.0);
                assertThat(c.vibratoHz()).as(at).isBetween(3.0, 12.0);
                assertThat(c.vibratoDepth()).as(at).isBetween(0.0, 0.8);
                assertThat(c.breath()).as(at).isBetween(0.0, s == Species.SONGBIRD ? 0.3 : 0.8);
                assertThat(c.durationMs()).isEqualTo(c.pulses() * c.pulseMs() + (c.pulses() - 1) * c.gapMs());
            }
        }
    }

    @Test
    void contractLineRoundTripsForEverySeed() {
        for (Species s : Species.values()) {
            for (long seed = 0; seed < SEEDS; seed++) {
                CallSpec c = CallSynth.design(s, genome(seed));
                String line = c.toLine();
                assertThat(line).startsWith("PCS 1 hz=").doesNotContain(",");
                assertThat(line.split(" ")).hasSize(12);
                assertThat(CallSpec.parse(line)).as(s + " seed " + seed).isEqualTo(c);
                assertThat(CallSpec.parse("  " + line + "\n").toLine()).isEqualTo(line);
            }
        }
    }

    @Test
    void pitchGeneIsMonotonicOnALogScale() {
        for (Species s : Species.values()) {
            double prev = 0;
            for (int b = 0; b < 256; b++) {
                double hz = CallSynth.design(s, Genome.ofHex(String.format("%02x", b))).baseHz();
                assertThat(hz).as(s + " byte " + b).isGreaterThanOrEqualTo(prev);
                prev = hz;
            }
            double mid = CallSynth.design(s, Genome.ofHex("80")).baseHz();
            double geo = Math.sqrt(s.lowHz() * s.highHz());
            assertThat(Math.abs(Math.log(mid / geo) / Math.log(2))).as(s.toString()).isLessThan(0.05);
        }
    }

    @Test
    void lowerVoicesGetLongerSyllablesWithEverythingElseEqual() {
        Genome low = Genome.ofHex("00808080808080808080");
        Genome high = Genome.ofHex("ff808080808080808080");
        for (Species s : Species.values()) {
            assertThat(CallSynth.design(s, low).pulseMs()).as(s.toString())
                    .isGreaterThan(CallSynth.design(s, high).pulseMs());
        }
    }

    @Test
    void contractParseRejectsMalformedLines() {
        String good = CallSynth.design(Species.GOAT, genome(1)).toLine();
        assertThatThrownBy(() -> CallSpec.parse("PCS 2" + good.substring(5))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CallSpec.parse(good + " extra=1")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CallSpec.parse(good.replace("harm=", "harm"))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CallSpec.parse(good.replace("pulses=", "pulses=x"))).isInstanceOf(NumberFormatException.class);
        assertThatThrownBy(() -> new CallSpec(0, 0, 1, 0, 1, 10, 0, 3, 0, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new CallSpec(Double.NaN, 0, 1, 0, 1, 10, 0, 3, 0, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new CallSpec(100, 0, 0, 0, 1, 10, 0, 3, 0, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new CallSpec(100, 0, 1, 0, 1, 10, -1, 3, 0, 0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void renderIsSeededBoundedAndTheRightLength() {
        Set<Integer> hashes = new HashSet<>();
        for (Species s : Species.values()) {
            for (long seed = 0; seed < 20; seed++) {
                Genome g = genome(seed);
                CallSpec c = CallSynth.design(s, g);
                short[] a = CallSynth.render(c, 8000, g.seed());
                int pulseN = c.pulseMs() * 8000 / 1000;
                int gapN = c.gapMs() * 8000 / 1000;
                assertThat(a).hasSize(c.pulses() * pulseN + (c.pulses() - 1) * gapN);
                assertThat(CallSynth.render(c, 8000, g.seed())).isEqualTo(a);
                int peak = 0;
                for (short v : a) {
                    peak = Math.max(peak, Math.abs(v));
                }
                assertThat(peak).as("0.8 envelope ceiling").isLessThanOrEqualTo((int) Math.round(0.8 * Short.MAX_VALUE) + 1);
                assertThat(a[0]).as("envelope starts silent").isZero();
                for (int i = 0; i < gapN && c.pulses() > 1; i++) {
                    assertThat(a[pulseN + i]).as("gap is silent").isZero();
                }
                hashes.add(java.util.Arrays.hashCode(a));
            }
        }
        assertThat(hashes.size()).isGreaterThan(Species.values().length * 20 - 5);
    }

    @Test
    void breathNoiseDependsOnTheNoiseSeedOnly() {
        CallSpec c = new CallSpec(200, 0, 3, 0.5, 1, 100, 0, 5, 0.2, 0.5);
        assertThat(CallSynth.render(c, 8000, 1)).isNotEqualTo(CallSynth.render(c, 8000, 2));
        CallSpec pure = new CallSpec(200, 0, 3, 0.5, 1, 100, 0, 5, 0.2, 0);
        assertThat(CallSynth.render(pure, 8000, 1)).isEqualTo(CallSynth.render(pure, 8000, 2));
        assertThatThrownBy(() -> CallSynth.render(c, 7999, 1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void harmonicsAboveNyquistAreSkippedNotAliased() {
        CallSpec high = new CallSpec(3000, 0, 8, 1, 1, 50, 0, 3, 0, 0);
        CallSpec one = new CallSpec(3000, 0, 1, 1, 1, 50, 0, 3, 0, 0);
        assertThat(CallSynth.render(high, 8000, 0)).isEqualTo(CallSynth.render(one, 8000, 0));
    }

    @Test
    void genomeSeedIsStableAndDistinguishesGenomes() {
        assertThat(Genome.ofHex("0xAB").seed()).isEqualTo(Genome.ofHex("ab").seed());
        assertThat(Genome.ofHex("ab").equals(Genome.ofHex(" AB "))).isTrue();
        assertThat(Genome.ofHex("ab").hashCode()).isEqualTo(Genome.ofHex("AB").hashCode());
        Set<Long> seeds = new HashSet<>();
        for (long seed = 0; seed < SEEDS; seed++) {
            seeds.add(genome(seed).seed());
        }
        assertThat(seeds).hasSize(SEEDS);
        assertThatThrownBy(() -> Genome.ofHex(null)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> Genome.ofHex("0x")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> Genome.ofHex("zz")).isInstanceOf(IllegalArgumentException.class);
    }
}
