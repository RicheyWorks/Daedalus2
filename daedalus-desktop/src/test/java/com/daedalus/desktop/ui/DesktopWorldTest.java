// SPDX-License-Identifier: MIT

package com.daedalus.desktop.ui;

import com.daedalus.api.dto.WorldEventFrame;
import com.daedalus.world.World;
import org.junit.jupiter.api.Test;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;

import static org.assertj.core.api.Assertions.assertThat;

class DesktopWorldTest {

    @Test
    void inspectLineNamesRevisionAndLastEvent() {
        assertThat(DesktopWorld.inspectLine(null, null)).isEqualTo("world-zero · unavailable");
        assertThat(DesktopWorld.inspectLine(World.zero(), null))
                .isEqualTo("world-zero r=0 · listening");
        WorldEventFrame placed = new WorldEventFrame(
                DesktopWorld.ID, "BLOCK_PLACED", 1, 2, 3, "STONE", "AIR", 4);
        assertThat(DesktopWorld.inspectLine(4, placed))
                .isEqualTo("world-zero r=4 · BLOCK_PLACED 1,2,3 STONE");
        assertThat(DesktopWorld.ID).isEqualTo("world-zero");
    }

    @Test
    void statusBarCarriesAWorldLineBesideMazeStatus() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/ui/main.fxml")) {
            assertThat(in).as("desktop shell").isNotNull();
            String fxml = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(fxml).contains("fx:id=\"worldLabel\"")
                    .contains("fx:id=\"statusLabel\"")
                    .contains("fx:id=\"generateButton\"")
                    .contains("fx:id=\"solveButton\"");
        }
    }
}
