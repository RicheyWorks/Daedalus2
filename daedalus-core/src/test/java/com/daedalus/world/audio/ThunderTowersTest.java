// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class ThunderTowersTest {
    @Test void everyStormHasExactlyOneMatchingCell() {
        for (long s = 0; s < 100; s++) {
            ThunderTowers t = ThunderTowers.seeded(s);
            assertThat(t.towers()).hasSize(3).doesNotHaveDuplicates();
            assertThat(t.candidates()).hasSize(1);
            ThunderTowers.Cell only = t.candidates().get(0);
            ThunderTowers.Verdict v = t.judge(only);
            assertThat(v.correct()).isTrue();
            assertThat(v.strike()).isEqualTo(only);
            assertThat(v.errorTenths()).containsOnly(0);
            assertThat(t.seed()).isEqualTo(s);
        }
    }

    @Test void wrongCellShowsDelayError() {
        ThunderTowers t = ThunderTowers.seeded(3);
        ThunderTowers.Cell s = t.candidates().get(0);
        ThunderTowers.Cell other = new ThunderTowers.Cell((s.x() + 6) % ThunderTowers.GRID, s.y());
        ThunderTowers.Verdict v = t.judge(other);
        assertThat(v.correct()).isFalse();
        assertThat(v.errorTenths()).anyMatch(e -> e != 0);
    }

    @Test void soundPhysics() {
        ThunderTowers.Cell a = new ThunderTowers.Cell(0, 0);
        assertThat(ThunderTowers.delayTenths(a, a)).isZero();
        assertThat(ThunderTowers.delayTenths(a, new ThunderTowers.Cell(0, 4))).isEqualTo(29); // 1000 m / 343 = 2.92 s
        assertThat(ThunderTowers.delayTenths(a, new ThunderTowers.Cell(3, 4))).isEqualTo(36); // 1250 m
        assertThatThrownBy(() -> new ThunderTowers.Cell(12, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new ThunderTowers.Cell(0, -1)).isInstanceOf(IllegalArgumentException.class);
    }
}