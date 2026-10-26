// SPDX-License-Identifier: MIT

package com.daedalus.world.ecology;

import com.daedalus.world.island.IslandGenerator;
import com.daedalus.world.island.IslandTraits;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

/**
 * The stepper against the ecology it claims to be. Each test is a textbook result: logistic growth
 * saturates at K, a guild shares its habitat, small populations blink out, bigger islands hold more
 * kinds, nearer islands are colonised faster, and the whole thing replays exactly from its seed.
 */
class EcologyTest {

    private final SpeciesCanon canon = SpeciesCanon.get();
    private final Habitat isle11 = Habitat.of(IslandGenerator.generate(11).traits());

    @Test
    void theClosedFormsMatchCsrbt() {
        // TheoreticalModels: S* = c/(c+e)·P; logistic K/(1+((K−N0)/N0)e^(−rt)).
        assertThat(Biogeography.equilibrium(0.3, 0.1, 40)).isCloseTo(30.0, within(1e-9));
        assertThat(Biogeography.equilibrium(0, 0, 40)).isZero();
        assertThat(Biogeography.richnessAt(0.3, 0.1, 40, 0, 0)).isZero();
        assertThat(Biogeography.richnessAt(0.3, 0.1, 40, 0, 1e6)).isCloseTo(30.0, within(1e-9));
        assertThat(Biogeography.logisticAt(0.5, 100, 10, 0)).isCloseTo(10.0, within(1e-9));
        assertThat(Biogeography.logisticAt(0.5, 100, 10, 200)).isCloseTo(100.0, within(1e-6));
        Biogeography.Environment env = new Biogeography.Environment(4, 1, 1, 0.5);
        assertThat(env.colonization(1)).isCloseTo(Math.exp(-0.5), within(1e-12));
        assertThat(env.extinction(1)).isEqualTo(0.25);
        assertThatThrownBy(() -> new Biogeography.Environment(0, 1, 1, 0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void habitatIsReadOffTheIslandsOwnTerrain() {
        IslandTraits t = IslandGenerator.generate(11).traits();
        assertThat(isle11.of(Guild.CANOPY)).isEqualTo(12.0 * t.trees());
        assertThat(isle11.of(Guild.POND)).isEqualTo(t.pondColumns() + t.streamLength());
        assertThat(isle11.of(Guild.STARBORN)).isEqualTo(6.0 * t.crystals());
        assertThat(isle11.of(Guild.MARINE)).isZero();
        assertThat(isle11.of(Guild.MEADOW)).isPositive();
        assertThat(isle11.area()).isGreaterThan(t.columns());
    }

    @Test
    void aLoneSpeciesGrowsLogisticallyToItsCarryingCapacity() {
        Species hamster = canon.byKey("hamster");
        Community c = new Community();
        c.arrive(hamster, 4, isle11);
        double k = Community.capacity(hamster, isle11);
        double previous = 4;
        boolean neverOvershotFar = true;
        for (int d = 0; d < 120; d++) {
            c.day(canon, isle11, d);
            double n = c.count("hamster");
            neverOvershotFar &= n < k * 1.15;
            previous = n;
        }
        assertThat(previous).isCloseTo(k, within(k * 0.1));
        assertThat(neverOvershotFar).isTrue();
    }

    @Test
    void aGuildSharesItsHabitat() {
        Community c = new Community();
        for (String key : new String[] {"hamster", "rabbit", "guinea_pig", "chinchilla"}) {
            c.arrive(canon.byKey(key), 3, isle11);
        }
        for (int d = 0; d < 200; d++) {
            c.day(canon, isle11, d);
        }
        double fullness = 0;
        for (Map.Entry<String, Double> e : c.abundance().entrySet()) {
            fullness += e.getValue() / Community.capacity(canon.byKey(e.getKey()), isle11);
        }
        // Four small grazers together fill the meadow about once — not four times over.
        assertThat(fullness).isBetween(0.85, 1.15);
    }

    @Test
    void theSeaFellAwaySoMarineKindsCannotLand() {
        Community c = new Community();
        assertThat(c.arrive(canon.byKey("octopus"), 10, isle11)).isZero();
        assertThat(c.abundance()).isEmpty();
    }

    @Test
    void aSingleFounderUsuallyFails() {
        int survived = 0;
        for (long seed = 0; seed < 200; seed++) {
            Community c = new Community();
            c.arrive(canon.byKey("black_bear"), 1.2, isle11);
            for (int d = 0; d < 10; d++) {
                c.day(canon, isle11, seed * 1000 + d);
            }
            survived += c.count("black_bear") > 0 ? 1 : 0;
        }
        // A K-selected founder below FRAGILE runs the 12% daily risk for days: most lines die out.
        assertThat(survived).isLessThan(100);
    }

    @Test
    void biggerIslandsHoldMoreKinds() {
        // The species–area relationship, from wild-sky rain alone on two isolated islands.
        double small = 0;
        double big = 0;
        for (long seed = 1; seed <= 6; seed++) {
            Ecosystem eco = new Ecosystem(canon);
            eco.addIsle(new Ecosystem.Isle(0, Habitat.of(IslandGenerator.generate(seed, 9).traits()), 0, 0));
            eco.addIsle(new Ecosystem.Isle(1, Habitat.of(IslandGenerator.generate(seed, 26).traits()), 1e6, 0));
            for (int d = 0; d < 600; d++) {
                eco.step(seed);
            }
            small += eco.community(0).diversity().richness();
            big += eco.community(1).diversity().richness();
        }
        assertThat(big).isGreaterThan(small * 1.3);
    }

    @Test
    void nearerIslandsAreColonisedFaster() {
        int near = 0;
        int far = 0;
        for (long seed = 1; seed <= 8; seed++) {
            Ecosystem eco = new Ecosystem(canon);
            Habitat h = isle11;
            eco.addIsle(new Ecosystem.Isle(0, h, 0, 0));
            eco.addIsle(new Ecosystem.Isle(1, h, 96, 0));
            eco.addIsle(new Ecosystem.Isle(2, h, 480, 0));
            for (Species s : canon.all()) {
                if (s.disperses()) {
                    eco.community(0).arrive(s, 20, h);
                }
            }
            for (int d = 0; d < 30; d++) {
                Ecosystem.DayReport r = eco.step(seed);
                near += r.drifted().getOrDefault(1, java.util.List.of()).size();
                far += r.drifted().getOrDefault(2, java.util.List.of()).size();
            }
        }
        // e^(−96/120) ≈ 0.45 vs e^(−480/120) ≈ 0.02 per source: the near island gets far more.
        assertThat(near).isGreaterThan(far * 5);
    }

    @Test
    void onlyFliersAndSporesArriveWithoutAnArk() {
        Ecosystem eco = new Ecosystem(canon);
        eco.addIsle(new Ecosystem.Isle(0, isle11, 0, 0));
        for (int d = 0; d < 500; d++) {
            eco.step(3);
        }
        for (String key : eco.community(0).abundance().keySet()) {
            assertThat(canon.byKey(key).disperses()).as(key).isTrue();
        }
    }

    @Test
    void anEcosystemReplaysExactlyFromItsSeed() {
        Map<String, Double> a = run(42);
        Map<String, Double> b = run(42);
        assertThat(a).isEqualTo(b).isNotEmpty();
        assertThat(run(43)).isNotEqualTo(a);
    }

    private Map<String, Double> run(long seed) {
        Ecosystem eco = new Ecosystem(canon);
        eco.addIsle(new Ecosystem.Isle(0, isle11, 0, 0));
        eco.addIsle(new Ecosystem.Isle(1, isle11, 96, 0));
        eco.community(0).arrive(canon.byKey("hamster"), 10, isle11);
        for (int d = 0; d < 200; d++) {
            eco.step(seed);
        }
        java.util.TreeMap<String, Double> out = new java.util.TreeMap<>(eco.community(0).abundance());
        eco.community(1).abundance().forEach((k, v) -> out.put("1:" + k, v));
        return out;
    }

    @Test
    void diversityMatchesTheFormulas() {
        Diversity even = Diversity.of(Map.of("a", 10.0, "b", 10.0, "c", 10.0, "d", 10.0));
        assertThat(even.richness()).isEqualTo(4);
        assertThat(even.shannon()).isCloseTo(Math.log(4), within(1e-12));
        assertThat(even.evenness()).isCloseTo(1.0, within(1e-12));
        assertThat(even.simpson()).isCloseTo(0.75, within(1e-12));
        Diversity one = Diversity.of(Map.of("a", 5.0));
        assertThat(one.shannon()).isZero();
        assertThat(one.evenness()).isZero();
        assertThat(Diversity.of(Map.of()).richness()).isZero();
    }
}
