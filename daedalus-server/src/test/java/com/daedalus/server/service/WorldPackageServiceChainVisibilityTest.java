// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.server.config.WalletProperties;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import org.springframework.beans.factory.support.StaticListableBeanFactory;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.file.Path;
import java.util.stream.Stream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

import static org.assertj.core.api.Assertions.assertThat;

/** Optional deployment metadata stays absent when its feature or configuration is unavailable. */
class WorldPackageServiceChainVisibilityTest {

    @TempDir
    Path tmp;

    @ParameterizedTest(name = "{0}")
    @MethodSource("unavailableConfigurations")
    void unavailableConfigurationDoesNotAdvertiseAChainInEitherManifest(
            String scenario, boolean enabled, String contract) throws IOException {
        WalletProperties wallet = new WalletProperties(
                enabled, "realm.invalid", "https://realm.invalid", 31_337L, contract, "", 30);
        StaticListableBeanFactory beans = new StaticListableBeanFactory();
        beans.addBean("wallet", wallet);
        WorldService zero = new WorldService(tmp.resolve("world-zero.daew"));
        WorldPackageService packages = new WorldPackageService(
                WorldHub.of(zero), beans.getBeanProvider(WalletProperties.class));

        WorldPackageService.Built built = packages.build("world-zero", "https://realm.invalid");

        assertThat(built.manifest().chain()).as(scenario).isNull();
        assertThat(archivedManifest(built.zip()).has("chain")).as(scenario).isFalse();
    }

    private static Stream<Arguments> unavailableConfigurations() {
        return Stream.of(
                Arguments.of("disabled feature with configured contract", false, "0x" + "1".repeat(40)),
                Arguments.of("enabled feature without a configured contract", true, " \t "));
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
