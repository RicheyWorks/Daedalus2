// SPDX-License-Identifier: MIT

package com.daedalus.world.fishing;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import org.junit.jupiter.api.Test;

class ConditionsTest {

    private final FishSpecies common = FishSpecies.of("c", Rarity.COMMON, 10, 1.0, 1);
    private final FishSpecies legend = new FishSpecies("l", Rarity.LEGENDARY, 1, 4, 0.4, "", 1, "",
            java.util.List.of(), java.util.List.of(), false);

    @Test
    void stormDoublesOnlyTheRareFishAndShortensBites() {
        assertThat(Conditions.STORM.weight(common)).isEqualTo(10);
        assertThat(Conditions.STORM.weight(legend)).isEqualTo(2);
        assertThat(Conditions.NIGHT_STORM.weight(legend)).isEqualTo(8);
        assertThat(Conditions.NIGHT.weight(legend)).isEqualTo(4);
        assertThat(Conditions.DAY.weight(legend)).isEqualTo(1);
        assertThat(Conditions.STORM.window(legend)).isCloseTo(0.34, within(1e-12));
        assertThat(Conditions.DAY.window(legend)).isEqualTo(0.4);
        assertThat(Conditions.STORM.waitFactor()).isEqualTo(0.75);
        assertThat(Conditions.NIGHT.waitFactor()).isEqualTo(1.0);
    }

    @Test
    void hoursMapToDayAndNight() {
        assertThat(Conditions.atHour(18, false)).isEqualTo(Conditions.DAY);
        assertThat(Conditions.atHour(19, false)).isEqualTo(Conditions.NIGHT);
        assertThat(Conditions.atHour(5, true)).isEqualTo(Conditions.NIGHT_STORM);
        assertThat(Conditions.atHour(6, true)).isEqualTo(Conditions.STORM);
        assertThatThrownBy(() -> Conditions.atHour(24, false)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> Conditions.atHour(-1, false)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void labelsReadPlainly() {
        assertThat(Conditions.DAY.label()).isEqualTo("day");
        assertThat(Conditions.NIGHT.label()).isEqualTo("night");
        assertThat(Conditions.STORM.label()).isEqualTo("storm");
        assertThat(Conditions.NIGHT_STORM.label()).isEqualTo("night storm");
    }
}
