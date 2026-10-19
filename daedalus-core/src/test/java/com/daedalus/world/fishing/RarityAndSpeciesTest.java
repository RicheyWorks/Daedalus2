// SPDX-License-Identifier: MIT

package com.daedalus.world.fishing;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.List;
import org.junit.jupiter.api.Test;

class RarityAndSpeciesTest {

    @Test
    void rarityParsesTableWordsAndKnowsWhichAreRare() {
        assertThat(Rarity.parse(" legendary ")).isEqualTo(Rarity.LEGENDARY);
        assertThat(Rarity.COMMON.isRare()).isFalse();
        assertThat(Rarity.UNCOMMON.isRare()).isFalse();
        assertThat(Rarity.RARE.isRare()).isTrue();
        assertThat(Rarity.LEGENDARY.isRare()).isTrue();
        assertThatThrownBy(() -> Rarity.parse(null)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> Rarity.parse("MYTHIC")).hasMessageContaining("MYTHIC");
    }

    @Test
    void speciesUsesItsNightWeightOnlyAtNight() {
        FishSpecies koi = new FishSpecies("koi", Rarity.RARE, 2, 8, 0.4, "heal 1 HP", 50, "n",
                List.of("Winter", "spring"), List.of(), true);
        assertThat(koi.weightAt(false)).isEqualTo(2);
        assertThat(koi.weightAt(true)).isEqualTo(8);
        assertThat(koi.feedsAtNight()).isTrue();
        assertThat(koi.seasons()).containsExactly("spring", "winter");
        assertThat(koi.inSeason("WINTER")).isTrue();
        assertThat(koi.inSeason("summer")).isFalse();
        assertThat(koi.isNative()).isTrue();
        assertThat(koi.visits("lake")).isFalse();
        assertThat(koi.duskOnly()).isTrue();
        assertThat(koi.effect()).isEqualTo("heal 1 HP");
        assertThat(koi.note()).isEqualTo("n");
        assertThat(koi.nightWeight()).isEqualTo(8);
        assertThat(koi.toString()).isEqualTo("koi (RARE)");

        FishSpecies plain = FishSpecies.of("dace", Rarity.COMMON, 5, 0.9, 3);
        assertThat(plain.weightAt(true)).isEqualTo(5);
        assertThat(plain.feedsAtNight()).isFalse();
        assertThat(plain.inSeason("autumn")).isTrue();
        assertThat(plain.spots()).isEmpty();
        assertThat(plain.effect()).isEmpty();
    }

    @Test
    void visitorsKnowTheirSpots() {
        FishSpecies ray = new FishSpecies("ray", Rarity.UNCOMMON, 1, 0, 0.7, null, 3, null, null, List.of("Ocean_Basin"), false);
        assertThat(ray.isNative()).isFalse();
        assertThat(ray.visits("ocean_basin")).isTrue();
        assertThat(ray.visits("lake")).isFalse();
        assertThat(ray.note()).isEmpty();
    }

    @Test
    void speciesRejectsNonsense() {
        assertThatThrownBy(() -> FishSpecies.of(" ", Rarity.COMMON, 1, 1, 1)).hasMessageContaining("name");
        assertThatThrownBy(() -> FishSpecies.of(null, Rarity.COMMON, 1, 1, 1)).hasMessageContaining("name");
        assertThatThrownBy(() -> FishSpecies.of("a", null, 1, 1, 1)).isInstanceOf(NullPointerException.class);
        assertThatThrownBy(() -> FishSpecies.of("a", Rarity.COMMON, 0, 1, 1)).hasMessageContaining("weight");
        assertThatThrownBy(() -> FishSpecies.of("a", Rarity.COMMON, Double.NaN, 1, 1)).hasMessageContaining("weight");
        assertThatThrownBy(() -> FishSpecies.of("a", Rarity.COMMON, Double.POSITIVE_INFINITY, 1, 1))
                .hasMessageContaining("weight");
        assertThatThrownBy(() -> FishSpecies.of("a", Rarity.COMMON, 1, 0, 1)).hasMessageContaining("window");
        assertThatThrownBy(() -> FishSpecies.of("a", Rarity.COMMON, 1, Double.POSITIVE_INFINITY, 1))
                .hasMessageContaining("window");
        assertThatThrownBy(() -> FishSpecies.of("a", Rarity.COMMON, 1, 1, -1)).hasMessageContaining("price");
        assertThatThrownBy(() -> new FishSpecies("a", Rarity.COMMON, 1, -1, 1, "", 1, "", List.of(), List.of(), false))
                .hasMessageContaining("night");
        assertThatThrownBy(() -> new FishSpecies("a", Rarity.COMMON, 1, Double.POSITIVE_INFINITY, 1, "", 1, "",
                List.of(), List.of(), false)).hasMessageContaining("night");
        assertThatThrownBy(() -> new FishSpecies("a", Rarity.COMMON, 1, 0, 1, "", 1, "", List.of(" "), List.of(), false))
                .hasMessageContaining("blank");
    }
}
