// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.IslandEcologyComparisonResponse;
import com.daedalus.server.service.WorldHub;
import com.daedalus.server.service.WorldService;
import com.daedalus.server.web.ResourceNotFoundException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.verifyNoMoreInteractions;
import static org.mockito.Mockito.when;

/** Snapshot routing only: no world files, server, or advancing real simulation clock. */
class EcologyComparisonControllerTest {

    private WorldHub hub;
    private WorldService first;
    private WorldService second;
    private EcologyComparisonController controller;

    @BeforeEach
    void setUp() {
        hub = mock(WorldHub.class);
        first = mock(WorldService.class);
        second = mock(WorldService.class);
        when(hub.get("world-zero")).thenReturn(first);
        when(hub.get("parcels")).thenReturn(second);
        controller = new EcologyComparisonController(hub);
    }

    @Test
    void comparingAnIslandWithItselfCapturesExactlyOneSnapshot() {
        when(first.ecology("world-zero", 2)).thenReturn(
                snapshot(2, 17, Map.of("fern", 0.25)),
                snapshot(2, 18, Map.of("pine", 2.0)));

        IslandEcologyComparisonResponse result = controller.compare("world-zero", 2, "world-zero", 2);

        assertThat(result.worldId()).isEqualTo("world-zero");
        assertThat(result.otherWorldId()).isEqualTo("world-zero");
        assertThat(result.slot()).isEqualTo(2);
        assertThat(result.otherSlot()).isEqualTo(2);
        assertThat(result.day()).isEqualTo(17);
        assertThat(result.otherDay()).isEqualTo(17);
        assertThat(result.comparison().jaccard()).isEqualTo(1);
        assertThat(result.comparison().brayCurtis()).isZero();
        verify(first, times(1)).ecology("world-zero", 2);
        verifyNoMoreInteractions(first);
        verifyNoInteractions(second);
        verify(hub, never()).resolve(anyString());
    }

    @Test
    void distinctWorldsKeepTheirOwnSlotsDaysAndCommunities() {
        when(first.ecology("world-zero", 3)).thenReturn(snapshot(3, 5, Map.of("fern", 1.0)));
        when(second.ecology("parcels", 7)).thenReturn(snapshot(7, 11, Map.of("fern", 2.0, "moss", 1.0)));

        IslandEcologyComparisonResponse result = controller.compare("world-zero", 3, "parcels", 7);

        assertThat(result.worldId()).isEqualTo("world-zero");
        assertThat(result.otherWorldId()).isEqualTo("parcels");
        assertThat(result.slot()).isEqualTo(3);
        assertThat(result.otherSlot()).isEqualTo(7);
        assertThat(result.day()).isEqualTo(5);
        assertThat(result.otherDay()).isEqualTo(11);
        assertThat(result.comparison().firstRichness()).isEqualTo(1);
        assertThat(result.comparison().secondRichness()).isEqualTo(2);
        assertThat(result.comparison().shared()).containsExactly("fern");
        assertThat(result.comparison().onlySecond()).containsExactly("moss");
        verify(first).ecology("world-zero", 3);
        verify(second).ecology("parcels", 7);
        verifyNoMoreInteractions(first, second);
        verify(hub, never()).resolve(anyString());
    }

    @Test
    void distinctSlotsInOneWorldAreCapturedSeparately() {
        when(first.ecology("world-zero", 2)).thenReturn(snapshot(2, 7, Map.of("fern", 1.0)));
        when(first.ecology("world-zero", 8)).thenReturn(snapshot(8, 8, Map.of("pine", 1.0)));

        IslandEcologyComparisonResponse result = controller.compare("world-zero", 2, "world-zero", 8);

        assertThat(result.day()).isEqualTo(7);
        assertThat(result.otherDay()).isEqualTo(8);
        assertThat(result.comparison().brayCurtis()).isEqualTo(1);
        verify(first).ecology("world-zero", 2);
        verify(first).ecology("world-zero", 8);
        verifyNoMoreInteractions(first);
        verifyNoInteractions(second);
    }

    @Test
    void unknownFirstWorldIsRefusedWithoutWorldZeroFallback() {
        ResourceNotFoundException failure = assertThrows(ResourceNotFoundException.class,
                () -> controller.compare("missing", 2, "parcels", 7));

        assertThat(failure.kind()).isEqualTo("world");
        assertThat(failure.requested()).isEqualTo("missing");
        verifyNoInteractions(first, second);
        verify(hub, never()).resolve(anyString());
    }

    @Test
    void unknownOtherWorldIsRefusedBeforeCapturingEitherCommunity() {
        ResourceNotFoundException failure = assertThrows(ResourceNotFoundException.class,
                () -> controller.compare("world-zero", 2, "missing", 7));

        assertThat(failure.kind()).isEqualTo("world");
        assertThat(failure.requested()).isEqualTo("missing");
        verifyNoInteractions(first, second);
        verify(hub, never()).resolve(anyString());
    }

    @Test
    void unknownFirstSlotIsRefusedWithoutReadingTheOtherIsland() {
        ResourceNotFoundException failure = assertThrows(ResourceNotFoundException.class,
                () -> controller.compare("world-zero", 99, "parcels", 7));

        assertThat(failure.kind()).isEqualTo("island");
        assertThat(failure.requested()).isEqualTo("99");
        verify(first).ecology("world-zero", 99);
        verifyNoMoreInteractions(first);
        verifyNoInteractions(second);
    }

    @Test
    void unknownOtherSlotReportsThatSlotWithoutSubstitutingTheFirst() {
        when(first.ecology("world-zero", 2)).thenReturn(snapshot(2, 17, Map.of("fern", 1.0)));

        ResourceNotFoundException failure = assertThrows(ResourceNotFoundException.class,
                () -> controller.compare("world-zero", 2, "parcels", 99));

        assertThat(failure.kind()).isEqualTo("island");
        assertThat(failure.requested()).isEqualTo("99");
        verify(first).ecology("world-zero", 2);
        verify(second).ecology("parcels", 99);
        verifyNoMoreInteractions(first, second);
    }

    private static WorldService.IslandEcology snapshot(int slot, long day, Map<String, Double> abundance) {
        // Habitat/diversity are not read by this controller; the real snapshot copies its abundance.
        return new WorldService.IslandEcology(slot, day, null, null, abundance);
    }
}
