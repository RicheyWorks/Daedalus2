// SPDX-License-Identifier: MIT

package com.daedalus.desktop.ui;

import com.daedalus.api.dto.WorldEventFrame;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.Parcel;
import com.daedalus.world.ParcelBounds;
import com.daedalus.world.World;
import org.junit.jupiter.api.Test;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;

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
        World named = World.zero();
        named.applyStamp(new ParcelBounds(8, 0, 8, 9, 1, 9), Parcel.SYSTEM_OWNER,
                List.of(new BlockCoordinate(8, 0, 8)),
                List.of(BlockType.WOOD));
        named.nameParcel(named.parcels().get(0).id(), "Willow Walk");
        assertThat(DesktopWorld.firstPlace(named)).isEqualTo("Willow Walk");
        assertThat(DesktopWorld.inspectLine(named, null))
                .isEqualTo("world-zero r=" + named.revision().value() + " · Willow Walk · listening");
        assertThat(DesktopWorld.inspectLine(named.revision().value(), "Willow Walk", placed))
                .isEqualTo("world-zero r=" + named.revision().value()
                        + " · Willow Walk · BLOCK_PLACED 1,2,3 STONE");
        assertThat(DesktopWorld.ID).isEqualTo("world-zero");
        assertThat(DesktopWorld.PLACE_INK).isEqualTo("#94612e");
        assertThat(DesktopWorld.PLACE_CLASS).isEqualTo("world-place");
        assertThat(DesktopWorld.firstPlace(World.zero())).isEmpty();
        named.leaseParcel(named.parcels().get(0).id(), Parcel.SYSTEM_TENANT);
        assertThat(DesktopWorld.firstLease(named)).isEqualTo(Parcel.SYSTEM_TENANT);
        assertThat(DesktopWorld.inspectLine(named, null))
                .isEqualTo("world-zero r=" + named.revision().value()
                        + " · Willow Walk · " + Parcel.SYSTEM_TENANT + " · listening");
        assertThat(DesktopWorld.firstLease(World.zero())).isEmpty();
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
        try (InputStream cssIn = getClass().getResourceAsStream("/ui/cosmic.css")) {
            assertThat(cssIn).as("desktop cosmic shell").isNotNull();
            String css = new String(cssIn.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(css).contains(".status-bar .label.world-place")
                    .contains(DesktopWorld.PLACE_INK);
        }
    }
}
