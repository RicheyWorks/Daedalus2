// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.server.config.WalletProperties;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.beans.factory.support.StaticListableBeanFactory;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.file.Path;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

import static org.assertj.core.api.Assertions.assertThat;

/** Cached geometry must not freeze the request URLs exported to package consumers. */
class WorldPackageServiceManifestTest {

    @TempDir
    Path tmp;

    @Test
    void aGeometryCacheHitStillRefreshesTheManifestAndItsArchiveForTheCurrentRequest() throws IOException {
        WorldService zero = new WorldService(tmp.resolve("world-zero.daew"));
        StaticListableBeanFactory beans = new StaticListableBeanFactory();
        WorldPackageService packages = new WorldPackageService(
                WorldHub.of(zero), beans.getBeanProvider(WalletProperties.class));

        WorldPackageService.Built first = packages.build("world-zero", "https://first.invalid");
        WorldPackageService.Built second = packages.build("world-zero", "https://second.invalid");

        assertThat(packages.meshes()).isEqualTo(1);
        assertThat(second.revision()).isEqualTo(first.revision());
        assertThat(second.glb()).isEqualTo(first.glb());
        assertThat(first.manifest().live().api()).isEqualTo("https://first.invalid/api/v1/world/world-zero");
        assertThat(second.manifest().live().api()).isEqualTo("https://second.invalid/api/v1/world/world-zero");
        assertThat(archivedManifest(first.zip()).path("live").path("api").asText())
                .isEqualTo("https://first.invalid/api/v1/world/world-zero");
        assertThat(archivedManifest(second.zip()).path("live").path("api").asText())
                .isEqualTo("https://second.invalid/api/v1/world/world-zero");
    }

    private static JsonNode archivedManifest(byte[] archive) throws IOException {
        try (ZipInputStream zip = new ZipInputStream(new ByteArrayInputStream(archive))) {
            for (ZipEntry entry = zip.getNextEntry(); entry != null; entry = zip.getNextEntry()) {
                if (entry.getName().equals("manifest.json")) {
                    return new ObjectMapper().readTree(zip.readAllBytes());
                }
            }
        }
        throw new AssertionError("Package is missing manifest.json");
    }
}
