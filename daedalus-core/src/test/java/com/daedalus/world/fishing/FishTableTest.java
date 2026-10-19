// SPDX-License-Identifier: MIT

package com.daedalus.world.fishing;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.odds.OddsRng;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class FishTableTest {

    @Test
    void readsPrismheartsPondExactly() {
        FishTable t = FishTestData.prism();
        assertThat(t.realm()).isEqualTo("prism");
        assertThat(t.size()).isEqualTo(6);
        assertThat(t.fish()).extracting(FishSpecies::name).containsExactly("Reedling", "Pond Perch", "Mudskipper Eel",
                "Glassfin Minnow", "Sunscale Carp", "Prismscale Koi");
        FishSpecies koi = t.require("Prismscale Koi");
        assertThat(koi.rarity()).isEqualTo(Rarity.LEGENDARY);
        assertThat(koi.weightAt(true)).isEqualTo(4);
        assertThat(koi.price()).isEqualTo(400);
        assertThat(koi.windowSeconds()).isEqualTo(0.35);
        assertThat(t.totalWeight(Conditions.DAY)).isEqualTo(100);
        assertThat(t.totalWeight(Conditions.NIGHT)).isEqualTo(118);
    }

    @Test
    void biteOddsFollowTheWeightsAndRareFishFeedAtNight() {
        FishTable t = FishTestData.prism();
        Map<String, Double> day = t.biteOdds(Conditions.DAY);
        assertThat(day.values().stream().mapToDouble(Double::doubleValue).sum()).isCloseTo(1.0, within(1e-12));
        assertThat(day.get("Reedling")).isEqualTo(0.40);
        assertThat(day.get("Prismscale Koi")).isEqualTo(0.01);
        assertThat(t.biteChance("Prismscale Koi", Conditions.NIGHT)).isGreaterThan(t.biteChance("Prismscale Koi", Conditions.DAY));
        assertThat(t.biteChance("Prismscale Koi", Conditions.STORM)).isGreaterThan(t.biteChance("Prismscale Koi", Conditions.DAY));
    }

    @Test
    void pickWalksTheTableLikeTheBrowserDemo() {
        FishTable t = FishTestData.prism();
        assertThat(t.pick(0.0, Conditions.DAY).name()).isEqualTo("Reedling");
        assertThat(t.pick(0.3999, Conditions.DAY).name()).isEqualTo("Reedling");
        assertThat(t.pick(0.40, Conditions.DAY).name()).isEqualTo("Pond Perch");
        assertThat(t.pick(0.94, Conditions.DAY).name()).isEqualTo("Sunscale Carp");
        assertThat(t.pick(0.99, Conditions.DAY).name()).isEqualTo("Prismscale Koi");
        assertThat(t.pick(Math.nextDown(1.0), Conditions.DAY).name()).isEqualTo("Prismscale Koi");
        assertThatThrownBy(() -> t.pick(1.0, Conditions.DAY)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> t.pick(-0.1, Conditions.DAY)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> t.pick(Double.NaN, Conditions.DAY)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void manyPicksMatchTheOdds() {
        FishTable t = FishTestData.prism();
        OddsRng rng = new OddsRng(42);
        int reed = 0;
        int n = 20000;
        for (int i = 0; i < n; i++) {
            if (t.pick(rng.nextDouble(), Conditions.DAY).name().equals("Reedling")) {
                reed++;
            }
        }
        assertThat(reed / (double) n).isCloseTo(0.40, within(0.02));
    }

    @Test
    void lastFishCatchesRoundingLeftovers() {
        FishTable t = new FishTable("r", List.of(FishSpecies.of("a", Rarity.COMMON, 0.1, 1, 1),
                FishSpecies.of("b", Rarity.COMMON, 0.2, 1, 1)));
        assertThat(t.pick(Math.nextDown(1.0), Conditions.DAY).name()).isEqualTo("b");
    }

    @Test
    void findFilterAndCopies() {
        FishTable t = FishTestData.pair();
        assertThat(t.find("nope")).isEmpty();
        assertThatThrownBy(() -> t.require("nope")).hasMessageContaining("nope");
        assertThat(t.filter(f -> f.rarity().isRare()).orElseThrow().size()).isEqualTo(1);
        assertThat(t.filter(f -> false)).isEmpty();
        List<FishSpecies> copy = t.fish();
        copy.clear();
        assertThat(t.size()).isEqualTo(2);
    }

    @Test
    void rejectsBadTables() {
        FishSpecies a = FishSpecies.of("a", Rarity.COMMON, 1, 1, 1);
        assertThatThrownBy(() -> new FishTable("x", List.of())).hasMessageContaining("at least one");
        assertThatThrownBy(() -> new FishTable("x", null)).hasMessageContaining("at least one");
        assertThatThrownBy(() -> new FishTable("x", List.of(a, a))).hasMessageContaining("duplicate");
        assertThatThrownBy(() -> new FishTable("x", new ArrayList<>(Arrays.asList(a, null)))).hasMessageContaining("null");
        assertThat(new FishTable(null, List.of(a)).realm()).isEqualTo("unknown");
        assertThat(new FishTable(" ", List.of(a)).realm()).isEqualTo("unknown");
    }
}
