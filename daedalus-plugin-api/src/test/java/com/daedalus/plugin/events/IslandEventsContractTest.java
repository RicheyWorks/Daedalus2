// SPDX-License-Identifier: MIT

package com.daedalus.plugin.events;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The island events added with ark voyages (ADR-020) and island life (ADR-024) shipped without tests,
 * which dropped this module's instruction coverage from the gate (0.96) to 0.76 and turned CI red.
 * These pin the contract plugins compile against: every field round-trips, and IslandLifeEvent's
 * collections are defensive, immutable copies (null becomes empty; richness iterates in slot order).
 */
class IslandEventsContractTest {

    @Test
    void arkVoyageEventCarriesEveryField() {
        Object src = new Object();
        ArkVoyageEvent e = new ArkVoyageEvent(src, "w1", ArkVoyageEvent.Kind.DEPARTED, "ark-7", 3, 9, 1_000L, 61_000L);
        assertThat(e.getSource()).isSameAs(src);
        assertThat(e.worldId()).isEqualTo("w1");
        assertThat(e.kind()).isEqualTo(ArkVoyageEvent.Kind.DEPARTED);
        assertThat(e.arkId()).isEqualTo("ark-7");
        assertThat(e.fromSlot()).isEqualTo(3);
        assertThat(e.toSlot()).isEqualTo(9);
        assertThat(e.departAt()).isEqualTo(1_000L);
        assertThat(e.arriveAt()).isEqualTo(61_000L);
        assertThat(ArkVoyageEvent.Kind.valueOf("ARRIVED")).isEqualTo(ArkVoyageEvent.Kind.ARRIVED);
        assertThat(ArkVoyageEvent.Kind.values()).hasSize(2);
    }

    @Test
    void islandLifeEventCopiesAndFreezesItsCollections() {
        List<String> keys = new ArrayList<>(List.of("oak", "fox"));
        Map<Integer, Integer> richness = new HashMap<>(Map.of(5, 2, 1, 7));
        IslandLifeEvent e = new IslandLifeEvent(this, "w2", IslandLifeEvent.Kind.LANDED, 42L, 4, "ark-1", keys, richness);
        keys.add("wolf");
        richness.put(9, 9);
        assertThat(e.worldId()).isEqualTo("w2");
        assertThat(e.kind()).isEqualTo(IslandLifeEvent.Kind.LANDED);
        assertThat(e.day()).isEqualTo(42L);
        assertThat(e.slot()).isEqualTo(4);
        assertThat(e.arkId()).isEqualTo("ark-1");
        assertThat(e.keys()).containsExactly("oak", "fox");
        assertThat(e.richness()).containsExactly(Map.entry(1, 7), Map.entry(5, 2));
        assertThatThrownBy(() -> e.keys().add("x")).isInstanceOf(UnsupportedOperationException.class);
        assertThatThrownBy(() -> e.richness().put(2, 2)).isInstanceOf(UnsupportedOperationException.class);
        assertThat(IslandLifeEvent.Kind.values()).containsExactly(
                IslandLifeEvent.Kind.DAY, IslandLifeEvent.Kind.LANDED, IslandLifeEvent.Kind.BOARDED);
    }

    @Test
    void islandLifeEventTreatsNullCollectionsAsEmpty() {
        IslandLifeEvent e = new IslandLifeEvent(this, "w3", IslandLifeEvent.Kind.DAY, 1L, 0, null, null, null);
        assertThat(e.keys()).isEmpty();
        assertThat(e.richness()).isEmpty();
        assertThat(e.arkId()).isNull();
    }
}