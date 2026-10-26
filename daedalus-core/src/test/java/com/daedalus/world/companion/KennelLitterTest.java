// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import static org.assertj.core.api.Assertions.assertThat;

import com.daedalus.world.companion.KennelLitter.Attempt;
import com.daedalus.world.companion.KennelLitter.Parent;
import com.daedalus.world.companion.TonicBrewer.Brew;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

class KennelLitterTest {
    private static final Parent TANK = new Parent("tank", TuringCoat.LABYRINTH_LINE, null);
    private static final Parent LUNA = new Parent("luna", TuringCoat.LABYRINTH_LINE, 9);
    private static TonicBrewer brewer;

    @BeforeAll
    static void load() throws Exception {
        Path p = Path.of("..", "tools", "islands", "kennel-isle", "tonics.json");
        brewer = new TonicBrewer(TonicBook.load(Files.exists(p) ? p : Path.of("tools", "islands", "kennel-isle", "tonics.json")));
    }

    private static Optional<Brew> bond(String coat) {
        return brewer.brew(List.of("Dozeleaf", "Starkibble"), coat, "other", 1, false);
    }

    @Test
    void bondRecipeCarriesBreedBonus() {
        Optional<Brew> b = bond("None");
        assertThat(b).isPresent();
        assertThat(b.get().recipe().breedChancePct()).isEqualTo(20.0);
        assertThat(KennelLitter.chancePct(b)).isEqualTo(30.0 + 20.0 * b.get().factor());
        assertThat(KennelLitter.chancePct(b)).isGreaterThan(KennelLitter.chancePct(Optional.empty()));
    }

    @Test
    void nonBreedingBrewAddsNothing() {
        Optional<Brew> mend = brewer.brew(List.of("Barkbalm", "Pawmint"), "None", "other", 1, false);
        assertThat(mend).isPresent();
        assertThat(KennelLitter.chancePct(mend)).isEqualTo(KennelLitter.BASE_PCT);
    }

    @Test
    void observedRatesMatchOdds() {
        double base = KennelLitter.observedRate(TANK, LUNA, Optional.empty(), 0, 5000);
        assertThat(base).isBetween(0.28, 0.32);
        Optional<Brew> b = bond("None");
        double p = KennelLitter.chancePct(b) / 100;
        assertThat(KennelLitter.observedRate(TANK, LUNA, b, 0, 5000)).isBetween(p - 0.02, p + 0.02);
    }

    @Test
    void litterSizeAndGenesBounded() {
        int seen = 0;
        for (long s = 0; s < 400; s++) {
            Attempt a = KennelLitter.pair(TANK, LUNA, bond("None"), s);
            if (a.success()) {
                seen++;
                assertThat(a.litter()).hasSizeBetween(1, KennelLitter.MAX_LITTER);
                for (KennelLitter.Pup p : a.litter()) {
                    assertThat(Math.abs(p.genes().feed() - TuringCoat.LABYRINTH_LINE.feed()))
                        .isLessThanOrEqualTo(TuringCoat.MUTATION);
                    assertThat(p.name()).startsWith("tank-luna-");
                }
            } else {
                assertThat(a.litter()).isEmpty();
            }
        }
        assertThat(seen).isGreaterThan(100);
    }

    @Test
    void labyrinthPairThrowsLabyrinthPups() {
        Attempt a = null;
        for (long s = 0; a == null || !a.success(); s++) {
            a = KennelLitter.pair(TANK, LUNA, bond("Labyrinth"), s);
        }
        assertThat(a.litter().get(0).coat(1)).isEqualTo("Labyrinth");
    }

    @Test
    void restingOrSamePetBlocked() {
        Parent tired = new Parent("bo", TuringCoat.SPOTTED_LINE, 3);
        assertThat(KennelLitter.pair(TANK, tired, bond("None"), 1).blockedReason()).isEqualTo("parent resting");
        assertThat(KennelLitter.pair(TANK, TANK, bond("None"), 1).blockedReason()).isEqualTo("same pet");
        assertThat(new Parent("x", TuringCoat.SPOTTED_LINE, 7).rested()).isTrue();
    }

    @Test
    void deterministicPerSeed() {
        assertThat(KennelLitter.pair(TANK, LUNA, bond("None"), 42)).isEqualTo(KennelLitter.pair(TANK, LUNA, bond("None"), 42));
    }
}
