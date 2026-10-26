// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import static org.assertj.core.api.Assertions.assertThat;

import com.daedalus.world.companion.TonicBook.Recipe;
import com.daedalus.world.companion.TonicBottler.Bottle;
import com.daedalus.world.companion.TonicBottler.Bottling;
import com.daedalus.world.companion.TonicBottler.Tier;
import com.daedalus.world.companion.TonicBottler.Water;
import com.daedalus.world.companion.TonicBrewer.Brew;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.OptionalInt;
import org.junit.jupiter.api.Test;

class TonicBottlerTest {
    private static final Map<String, Integer> FULL = Map.of("bottle", 5, "cork", 5, "wax", 5, "ark_glass", 1);

    private static Brew brew(double factor) {
        Recipe r = new Recipe("bond", "Bond", List.of("Dozeleaf", "Starkibble"), "calm", "round", "soft", 600,
            "drink", List.of(), List.of(), 20.0);
        return new Brew(r, factor, List.of(), 600);
    }

    @Test
    void qualityTierFromStrengthWaterAndRoll() {
        assertThat(TonicBottler.qualityTier(0.5, Water.RAW, false)).isEqualTo(Tier.T1);
        assertThat(TonicBottler.qualityTier(0.6, Water.FILTERED, false)).isEqualTo(Tier.T1);
        assertThat(TonicBottler.qualityTier(0.8, Water.FILTERED, false)).isEqualTo(Tier.T2);
        assertThat(TonicBottler.qualityTier(1.0, Water.SPRING, true)).isEqualTo(Tier.T3);
        assertThat(TonicBottler.score(1.0, Water.SPRING, true)).isEqualTo(75);
        assertThat(TonicBottler.qualityTier(2.0, Water.SPRING, false)).isEqualTo(Tier.T4);
        assertThat(TonicBottler.qualityTier(2.0, Water.FILTERED, true)).isEqualTo(Tier.T3);
        assertThat(TonicBottler.score(5.0, Water.FILTERED, false)).isEqualTo(100);
    }

    @Test
    void t4UsesArkGlassAndSpendsMaterials() {
        Bottling b = TonicBottler.bottle(brew(2.0), Water.SPRING, false, FULL, 1);
        assertThat(b.bottle()).isPresent();
        assertThat(b.bottle().get().tier()).isEqualTo(Tier.T4);
        assertThat(b.remaining()).containsEntry("ark_glass", 0).containsEntry("bottle", 5).containsEntry("wax", 4);
        assertThat(Tier.T4.materials()).containsKey("ark_glass").doesNotContainKey("bottle");
    }

    @Test
    void shortMaterialsDowngradeOrFail() {
        Bottling noGlass = TonicBottler.bottle(brew(2.0), Water.SPRING, false, Map.of("bottle", 1, "cork", 1, "wax", 1), 0);
        assertThat(noGlass.qualityTier()).isEqualTo(Tier.T4);
        assertThat(noGlass.bottle().get().tier()).isEqualTo(Tier.T3);
        Bottling bare = TonicBottler.bottle(brew(2.0), Water.SPRING, false, Map.of("bottle", 1), 0);
        assertThat(bare.bottle().get().tier()).isEqualTo(Tier.T1);
        Bottling none = TonicBottler.bottle(brew(2.0), Water.SPRING, false, Map.of("cork", 2), 0);
        assertThat(none.bottle()).isEmpty();
        assertThat(none.remaining()).containsExactly(Map.entry("cork", 2));
    }

    @Test
    void bottlesAgeDownATierPerShelfLifeThenSpoil() {
        Bottle b = new Bottle("bond", Tier.T3, 600, 0);
        assertThat(TonicBottler.tierAt(b, 13)).isEqualTo(OptionalInt.of(3));
        assertThat(TonicBottler.tierAt(b, 14)).isEqualTo(OptionalInt.of(2));
        assertThat(TonicBottler.tierAt(b, 20)).isEqualTo(OptionalInt.of(2));
        assertThat(TonicBottler.tierAt(b, 21)).isEqualTo(OptionalInt.of(1));
        assertThat(TonicBottler.tierAt(b, 23)).isEqualTo(OptionalInt.of(1));
        assertThat(TonicBottler.tierAt(b, 24)).isEmpty();
        assertThat(TonicBottler.durationAt(b, 0)).isEqualTo(900);
        assertThat(TonicBottler.durationAt(b, 14)).isEqualTo(750);
        assertThat(TonicBottler.durationAt(b, 24)).isZero();
    }

    @Test
    void arkGlassCellarQuest() {
        List<Bottle> cellar = List.of(new Bottle("bond", Tier.T4, 600, 0), new Bottle("calm", Tier.T3, 600, 0),
            new Bottle("calm", Tier.T3, 600, 0), new Bottle("zest", Tier.T3, 600, 1));
        assertThat(TonicBottler.cellarReady(cellar, 10)).isTrue();
        assertThat(TonicBottler.cellarReady(cellar, 14)).isFalse();
        assertThat(TonicBottler.cellarReady(cellar.subList(1, 4), 0)).isFalse();
    }

    @Test
    void bottlesARealBrewFromTheTonicBook() throws Exception {
        Path p = Path.of("..", "tools", "islands", "kennel-isle", "tonics.json");
        TonicBrewer brewer = new TonicBrewer(TonicBook.load(Files.exists(p) ? p
            : Path.of("tools", "islands", "kennel-isle", "tonics.json")));
        Optional<Brew> bond = brewer.brew(List.of("Dozeleaf", "Starkibble"), "None", TonicBrewer.CANE_CORSO, 1, false);
        assertThat(bond).isPresent();
        Bottling b = TonicBottler.bottle(bond.get(), Water.FILTERED, false, FULL, 3);
        assertThat(b.bottle()).isPresent();
        assertThat(b.bottle().get().recipeId()).isEqualTo(bond.get().recipe().id());
        assertThat(b.bottle().get().tier()).isEqualTo(TonicBottler.qualityTier(bond.get().factor(), Water.FILTERED, false));
        assertThat(b.bottle().get().baseDurationSec()).isEqualTo(bond.get().durationSec());
    }
}