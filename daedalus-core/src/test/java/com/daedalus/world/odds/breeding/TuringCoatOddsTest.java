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

class TuringCoatOddsTest {

    @Test
    void genotypesShowTheRightCoat() {
        assertThat(Genotype.parse("sb ea cm").coat()).isEqualTo(new Coat(Pattern.SPOTS, Colour.SMOKE, false));
        assertThat(Genotype.parse("PB EE MM").coat()).isEqualTo(new Coat(Pattern.STRIPES, Colour.EMBER, true));
        assertThat(Genotype.parse("PPAACC").coat()).isEqualTo(new Coat(Pattern.PLAIN, Colour.ASH, false));
        assertThat(Genotype.parse("BS AE MC").toString()).isEqualTo("SB EA CM");
        assertThat(Genotype.parse("PP EE MC").carriesStormMark()).isTrue();
        assertThat(Genotype.parse("PP EE CC").carriesStormMark()).isFalse();
        assertThat(new Coat(Pattern.STRIPES, Colour.SMOKE, true).describe()).isEqualTo("storm-marked smoke stripes");
        assertThat(new Coat(Pattern.SPOTS, Colour.EMBER, false).describe()).isEqualTo("ember spots");
    }

    @Test
    void patternsAreTheG21TuringCoatLinesAndGrowTheirKeys() {
        assertThat(Pattern.SPOTS.genes()).isEqualTo(com.daedalus.world.companion.TuringCoat.SPOTTED_LINE);
        assertThat(Pattern.PLAIN.coatKey()).isEqualTo("None");
        assertThat(Genotype.parse("LP EE CC").coat().pattern()).isEqualTo(Pattern.LABYRINTH);
        for (String g : new String[] {"SP EE CC", "BL EE CC", "LP EE CC", "PP EE CC"}) {
            Genotype pup = Genotype.parse(g);
            assertThat(pup.grownCoatKey(1)).as(g).isEqualTo(pup.coat().pattern().coatKey());
            assertThat(pup.turingGenes()).isEqualTo(pup.coat().pattern().genes());
        }
    }

    @Test
    void badGenesAreRefused() {
        assertThatThrownBy(() -> Genotype.parse(null)).hasMessageContaining("no genotype");
        assertThatThrownBy(() -> Genotype.parse("SB EA")).hasMessageContaining("3 letter pairs");
        assertThatThrownBy(() -> Genotype.parse("XB EA CM")).hasMessageContaining("pattern");
        assertThatThrownBy(() -> Genotype.parse("SX EA CM")).hasMessageContaining("pattern");
        assertThatThrownBy(() -> Genotype.parse("SB XA CM")).hasMessageContaining("colour");
        assertThatThrownBy(() -> Genotype.parse("SB EX CM")).hasMessageContaining("colour");
        assertThatThrownBy(() -> Genotype.parse("SB EA XM")).hasMessageContaining("storm");
        assertThatThrownBy(() -> Genotype.parse("SB EA CX")).hasMessageContaining("storm");
        assertThatThrownBy(() -> new Coat(null, Colour.ASH, false)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Coat(Pattern.PLAIN, null, false)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void crossTablesAreExactMendelianOdds() {
        Genotype a = Genotype.parse("SP EA CM");
        Genotype b = Genotype.parse("BP EA CM");
        Map<Coat, Double> t = CoatOdds.cross(a, b);
        assertThat(t.values().stream().mapToDouble(Double::doubleValue).sum()).isCloseTo(1.0, within(1e-12));
        assertThat(CoatOdds.chance(a, b, c -> c.pattern() == Pattern.SPOTS)).isEqualTo(0.5);
        assertThat(CoatOdds.chance(a, b, c -> c.pattern() == Pattern.STRIPES)).isEqualTo(0.25);
        assertThat(CoatOdds.chance(a, b, c -> c.pattern() == Pattern.PLAIN)).isEqualTo(0.25);
        assertThat(CoatOdds.chance(a, b, c -> c.colour() == Colour.SMOKE)).isEqualTo(0.5);
        assertThat(CoatOdds.stormMarkedChance(a, b)).isEqualTo(0.25);
        assertThat(t.get(new Coat(Pattern.PLAIN, Colour.ASH, true))).isEqualTo(1.0 / 64);
        assertThat(t.keySet().iterator().next()).isEqualTo(new Coat(Pattern.SPOTS, Colour.EMBER, false));
        assertThatThrownBy(() -> t.put(new Coat(Pattern.SPOTS, Colour.ASH, true), 1.0)).isInstanceOf(UnsupportedOperationException.class);
    }

    @Test
    void trueBreedingPairsHaveOneCoat() {
        Map<Coat, Double> t = CoatOdds.cross(Genotype.parse("PP AA MM"), Genotype.parse("PP AA MM"));
        assertThat(t).containsExactly(Map.entry(new Coat(Pattern.PLAIN, Colour.ASH, true), 1.0));
        assertThat(CoatOdds.carrierChance(Genotype.parse("PP AA MM"), Genotype.parse("PP AA MM"))).isNaN();
        assertThat(CoatOdds.stormMarkedChance(Genotype.parse("SS EE CC"), Genotype.parse("PP AA MM"))).isZero();
    }

    @Test
    void carrierOddsFollowBayes() {
        assertThat(CoatOdds.carrierChance(Genotype.parse("PP EE CM"), Genotype.parse("PP EE CM"))).isCloseTo(2.0 / 3, within(1e-12));
        assertThat(CoatOdds.carrierChance(Genotype.parse("PP EE CC"), Genotype.parse("PP EE MM"))).isEqualTo(1.0);
        assertThat(CoatOdds.carrierChance(Genotype.parse("PP EE CC"), Genotype.parse("PP EE CC"))).isZero();
    }

    @Test
    void littersAreSeededAndFollowTheOdds() {
        Genotype a = Genotype.parse("SP EA CM");
        Genotype b = Genotype.parse("BP EA CM");
        assertThat(CoatOdds.litter(a, b, 9, 6)).hasSize(6).isEqualTo(CoatOdds.litter(a, b, 9, 6));
        int marked = 0;
        int n = 0;
        for (long seed = 0; seed < 1000; seed++) {
            for (Genotype pup : CoatOdds.litter(a, b, seed, 8)) {
                n++;
                if (pup.coat().stormMarked()) {
                    marked++;
                }
            }
        }
        assertThat(marked / (double) n).isCloseTo(0.25, within(0.02));
        assertThatThrownBy(() -> CoatOdds.litter(a, b, 1, 0)).hasMessageContaining("1-8");
        assertThatThrownBy(() -> CoatOdds.litter(a, b, 1, 9)).hasMessageContaining("1-8");
    }

    @Test
    void theStormcoatQuest() {
        Genotype a = Genotype.parse("SP EA CM");
        Genotype b = Genotype.parse("BP EA CM");
        assertThat(StormcoatQuest.advice(a, b)).isEqualTo("SP EA CM with BP EA CM: 25.0% of pups come storm-marked, about one in 4.");
        assertThat(StormcoatQuest.advice(Genotype.parse("SS EE CC"), b)).contains("never throw a stormcoat");
        StormcoatQuest q = new StormcoatQuest();
        assertThat(q.record(List.of(Genotype.parse("PP EE CM")))).isFalse();
        assertThat(q.done()).isFalse();
        assertThat(q.record(List.of(Genotype.parse("PP EE CC"), Genotype.parse("PP EE MM")))).isTrue();
        assertThat(q.done()).isTrue();
        assertThat(q.record(List.of(Genotype.parse("PP EE MM")))).isFalse();
        assertThat(q.litters()).isEqualTo(3);
        assertThat(q.pups()).isEqualTo(4);
    }
}
