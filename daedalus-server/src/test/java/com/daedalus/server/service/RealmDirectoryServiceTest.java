// SPDX-License-Identifier: MIT
package com.daedalus.server.service;

import com.daedalus.world.WorldStyle;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.beans.factory.support.StaticListableBeanFactory;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

class RealmDirectoryServiceTest {
    @TempDir Path tmp;

    @Test void existingWorldsRetainTheirProviderAndImmutableOrderWithoutOcean() {
        WorldHub hub = mock(WorldHub.class);
        when(hub.worlds()).thenReturn(List.of(
                new WorldHub.WorldEntry("world-zero", WorldStyle.SKY_ISLANDS, 1, "World Zero"),
                new WorldHub.WorldEntry("gallery", WorldStyle.GALLERY, 2, "Gallery City")));
        var directory = new RealmDirectoryService(hub,
                new StaticListableBeanFactory().getBeanProvider(OceanHostService.class)).directory();
        assertThat(directory.schemaVersion()).isEqualTo(1);
        assertThat(directory.chunkSize()).isEqualTo(16);
        assertThat(directory.realms()).extracting(RealmDirectoryService.Realm::id).containsExactly("world-zero", "gallery");
        assertThat(directory.realms().get(1).chunkPathTemplate()).isEqualTo("/api/v1/world/gallery/chunk/blocks?x={x}&y={y}&z={z}");
        assertThat(directory.realms().get(1).blockEditsSupported()).isTrue();
        assertThatThrownBy(() -> directory.realms().clear()).isInstanceOf(UnsupportedOperationException.class);
        verify(hub).worlds();verifyNoMoreInteractions(hub);
    }

    @Test void enabledOceanUsesItsExistingProviderWithoutGeneratingChunksOrMountingWorlds() throws Exception {
        WorldHub hub = mock(WorldHub.class);when(hub.worlds()).thenReturn(List.of());
        try (var ocean = new OceanHostService(tmp, 42, 8, new OceanHostService.Bounds(-2, 1, -3, 0, -2, 1))) {
            var factory = new StaticListableBeanFactory();factory.addBean("ocean", ocean);
            var directory = new RealmDirectoryService(hub, factory.getBeanProvider(OceanHostService.class)).directory();
            assertThat(directory.realms()).hasSize(1);
            var entry = directory.realms().getFirst();
            assertThat(entry.protocol()).isEqualTo(RealmDirectoryService.Protocol.OCEAN_V1);
            assertThat(entry.manifestPath()).isEqualTo("/api/v1/ocean/v1");
            assertThat(entry.chunkPathTemplate()).isEqualTo("/api/v1/ocean/v1/chunk?x={x}&y={y}&z={z}");
            assertThat(entry.blockEditsSupported()).isFalse();
            try (var files = Files.list(tmp)) { assertThat(files.noneMatch(path -> path.toString().endsWith(".daew"))).isTrue(); }
            verify(hub).worlds();verifyNoMoreInteractions(hub);
        }
    }

    @Test void conflictingProviderIdentityRefusesRatherThanShadowingAnExistingWorld() throws Exception {
        WorldHub hub = mock(WorldHub.class);
        when(hub.worlds()).thenReturn(List.of(new WorldHub.WorldEntry("ocean", WorldStyle.SKY_ISLANDS, 1, "Existing Ocean")));
        try (var ocean = new OceanHostService(tmp, 42, 8, new OceanHostService.Bounds(-2, 1, -3, 0, -2, 1))) {
            var factory = new StaticListableBeanFactory();factory.addBean("ocean", ocean);
            var directory = new RealmDirectoryService(hub, factory.getBeanProvider(OceanHostService.class));
            assertThatThrownBy(directory::directory).isInstanceOf(IllegalStateException.class).hasMessage("Duplicate realm id");
        }
    }
}
