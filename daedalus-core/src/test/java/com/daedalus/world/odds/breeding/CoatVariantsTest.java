// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.breeding;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.odds.breeding.Coat.Colour;
import com.daedalus.world.odds.breeding.Coat.Pattern;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class CoatVariantsTest {

    private static final CoatVariants TABLE = CoatVariants.load();

    @Test
    void deliveredTableCoversEveryCoat() {
        assertThat(TABLE.size()).isEqualTo(24);
        assertThat(TABLE.coversAllCoats()).isTrue();
    }

    @Test
    void keysFollowTheBlenderSchema() {
        assertThat(CoatVariants.key(new Coat(Pattern.PLAIN, Colour.ASH, true))).isEqualTo("None/ASH/Storm");
        assertThat(CoatVariants.key(new Coat(Pattern.SPOTS, Colour.EMBER, false))).isEqualTo("Spots/EMBER");
        assertThat(TABLE.material(new Coat(Pattern.STRIPES, Colour.SMOKE, true)))
                .isEqualTo("MI_Mob_CorsoPup_Coat_Smoke_Storm");
        assertThat(TABLE.material(Genotype.parse("SB EA CM").coat())).isEqualTo("MI_Mob_CorsoPup_Coat_Smoke");
    }

    @Test
    void materialOddsSumTheCrossTable() {
        Genotype mum = Genotype.parse("SP EA MC");
        Genotype dad = Genotype.parse("BP EA MC");
        Map<String, Double> odds = TABLE.materialOdds(mum, dad);
        assertThat(odds.values().stream().mapToDouble(Double::doubleValue).sum()).isCloseTo(1.0, within(1e-12));
        double storm = odds.entrySet().stream().filter(e -> e.getKey().endsWith("_Storm"))
                .mapToDouble(Map.Entry::getValue).sum();
        assertThat(storm).isCloseTo(CoatOdds.stormMarkedChance(mum, dad), within(1e-12));
        assertThat(odds.get("MI_Mob_CorsoPup_Coat_Smoke")).isCloseTo(0.5 * 0.75, within(1e-12));
    }

    @Test
    void litterMaterialsMatchTheLitter() {
        Genotype mum = Genotype.parse("SP EA MC");
        Genotype dad = Genotype.parse("BP EA MC");
        List<String> mats = TABLE.litterMaterials(mum, dad, 77, 6);
        List<Genotype> pups = CoatOdds.litter(mum, dad, 77, 6);
        assertThat(mats).hasSize(6);
        for (int i = 0; i < 6; i++) {
            assertThat(mats.get(i)).isEqualTo(TABLE.material(pups.get(i).coat()));
        }
    }

    @Test
    void rejectsBrokenTables() {
        assertThatThrownBy(() -> CoatVariants.fromJson("{}")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CoatVariants.fromJson("{\"lookup\": {}}"))
                .isInstanceOf(IllegalArgumentException.class);
        CoatVariants partial = CoatVariants.fromJson("{\"lookup\": {\"Spots/EMBER\": \"MI_X\"}}");
        assertThat(partial.coversAllCoats()).isFalse();
        assertThat(partial.find(new Coat(Pattern.SPOTS, Colour.EMBER, true))).isEmpty();
        assertThatThrownBy(() -> partial.material(new Coat(Pattern.PLAIN, Colour.ASH, false)))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
