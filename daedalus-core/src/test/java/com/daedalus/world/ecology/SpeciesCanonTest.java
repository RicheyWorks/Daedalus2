// SPDX-License-Identifier: MIT

package com.daedalus.world.ecology;

import org.junit.jupiter.api.Test;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class SpeciesCanonTest {

    private final SpeciesCanon canon = SpeciesCanon.get();

    @Test
    void theWholeComputerPetsCatalogIsHere() {
        // The catalog's 221 kinds and its rarity split, exactly (web/src/lib/pets/catalog.ts).
        assertThat(canon.all()).hasSize(221);
        Map<String, Integer> rarity = new HashMap<>();
        canon.all().forEach(s -> rarity.merge(s.rarity(), 1, Integer::sum));
        assertThat(rarity).containsOnlyKeys("COMMON", "UNCOMMON", "RARE", "LEGENDARY");
        assertThat(canon.byKey("red_panda").name()).isEqualTo("Red Panda");
        assertThat(canon.all().get(0).key()).isEqualTo("red_panda");
    }

    @Test
    void everyGuildIsPopulatedAndClassificationIsSane() {
        for (Guild g : Guild.values()) {
            assertThat(canon.guild(g)).as("guild %s", g).isNotEmpty();
        }
        assertThat(canon.byKey("goldfish").guild()).isEqualTo(Guild.POND);
        assertThat(canon.byKey("barn_owl").guild()).isEqualTo(Guild.CANOPY);
        assertThat(canon.byKey("fly_agaric").guild()).isEqualTo(Guild.DECOMPOSER);
        assertThat(canon.byKey("ground_dragon").guild()).isEqualTo(Guild.STARBORN);
        assertThat(canon.byKey("octopus").guild()).isEqualTo(Guild.MARINE);
        // Small fast breeders are r-selected, big slow ones K.
        assertThat(canon.byKey("hamster").rSelected()).isTrue();
        assertThat(canon.byKey("black_bear").rSelected()).isFalse();
        // Wings and spores cross the sky alone; a rabbit needs an ark.
        assertThat(canon.byKey("monarch").disperses()).isTrue();
        assertThat(canon.byKey("puffball").disperses()).isTrue();
        assertThat(canon.byKey("rabbit").disperses()).isFalse();
        for (Species s : canon.all()) {
            assertThat(Set.of("TINY", "SMALL", "MEDIUM", "LARGE", "SESSILE")).contains(s.size());
        }
    }

    @Test
    void theStrategyRuleHoldsOnEveryRow() {
        // build_species.py: R iff TINY/SMALL or a decomposer. A hand edit to the TSV that breaks the
        // rule fails here, since CI cannot rerun the generator without the ComputerPets source.
        for (Species s : canon.all()) {
            boolean r = "TINY".equals(s.size()) || "SMALL".equals(s.size()) || s.guild() == Guild.DECOMPOSER;
            assertThat(s.rSelected()).as(s.key()).isEqualTo(r);
        }
    }

    @Test
    void malformedRowsAreRefusedWithTheirLineNumber() {
        String bad = "# header\nfox\tFox\tCOMMON\tSly\tMEADOW\tMEDIUM\tX\t0\n";
        assertThatThrownBy(() -> SpeciesCanon.parse(new ByteArrayInputStream(bad.getBytes(StandardCharsets.UTF_8))))
                .hasMessageContaining("row 2");
        String dup = "a\tA\tCOMMON\tx\tMEADOW\tSMALL\tR\t0\na\tA\tCOMMON\tx\tMEADOW\tSMALL\tR\t0\n";
        assertThatThrownBy(() -> SpeciesCanon.parse(new ByteArrayInputStream(dup.getBytes(StandardCharsets.UTF_8))))
                .hasMessageContaining("Duplicate");
    }
}
