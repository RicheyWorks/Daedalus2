// SPDX-License-Identifier: MIT

package com.daedalus.world;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class WorldBlockStorageTest {

    private static final BlockCoordinate ORIGIN = new BlockCoordinate(0, 0, 0);
    private static final BlockCoordinate OTHER_CHUNK = new BlockCoordinate(16, 0, 0);
    private static final BlockCoordinate NEGATIVE = new BlockCoordinate(-1, 0, 0);

    @Test
    void aWrittenBlockIsReadableAtTheSameCoordinate() {
        World world = World.zero();
        assertThat(world.place(ORIGIN, BlockType.STONE)).isEqualTo(BlockType.AIR);
        assertThat(world.get(ORIGIN)).isEqualTo(BlockType.STONE);
        assertThat(world.contains(ORIGIN)).isTrue();
    }

    @Test
    void aBlockInAnotherChunkDoesNotLeak() {
        World world = World.zero();
        world.place(ORIGIN, BlockType.DIRT);
        world.place(OTHER_CHUNK, BlockType.WOOD);
        assertThat(world.get(ORIGIN)).isEqualTo(BlockType.DIRT);
        assertThat(world.get(OTHER_CHUNK)).isEqualTo(BlockType.WOOD);
        assertThat(world.get(new BlockCoordinate(15, 0, 0))).isEqualTo(BlockType.AIR);
        assertThat(world.chunkCount()).isEqualTo(2);
    }

    @Test
    void aMissingChunkReadsAsAir() {
        World world = World.zero();
        assertThat(world.get(ORIGIN)).isEqualTo(BlockType.AIR);
        assertThat(world.get(NEGATIVE)).isEqualTo(BlockType.AIR);
        assertThat(world.contains(ORIGIN)).isFalse();
        assertThat(world.chunk(new ChunkCoordinate(0, 0, 0))).isNull();
        assertThat(world.chunkCount()).isZero();
    }

    @Test
    void removeReturnsTheCellToAirAndDropsAnEmptyChunk() {
        World world = World.zero();
        world.place(NEGATIVE, BlockType.GLASS);
        assertThat(world.chunkCount()).isEqualTo(1);
        assertThat(world.remove(NEGATIVE)).isEqualTo(BlockType.GLASS);
        assertThat(world.get(NEGATIVE)).isEqualTo(BlockType.AIR);
        assertThat(world.contains(NEGATIVE)).isFalse();
        assertThat(world.chunkCount()).isZero();
    }

    @Test
    void mutationBumpsRevisionAndInspectDoesNot() {
        World world = World.zero();
        assertThat(world.revision()).isEqualTo(WorldRevision.ZERO);
        world.get(ORIGIN);
        world.contains(ORIGIN);
        world.chunkCount();
        assertThat(world.revision()).isEqualTo(WorldRevision.ZERO);

        world.place(ORIGIN, BlockType.STONE);
        assertThat(world.revision().value()).isEqualTo(1);
        world.get(ORIGIN);
        assertThat(world.revision().value()).isEqualTo(1);

        world.place(ORIGIN, BlockType.STONE);
        assertThat(world.revision().value()).isEqualTo(2);
        world.remove(ORIGIN);
        assertThat(world.revision().value()).isEqualTo(3);
        world.remove(ORIGIN);
        assertThat(world.revision().value()).isEqualTo(4);
    }

    @Test
    void twoWorldsDoNotShareChunkStorage() {
        World a = new World(new WorldId("alpha"));
        World b = new World(new WorldId("beta"));
        a.place(ORIGIN, BlockType.STONE);
        assertThat(b.get(ORIGIN)).isEqualTo(BlockType.AIR);
        assertThat(b.chunkCount()).isZero();
        assertThat(b.revision()).isEqualTo(WorldRevision.ZERO);
        b.place(ORIGIN, BlockType.DIRT);
        assertThat(a.get(ORIGIN)).isEqualTo(BlockType.STONE);
        assertThat(b.get(ORIGIN)).isEqualTo(BlockType.DIRT);
    }

    @Test
    void placingAirIsRemove() {
        World world = World.zero();
        world.place(ORIGIN, BlockType.WOOD);
        assertThat(world.place(ORIGIN, BlockType.AIR)).isEqualTo(BlockType.WOOD);
        assertThat(world.get(ORIGIN)).isEqualTo(BlockType.AIR);
        assertThat(world.chunkCount()).isZero();
    }

    @Test
    void returnedChunksAreCopies() {
        World world = World.zero();
        world.place(ORIGIN, BlockType.STONE);
        Chunk snapshot = world.chunk(ORIGIN.chunk());
        assertThat(snapshot).isNotNull();
        snapshot.set(0, 0, 0, BlockType.GLASS);
        assertThat(world.get(ORIGIN)).isEqualTo(BlockType.STONE);
    }

    @Test
    void localCoordinatesOutsideTheChunkAreRefused() {
        Chunk chunk = new Chunk();
        assertThatThrownBy(() -> chunk.get(16, 0, 0))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> chunk.set(-1, 0, 0, BlockType.STONE))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
