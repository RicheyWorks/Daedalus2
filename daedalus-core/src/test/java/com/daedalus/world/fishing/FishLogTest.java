// SPDX-License-Identifier: MIT

package com.daedalus.world.fishing;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Map;
import org.junit.jupiter.api.Test;

class FishLogTest {

    @Test
    void countsNewOnlyTheFirstTimeAndTracksProgressAndValue() {
        FishTable pond = FishTestData.prism();
        FishLog log = new FishLog(pond);
        assertThat(log.progress()).isEqualTo("0 / 6");
        assertThat(log.record(pond.require("Reedling"))).isTrue();
        assertThat(log.record(pond.require("Reedling"))).isFalse();
        assertThat(log.record(pond.require("Prismscale Koi"))).isTrue();
        assertThat(log.count("Reedling")).isEqualTo(2);
        assertThat(log.count("Pond Perch")).isZero();
        assertThat(log.kinds()).isEqualTo(2);
        assertThat(log.total()).isEqualTo(3);
        assertThat(log.value()).isEqualTo(6 + 6 + 400);
        assertThat(log.progress()).isEqualTo("2 / 6");
        assertThat(log.complete()).isFalse();
        Map<String, Integer> counts = log.counts();
        assertThat(counts).containsExactly(Map.entry("Reedling", 2), Map.entry("Prismscale Koi", 1));
        assertThatThrownBy(() -> counts.put("x", 1)).isInstanceOf(UnsupportedOperationException.class);
        for (FishSpecies f : pond.fish()) {
            log.record(f);
        }
        assertThat(log.complete()).isTrue();
    }

    @Test
    void logsOnlyCastsThatCaughtSomething() {
        FishTable pond = FishTestData.prism();
        FishLog log = new FishLog(pond);
        CastSession early = new CastSession(pond, Conditions.DAY, 3, 0);
        early.strike();
        assertThat(log.record(early)).isFalse();
        CastSession good = new CastSession(pond, Conditions.DAY, 3, 1);
        good.tick(good.waitSeconds());
        good.strike();
        assertThat(log.record(good)).isTrue();
        assertThat(log.total()).isEqualTo(1);
    }

    @Test
    void rejectsStrangers() {
        FishLog log = new FishLog(FishTestData.pair());
        assertThatThrownBy(() -> log.record(FishSpecies.of("eel", Rarity.COMMON, 1, 1, 1))).hasMessageContaining("eel");
        assertThatThrownBy(() -> log.record((FishSpecies) null)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new FishLog(null)).isInstanceOf(IllegalArgumentException.class);
    }
}
