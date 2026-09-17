// SPDX-License-Identifier: MIT

package com.daedalus.world;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Pins {@code floorDiv} / {@code floorMod} chunk membership. Signed {@code %} would
 * put {@code (-1,0,0)} in chunk {@code (0,0,0)} at local {@code -1}.
 */
class WorldCoordinatesTest {

    @ParameterizedTest
    @CsvSource({
            "0,0,0, 0,0,0, 0,0,0",
            "15,15,15, 0,0,0, 15,15,15",
            "16,0,0, 1,0,0, 0,0,0",
            "0,16,0, 0,1,0, 0,0,0",
            "0,0,16, 0,0,1, 0,0,0",
            "-1,0,0, -1,0,0, 15,0,0",
            "-16,0,0, -1,0,0, 0,0,0",
            "-17,0,0, -2,0,0, 15,0,0",
            "0,-1,0, 0,-1,0, 0,15,0",
            "0,0,-1, 0,0,-1, 0,0,15",
            "16,-1,32, 1,-1,2, 0,15,0"
    })
    void chunkOfAndLocalOfOnPositiveNegativeAndAxisCrossing(
            int x, int y, int z,
            int cx, int cy, int cz,
            int lx, int ly, int lz) {
        BlockCoordinate block = new BlockCoordinate(x, y, z);
        assertThat(block.chunk()).isEqualTo(new ChunkCoordinate(cx, cy, cz));
        assertThat(ChunkCoordinate.of(block)).isEqualTo(block.chunk());
        assertThat(block.localX()).isEqualTo(lx);
        assertThat(block.localY()).isEqualTo(ly);
        assertThat(block.localZ()).isEqualTo(lz);
    }

    @Test
    void worldZeroIdIsTheWellKnownName() {
        assertThat(WorldId.ZERO.value()).isEqualTo("world-zero");
        assertThat(World.zero().id()).isEqualTo(WorldId.ZERO);
    }

    @Test
    void blankWorldIdIsRefused() {
        assertThatThrownBy(() -> new WorldId(" "))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new WorldId(null))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void revisionStartsAtZeroAndRefusesNegatives() {
        assertThat(WorldRevision.ZERO.value()).isZero();
        assertThat(WorldRevision.ZERO.next().value()).isEqualTo(1);
        assertThatThrownBy(() -> new WorldRevision(-1))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void fiveBlockTypesAndAirIsNotSolid() {
        assertThat(BlockType.values()).containsExactly(
                BlockType.AIR, BlockType.STONE, BlockType.DIRT, BlockType.WOOD, BlockType.GLASS);
        assertThat(BlockType.AIR.solid()).isFalse();
        assertThat(BlockType.STONE.solid()).isTrue();
    }
}
