// SPDX-License-Identifier: MIT
package com.daedalus.world.labyrinth;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import org.junit.jupiter.api.Test;

class EchoBellGateTest {
    static final long[] SEEDS = {1L, 42L, -7L, 0x5EED_CAFEL, Long.MIN_VALUE};

    static String fixtureText() {
        StringBuilder sb = new StringBuilder();
        for (long s : SEEDS) {
            for (int d = 0; d <= 3; d++) {
                sb.append(EchoBellGate.seeded(s, d, d % 2 == 1).toWire());
            }
        }
        return sb.toString();
    }

    static List<Integer> perfectTaps(EchoBellGate g) {
        List<Integer> echoes = new ArrayList<>();
        for (EchoBellGate.Ring r : g.rings()) {
            echoes.add(r.echoMs());
        }
        echoes.sort(null);
        return echoes;
    }

    @Test void fixtureMatchesAndLocaleDoesNotChangeIt() throws Exception {
        Path fixture = Path.of("..", "docs", "contracts", "echo-bell-v1", "peals.ebg");
        Locale old = Locale.getDefault();
        String actual;
        try {
            Locale.setDefault(Locale.GERMANY);
            actual = fixtureText();
        } finally {
            Locale.setDefault(old);
        }
        if (!Files.exists(fixture) || !Files.readString(fixture).equals(actual)) {
            Files.createDirectories(Path.of("target"));
            Files.writeString(Path.of("target", "peals-actual.ebg"), actual);
        }
        assertThat(actual).isEqualTo(Files.readString(fixture));
    }

    @Test void earRulesHoldForManySeeds() {
        for (long s = -500; s < 500; s++) {
            for (int d = 0; d <= 3; d++) {
                EchoBellGate g = EchoBellGate.seeded(s, d, false);
                assertThat(g.rings()).hasSize(3 + d);
                int lastRing = 0;
                for (EchoBellGate.Ring r : g.rings()) {
                    assertThat(r.hz()).isBetween(EchoBellGate.ROOT_HZ - 0.001, EchoBellGate.MAX_HZ);
                    int gap = r.ringMs() - lastRing;
                    assertThat(gap).isBetween(600, 1200);
                    assertThat(r.gain()).isEqualTo(gap <= 750 ? 0.3 : 0.6);
                    assertThat(r.echoMs() - r.ringMs()).isEqualTo(EchoBellGate.echoDelayMs(r.depthCells()));
                    lastRing = r.ringMs();
                }
            }
        }
    }

    @Test void perfectTapsOpenTheGateAndEdgesOfTheWindowCount() {
        EchoBellGate g = EchoBellGate.seeded(42L, 2, false);
        assertThat(g.windowMs()).isEqualTo(100);
        assertThat(g.judge(perfectTaps(g)).open()).isTrue();
        List<Integer> edge = new ArrayList<>(perfectTaps(g));
        edge.replaceAll(t -> t + 100);
        assertThat(g.judge(edge).open()).isTrue();
        edge.set(0, edge.get(0) + 1);
        EchoBellGate.Verdict v = g.judge(edge);
        assertThat(v.open()).isFalse();
        assertThat(v.firstMiss()).isZero();
        assertThat(v.hits()).isEqualTo(g.rings().size() - 1);
    }

    @Test void missingExtraAndOutOfOrderTapsKeepTheGateShut() {
        EchoBellGate g = EchoBellGate.seeded(7L, 1, false);
        List<Integer> taps = perfectTaps(g);
        assertThat(g.judge(taps.subList(0, taps.size() - 1)).firstMiss()).isEqualTo(taps.size() - 1);
        List<Integer> extra = new ArrayList<>(taps);
        extra.add(taps.get(taps.size() - 1) + 50);
        EchoBellGate.Verdict v = g.judge(extra);
        assertThat(v.open()).isFalse();
        assertThat(v.firstMiss()).isEqualTo(taps.size());
        List<Integer> swapped = new ArrayList<>(taps);
        swapped.set(1, taps.get(0) - 1);
        assertThat(g.judge(swapped).open()).isFalse();
        assertThat(g.judge(List.of()).open()).isFalse();
        assertThatThrownBy(() -> g.judge(null)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test void cricketsWidenTheWindowByHalf() {
        assertThat(EchoBellGate.seeded(1L, 0, false).windowMs()).isEqualTo(140);
        assertThat(EchoBellGate.seeded(1L, 0, true).windowMs()).isEqualTo(210);
        assertThat(EchoBellGate.seeded(1L, 3, true).windowMs()).isEqualTo(120);
        EchoBellGate g = EchoBellGate.seeded(1L, 0, true);
        List<Integer> late = new ArrayList<>(perfectTaps(g));
        late.replaceAll(t -> t + 200);
        assertThat(g.judge(late).open()).isTrue();
        assertThat(EchoBellGate.seeded(1L, 0, false).judge(late).open()).isFalse();
    }

    @Test void mazeDepthsDriveTheEchoAndRetryRepeatsThePeal() {
        int[] depths = {1, 20, 40};
        EchoBellGate g = EchoBellGate.fromMazeDepths(99L, 0, false, depths);
        depths[0] = 30; // caller array is copied
        assertThat(g.rings().get(0).depthCells()).isEqualTo(1);
        assertThat(g.rings().get(2).echoMs() - g.rings().get(2).ringMs()).isEqualTo(200 + 70 * 40);
        assertThat(g.retry().toWire()).isEqualTo(g.toWire());
        assertThat(EchoBellGate.seeded(99L, 0, false).toWire()).isEqualTo(EchoBellGate.seeded(99L, 0, false).toWire());
        assertThatThrownBy(() -> EchoBellGate.fromMazeDepths(1L, 0, false, new int[] {1, 2})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> EchoBellGate.fromMazeDepths(1L, 0, false, new int[] {0, 2, 3})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> EchoBellGate.fromMazeDepths(1L, 0, false, new int[] {41, 2, 3})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> EchoBellGate.fromMazeDepths(1L, 0, false, null)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> EchoBellGate.seeded(1L, 4, false)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> EchoBellGate.seeded(1L, -1, false)).isInstanceOf(IllegalArgumentException.class);
    }
}