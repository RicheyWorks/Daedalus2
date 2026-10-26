// SPDX-License-Identifier: MIT
package com.daedalus.plugin;

import com.daedalus.plugin.events.ArkVoyageEvent;
import com.daedalus.plugin.events.IslandLifeEvent;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Contracts seen by plugins consuming harbour and ecology notifications. */
class IslandEventContractTest {
    @Test
    void departureAndArrivalKeepTheSameRouteAndServerSchedule() {
        Object harbour = new Object();
        long departure = 1_800_000_000_000L;
        long arrival = departure + 60_000;
        var events = List.of(
                new ArkVoyageEvent(harbour, "world-zero", ArkVoyageEvent.Kind.DEPARTED, "ark-7", 2, 9, departure, arrival),
                new ArkVoyageEvent(harbour, "world-zero", ArkVoyageEvent.Kind.ARRIVED, "ark-7", 2, 9, departure, arrival));
        assertThat(events).extracting(ArkVoyageEvent::kind)
                .containsExactly(ArkVoyageEvent.Kind.DEPARTED, ArkVoyageEvent.Kind.ARRIVED);
        for (var event : events) {
            assertThat(event.getSource()).isSameAs(harbour);
            assertThat(event.worldId()).isEqualTo("world-zero");
            assertThat(event.arkId()).isEqualTo("ark-7");
            assertThat(event.fromSlot()).isEqualTo(2);
            assertThat(event.toSlot()).isEqualTo(9);
            assertThat(event.departAt()).isEqualTo(departure);
            assertThat(event.arriveAt()).isEqualTo(arrival);
        }
    }

    @Test
    void ecologyNotificationsCannotBeChangedByTheProducerOrAnotherPlugin() {
        var keys = new ArrayList<>(List.of("fern", "moss"));
        var richness = new LinkedHashMap<Integer, Integer>();
        richness.put(9, 4);
        richness.put(2, 7);
        for (var kind : IslandLifeEvent.Kind.values()) {
            var event = new IslandLifeEvent(this, "world-zero", kind, 37, 9, "ark-7", keys, richness);
            assertThat(event.getSource()).isSameAs(this);
            assertThat(event.worldId()).isEqualTo("world-zero");
            assertThat(event.kind()).isEqualTo(kind);
            assertThat(event.day()).isEqualTo(37);
            assertThat(event.slot()).isEqualTo(9);
            assertThat(event.arkId()).isEqualTo("ark-7");
            keys.set(0, "changed");
            richness.put(9, 99);
            assertThat(event.keys()).containsExactly("fern", "moss");
            assertThat(event.richness()).containsExactly(Map.entry(2, 7), Map.entry(9, 4));
            assertThatThrownBy(() -> event.keys().clear()).isInstanceOf(UnsupportedOperationException.class);
            assertThatThrownBy(() -> event.richness().put(9, 99)).isInstanceOf(UnsupportedOperationException.class);
            keys.set(0, "fern");
            richness.put(9, 4);
        }
    }

    @Test
    void absentCollectionPayloadsAreSafeForPluginIteration() {
        var event = new IslandLifeEvent(this, "world-zero", IslandLifeEvent.Kind.DAY, 0, -1, null, null, null);
        assertThat(event.arkId()).isNull();
        assertThat(event.keys()).isEmpty();
        assertThat(event.richness()).isEmpty();
        assertThatThrownBy(() -> event.keys().add("fern")).isInstanceOf(UnsupportedOperationException.class);
        assertThatThrownBy(() -> event.richness().put(1, 1)).isInstanceOf(UnsupportedOperationException.class);
    }
}
