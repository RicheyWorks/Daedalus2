// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.TrapResult;
import com.daedalus.world.TrapState;
import com.daedalus.world.WorldId;
import com.daedalus.world.auto.WorldOps;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.lang.reflect.Constructor;
import java.nio.file.Path;
import java.util.Arrays;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Place, remove, drop the live service, open a new one on the same file.
 * Proves the maze cache is not on this path.
 */
class WorldServiceTest {

    @TempDir
    Path tmp;

    @Test
    void constructorDoesNotTakeTheMazeCache() {
        for (Constructor<?> ctor : WorldService.class.getDeclaredConstructors()) {
            assertThat(Arrays.asList(ctor.getParameterTypes()))
                    .doesNotContain(MazeGenerationService.class);
        }
    }

    @Test
    void placeRemoveSaveReloadIsIdentical() {
        Path file = tmp.resolve("world-zero.daew");
        WorldService live = new WorldService(file);
        assertThat(live.inspect("world-zero").id()).isEqualTo(WorldId.ZERO);
        assertThat(live.inspect("missing")).isNull();
        live.place("world-zero", 3, -2, 8, BlockType.GLASS);
        live.place("world-zero", 16, 0, 0, BlockType.WOOD);
        live.remove("world-zero", 16, 0, 0);
        long revision = live.inspect("world-zero").revision().value();
        int chunks = live.inspect("world-zero").chunkCount();

        WorldService restarted = new WorldService(file);
        assertThat(restarted.file()).isEqualTo(file);
        assertThat(restarted.inspectBlock("world-zero", 3, -2, 8)).isEqualTo(BlockType.GLASS);
        assertThat(restarted.inspectBlock("world-zero", 16, 0, 0)).isEqualTo(BlockType.AIR);
        assertThat(restarted.inspect("world-zero").revision().value()).isEqualTo(revision);
        assertThat(restarted.inspect("world-zero").chunkCount()).isEqualTo(chunks);
        assertThat(restarted.inspectChunk("world-zero", 0, -1, 0)).isNotNull();
        assertThat(live.observe("world-zero", 3, -2, 8).blockType()).isEqualTo("GLASS");
        assertThat(live.trace("world-zero")).extracting(s -> s.capability())
                .contains("block.place", "block.remove");
        assertThat(live.observe("missing", 0, 0, 0)).isNull();
        assertThat(live.trace("missing")).isNull();
    }

    @Test
    void aDeniedDriveSurvivesRestart() {
        Path file = tmp.resolve("world-zero.daew");
        WorldService live = new WorldService(file);
        live.stamp("world-zero", new BlockCoordinate(0, 0, 0));
        assertThat(live.armTrap("world-zero", "carol")).isEqualTo(TrapResult.DENIED);
        assertThat(WorldOps.driveLine(live.inspect("world-zero"))).isEqualTo("trap.arm DENIED");
        WorldService restarted = new WorldService(file);
        assertThat(WorldOps.driveLine(restarted.inspect("world-zero"))).isEqualTo("trap.arm DENIED");
        assertThat(restarted.inspect("world-zero").trap().state()).isEqualTo(TrapState.DISARMED);
    }
}
