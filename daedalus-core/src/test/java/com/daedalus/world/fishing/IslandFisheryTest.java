// SPDX-License-Identifier: MIT

package com.daedalus.world.fishing;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.List;
import org.junit.jupiter.api.Test;

class IslandFisheryTest {

    private final FishTable sky = FishTestData.sky();
    private final List<String> island = List.of("rillperch", "ember_koi");

    private List<String> names(String spot, String season, int hour) {
        return IslandFishery.at(sky, island, spot, season, hour).map(t -> t.fish().stream().map(FishSpecies::name).toList())
                .orElse(List.of());
    }

    @Test
    void theSkyCatalogLoads() {
        assertThat(sky.realm()).isEqualTo("shattered-planet");
        assertThat(sky.fish()).filteredOn(FishSpecies::isNative).extracting(FishSpecies::name)
                .containsExactly("rillperch", "glassfin", "skytrout", "ember_koi");
        assertThat(sky.require("rainbow_eel").duskOnly()).isTrue();
    }

    @Test
    void islandChemistryAndSeasonDecideTheLakeFish() {
        assertThat(names("lake", "spring", 8)).containsExactly("rillperch", "ember_koi");
        assertThat(names("lake", "summer", 8)).containsExactly("rillperch");
        assertThat(names("lake", "autumn", 8)).isEmpty();
        assertThat(names("pier", "winter", 18)).containsExactly("ember_koi");
    }

    @Test
    void spotsBringTheirVisitors() {
        assertThat(names("ocean_basin", "summer", 9)).containsExactly("rillperch", "basin_ray");
        assertThat(names("sky_river", "spring", 9)).containsExactly("rillperch", "ember_koi");
        assertThat(names("sky_river", "spring", 18)).containsExactly("rillperch", "ember_koi", "rainbow_eel");
        assertThat(names("sky_river", "autumn", 20)).containsExactly("rainbow_eel");
        assertThat(names("Stream", "Spring", 8)).containsExactly("rillperch", "ember_koi");
    }

    @Test
    void nothingBitesOutsideTheRise() {
        assertThat(IslandFishery.biting(11)).isFalse();
        assertThat(IslandFishery.biting(5)).isFalse();
        assertThat(IslandFishery.biting(22)).isFalse();
        assertThat(IslandFishery.biting(6)).isTrue();
        assertThat(IslandFishery.biting(21)).isTrue();
        assertThat(IslandFishery.dusk(16)).isFalse();
        assertThat(IslandFishery.dusk(22)).isFalse();
        assertThat(names("lake", "spring", 13)).isEmpty();
        assertThat(IslandFishery.at(sky, null, "ocean_basin", "spring", 7).orElseThrow().size()).isEqualTo(1);
    }

    @Test
    void anIslandTableFeedsTheOddsEngine() {
        FishTable river = IslandFishery.at(sky, island, "sky_river", "spring", 19).orElseThrow();
        FishingOdds.Breakdown calm = FishingOdds.exact(river, Conditions.atHour(19, false), AnglerSkill.OLD_HAND);
        FishingOdds.Breakdown storm = FishingOdds.exact(river, Conditions.atHour(19, true), AnglerSkill.OLD_HAND);
        // the storm makes the eel bite more often, but its shorter window costs even an old hand landings
        assertThat(river.biteChance("rainbow_eel", storm.conditions())).isGreaterThan(river.biteChance("rainbow_eel", calm.conditions()));
        assertThat(storm.lines().get(2).catchChance()).isLessThan(calm.lines().get(2).catchChance());
    }

    @Test
    void nativeFishFromASeedAreStableDistinctAndNative() {
        List<String> a = IslandFishery.nativeFish(sky, 1234L, 2);
        assertThat(a).hasSize(2).doesNotHaveDuplicates().isSorted();
        assertThat(IslandFishery.nativeFish(sky, 1234L, 2)).isEqualTo(a);
        assertThat(IslandFishery.nativeFish(sky, 99L, 4)).containsExactly("ember_koi", "glassfin", "rillperch", "skytrout");
        assertThat(IslandFishery.nativeFish(sky, 99L, 0)).isEmpty();
        boolean differs = false;
        for (long s = 0; s < 20 && !differs; s++) {
            differs = !IslandFishery.nativeFish(sky, s, 2).equals(a);
        }
        assertThat(differs).isTrue();
        assertThatThrownBy(() -> IslandFishery.nativeFish(sky, 1, 5)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> IslandFishery.nativeFish(sky, 1, -1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void rejectsUnknownSpotsSeasonsHoursAndVisitorsAsNatives() {
        assertThatThrownBy(() -> names("bathtub", "spring", 8)).hasMessageContaining("spot");
        assertThatThrownBy(() -> names(null, "spring", 8)).hasMessageContaining("spot");
        assertThatThrownBy(() -> names("lake", "monsoon", 8)).hasMessageContaining("season");
        assertThatThrownBy(() -> names("lake", "spring", 24)).hasMessageContaining("hour");
        assertThatThrownBy(() -> names("lake", "spring", -1)).hasMessageContaining("hour");
        assertThatThrownBy(() -> IslandFishery.at(sky, List.of("basin_ray"), "lake", "spring", 8))
                .hasMessageContaining("visitor");
        assertThatThrownBy(() -> IslandFishery.at(sky, List.of("nope"), "lake", "spring", 8)).hasMessageContaining("nope");
    }
}
