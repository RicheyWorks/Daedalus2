// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.companion.KennelPantry.Day;
import com.daedalus.world.companion.KennelPantry.DayReport;
import com.daedalus.world.companion.KennelPantry.Pet;
import com.daedalus.world.companion.KennelPantry.State;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

class KennelPantryTest {
    private static final List<Pet> PACK = List.of(
        new Pet("pip", "pup"), new Pet("rex", "dog"), new Pet("tank", "cane_corso"), new Pet("bo", "dog"));
    private static KennelPantry k;

    @BeforeAll
    static void load() throws Exception {
        Path p = Path.of("..", "data", "islands", "kennel-food-v1.json");
        k = KennelPantry.load(Files.exists(p) ? p : Path.of("data", "islands", "kennel-food-v1.json"));
    }

    @Test
    void needAndCorsoEatsFirst() {
        assertThat(k.need(PACK)).isEqualTo(1 + 1 + 2 + 1);
        assertThat(k.eatingOrder(PACK)).extracting(Pet::name).containsExactly("tank", "rex", "bo", "pip");
    }

    @Test
    void goatsNeedHayToMilk() {
        DayReport d = k.day(k.empty(), new Day(4, 2, 10), PACK);
        assertThat(d.milkL()).isEqualTo(3.0);
        assertThat(d.crafted()).isEqualTo(12);
        assertThat(d.spoiledMilkL()).isZero();
    }

    @Test
    void unusedMilkSpoilsStarkibbleKeeps() {
        DayReport d = k.day(k.empty(), new Day(3, 3, 2), PACK);
        assertThat(d.milkL()).isEqualTo(4.5);
        assertThat(d.crafted()).isEqualTo(8);
        assertThat(d.spoiledMilkL()).isEqualTo(2.5);
        assertThat(d.state().starkibble()).isZero();
        DayReport e = k.day(k.empty(), new Day(1, 1, 5), PACK);
        assertThat(e.state().starkibble()).isEqualTo(4);
    }

    @Test
    void shortagesHitTheBackOfThePack() {
        DayReport d = k.day(new State(3, 0, java.util.Map.of()), new Day(0, 0, 0), PACK);
        assertThat(d.hungry()).containsExactly("bo", "pip");
        assertThat(d.served()).isEqualTo(3);
        assertThat(d.state().kibble()).isZero();
    }

    @Test
    void corsoSkippedWhenShortButSmallerRationsStillServed() {
        DayReport d = k.day(new State(1, 0, java.util.Map.of()), new Day(0, 0, 0), PACK);
        assertThat(d.hungry()).containsExactly("tank", "bo", "pip");
        assertThat(d.served()).isEqualTo(1);
    }

    @Test
    void bowlCapacityLimitsServing() {
        List<Pet> big = new ArrayList<>();
        for (int i = 0; i < 8; i++) {
            big.add(new Pet("c" + i, "cane_corso"));
        }
        DayReport d = k.day(new State(100, 0, java.util.Map.of()), new Day(0, 0, 0), big);
        assertThat(d.served()).isEqualTo(12);
        assertThat(d.hungry()).hasSize(2);
        assertThat(k.minGoats(big)).isEqualTo(-1);
    }

    @Test
    void hungerStagesDrainAndReset() {
        State s = k.empty();
        for (int i = 0; i < 6; i++) {
            s = k.day(s, new Day(0, 0, 0), PACK).state();
        }
        assertThat(s.hunger().get("tank")).isEqualTo(6);
        assertThat(s.drainPct(k.rules(), "tank")).isEqualTo(50);
        s = k.day(s, new Day(2, 2, 2), PACK).state();
        assertThat(s.hunger()).isEmpty();
    }

    @Test
    void packOrderQuest() {
        // pack needs 5 portions/day; 1 goat = 1.5 L = 1 batch = 4 portions (short), 2 goats = 3 batches = 12.
        assertThat(k.minGoats(PACK)).isEqualTo(2);
        assertThat(k.packOrder(PACK, new Day(2, 1, 5)).passed()).isFalse();
        var ok = k.packOrder(PACK, new Day(2, 2, 5));
        assertThat(ok.passed()).isTrue();
        assertThat(ok.log()).hasSize(3);
        assertThat(ok.questId()).isEqualTo("kennel_pack_order");
        assertThat(k.packOrder(PACK, new Day(4, 4, 0)).passed()).isFalse();
    }

    @Test
    void deterministic() {
        assertThat(k.packOrder(PACK, new Day(2, 2, 5))).isEqualTo(k.packOrder(PACK, new Day(2, 2, 5)));
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> KennelPantry.parse("{\"version\":9}")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> k.need(List.of(new Pet("x", "wolf")))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new State(-1, 0, java.util.Map.of())).isInstanceOf(IllegalArgumentException.class);
    }
}
