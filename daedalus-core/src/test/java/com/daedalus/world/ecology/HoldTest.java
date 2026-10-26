// SPDX-License-Identifier: MIT

package com.daedalus.world.ecology;

import com.daedalus.world.island.IslandGenerator;
import org.junit.jupiter.api.Test;

import java.util.EnumMap;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Arks as the ecology's second road (ADR-023): founders are pairs of ark-bound kinds weighted by
 * rarity, stowaways board from strong populations, landing respects the island's habitat, and the
 * whole living state survives a restart bit for bit.
 */
class HoldTest {

    private final SpeciesCanon canon = SpeciesCanon.get();
    private final Habitat isle11 = Habitat.of(IslandGenerator.generate(11).traits());

    @Test
    void foundersArePairsOfKindsOnlyAnArkCanMove() {
        Hold hold = Hold.founders(11, canon);
        assertThat(hold.cargo()).hasSize(Hold.FOUNDER_KINDS);
        assertThat(hold.cargo().values()).allMatch(n -> n == Hold.PAIR);
        for (String key : hold.cargo().keySet()) {
            Species s = canon.byKey(key);
            assertThat(s).isNotNull();
            assertThat(Hold.needsArk(s)).as(key).isTrue();
            assertThat(s.guild()).isNotEqualTo(Guild.MARINE);
        }
        assertThat(Hold.founders(11, canon).cargo()).isEqualTo(hold.cargo());
        assertThat(Hold.founders(12, canon).cargo()).isNotEqualTo(hold.cargo());
    }

    @Test
    void rarityWeightsTheDraw() {
        Map<String, Integer> poolByRarity = new HashMap<>();
        for (Species s : canon.all()) {
            if (Hold.needsArk(s)) {
                poolByRarity.merge(s.rarity(), 1, Integer::sum);
            }
        }
        Map<String, Integer> drawn = new HashMap<>();
        for (long seed = 0; seed < 3000; seed++) {
            for (String key : Hold.founders(seed, canon).cargo().keySet()) {
                drawn.merge(canon.byKey(key).rarity(), 1, Integer::sum);
            }
        }
        double common = drawn.getOrDefault("COMMON", 0) / (double) poolByRarity.get("COMMON");
        double uncommon = drawn.getOrDefault("UNCOMMON", 0) / (double) poolByRarity.get("UNCOMMON");
        double rare = drawn.getOrDefault("RARE", 0) / (double) poolByRarity.get("RARE");
        double legendary = drawn.getOrDefault("LEGENDARY", 0) / (double) poolByRarity.get("LEGENDARY");
        // Per kind, a common rides more often than an uncommon, which rides more than a rare...
        assertThat(common).isGreaterThan(uncommon);
        assertThat(uncommon).isGreaterThan(rare);
        assertThat(rare).isGreaterThan(legendary);
        // ...but a legendary is not impossible.
        assertThat(drawn.getOrDefault("LEGENDARY", 0)).isPositive();
    }

    @Test
    void landingRespectsTheIslandsHabitat() {
        Map<Guild, Double> dry = new EnumMap<>(Guild.class);
        dry.put(Guild.MEADOW, 400.0);
        Habitat meadowOnly = new Habitat(dry);
        Species meadow = firstNeedingArk(Guild.MEADOW);
        Species pond = firstNeedingArk(Guild.POND);
        Hold hold = new Hold();
        hold.put(meadow.key(), 2);
        hold.put(pond.key(), 2);
        Community island = new Community();

        List<String> landed = hold.land(island, meadowOnly, canon);

        assertThat(landed).containsExactly(meadow.key());
        assertThat(island.count(meadow.key())).isEqualTo(2.0);
        assertThat(hold.cargo()).containsOnlyKeys(pond.key()); // waits aboard for a wetter island
        hold.land(island, isle11, canon);
        assertThat(hold.isEmpty()).isTrue();
    }

    @Test
    void stowawaysBoardOnlyFromStrongPopulationsAndTheHoldHasACeiling() {
        Community weak = new Community();
        for (Species s : canon.all()) {
            weak.put(s.key(), Hold.BOARD_MIN - 0.5);
        }
        Hold hold = new Hold();
        for (long seed = 0; seed < 40; seed++) {
            assertThat(hold.board(weak, seed)).isEmpty();
        }

        Community strong = new Community();
        for (Species s : canon.all()) {
            strong.put(s.key(), 50);
        }
        List<String> boarded = hold.board(strong, 7);
        assertThat(boarded).hasSize(Hold.CAPACITY);
        assertThat(hold.cargo()).hasSize(Hold.CAPACITY);
        for (String key : boarded) {
            assertThat(strong.count(key)).isEqualTo(50 - Hold.PAIR);
            assertThat(hold.cargo().get(key)).isEqualTo(Hold.PAIR);
        }
        // Already aboard can top up; nothing new fits.
        List<String> again = hold.board(strong, 8);
        assertThat(hold.cargo()).hasSize(Hold.CAPACITY);
        assertThat(boarded).containsAll(again);
    }

    @Test
    void anArkIsTheOnlyRoadForWalkers() {
        Ecosystem eco = new Ecosystem(canon);
        eco.addIsle(new Ecosystem.Isle(0, isle11, 0, 0));
        eco.addIsle(new Ecosystem.Isle(1, isle11, 5000, 0)); // beyond any drift
        Hold founders = Hold.founders(11, canon);
        founders.land(eco.community(0), isle11, canon);
        for (int d = 0; d < 150; d++) {
            eco.step(3);
        }
        assertThat(walkers(eco.community(1))).isZero();

        Hold ark = new Hold();
        long tries = 0;
        while (walkersIn(ark) == 0 && tries < 50) {
            ark.board(eco.community(0), tries++);
        }
        assertThat(walkersIn(ark)).as("a walker on island 0 is strong enough to board").isPositive();
        ark.land(eco.community(1), isle11, canon);
        assertThat(walkers(eco.community(1))).isPositive();
    }

    @Test
    void theLedgerRestoresTheLivingWorldExactly() {
        Ecosystem a = twoIsles();
        Map<String, Hold> holds = new TreeMap<>();
        holds.put("ark-0", Hold.founders(11, canon));
        holds.put("ark-1", Hold.founders(12, canon));
        holds.get("ark-0").land(a.community(0), isle11, canon);
        for (int d = 0; d < 60; d++) {
            a.step(9);
        }
        List<String> saved = EcologyLedger.toLines(1234L, a, holds);

        EcologyLedger.State state = EcologyLedger.fromLines(saved);
        assertThat(state.epoch()).isEqualTo(1234L);
        assertThat(state.day()).isEqualTo(60);
        Ecosystem b = twoIsles();
        b.setDay(state.day());
        state.isles().forEach((slot, counts) -> counts.forEach((k, n) -> b.community(slot).put(k, n)));
        Map<String, Hold> restored = new TreeMap<>();
        state.holds().forEach((id, counts) -> {
            Hold h = new Hold();
            counts.forEach(h::put);
            restored.put(id, h);
        });
        assertThat(EcologyLedger.toLines(1234L, b, restored)).isEqualTo(saved);

        for (int d = 0; d < 30; d++) {
            a.step(9);
            b.step(9);
        }
        assertThat(EcologyLedger.toLines(1234L, b, restored)).isEqualTo(EcologyLedger.toLines(1234L, a, holds));
    }

    @Test
    void theLedgerRefusesGarbage() {
        assertThatThrownBy(() -> EcologyLedger.fromLines(List.of("weather sunny")))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> EcologyLedger.fromLines(List.of("isle 0 cat")))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> EcologyLedger.fromLines(List.of("isle 0 cat=-1")))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> EcologyLedger.fromLines(List.of("hold")))
                .isInstanceOf(IllegalArgumentException.class);
        assertThat(EcologyLedger.fromLines(List.of("# only a comment", "")).isles()).isEmpty();
    }

    private Ecosystem twoIsles() {
        Ecosystem eco = new Ecosystem(canon);
        eco.addIsle(new Ecosystem.Isle(0, isle11, 0, 0));
        eco.addIsle(new Ecosystem.Isle(1, isle11, 96, 0));
        return eco;
    }

    private int walkers(Community c) {
        int n = 0;
        for (String key : c.abundance().keySet()) {
            if (Hold.needsArk(canon.byKey(key))) {
                n++;
            }
        }
        return n;
    }

    private int walkersIn(Hold h) {
        int n = 0;
        for (String key : h.cargo().keySet()) {
            if (Hold.needsArk(canon.byKey(key))) {
                n++;
            }
        }
        return n;
    }

    private Species firstNeedingArk(Guild g) {
        for (Species s : canon.guild(g)) {
            if (Hold.needsArk(s)) {
                return s;
            }
        }
        throw new AssertionError("no ark-bound kind in " + g);
    }
}
