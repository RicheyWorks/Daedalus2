// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.api.dto.WorldManifest;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** Binary payload ownership at the package boundary, without generating or meshing a world. */
class WorldPackageServiceBuiltTest {

    @Test
    void callerBufferReuseCannotChangeAnAlreadyBuiltPackage() {
        byte[] geometry = {1, 2, 3};
        byte[] archive = {4, 5, 6};
        WorldPackageService.Built built = new WorldPackageService.Built(7, manifest(), geometry, archive);

        Arrays.fill(geometry, (byte) 0);
        Arrays.fill(archive, (byte) 0);

        assertThat(built.glb()).isEqualTo(new byte[]{1, 2, 3});
        assertThat(built.zip()).isEqualTo(new byte[]{4, 5, 6});
    }

    @Test
    void archiveConsumersCannotChangeEachOthersBytesOrTheBuiltPackage() {
        WorldPackageService.Built built = new WorldPackageService.Built(
                7, manifest(), new byte[]{1, 2, 3}, new byte[]{4, 5, 6});
        byte[] firstDownload = built.zip();
        byte[] secondDownload = built.zip();

        firstDownload[0] = 0;
        assertThat(secondDownload).isEqualTo(new byte[]{4, 5, 6});

        secondDownload[1] = 0;
        assertThat(built.zip()).isEqualTo(new byte[]{4, 5, 6});
    }

    private static WorldManifest manifest() {
        return new WorldManifest(WorldPackageService.FORMAT, WorldPackageService.VERSION, "test",
                new WorldManifest.World("test-world", "SKY_ISLANDS", "Test world", 0, 7),
                "1 cube = 1 metre", "+Y up",
                new WorldManifest.Geometry("world.glb", 16, 0, 0, List.of()),
                List.of(), List.of(), List.of(), null, List.of(), List.of(), List.of(),
                new WorldManifest.Mount("ARK", false), List.of(),
                new WorldManifest.Live("/api/v1/world/test-world", "/topic/world/test-world"), null);
    }
}
