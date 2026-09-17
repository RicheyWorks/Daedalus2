// SPDX-License-Identifier: MIT

package com.daedalus.world;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Place, remove, save, drop the live object, reload — identical state.
 * This is not the maze Caffeine cache.
 */
class WorldStoreTest {

    @TempDir
    Path tmp;

    @Test
    void saveStopStartWorldIsIdentical() throws Exception {
        World live = World.zero();
        live.place(new BlockCoordinate(0, 0, 0), BlockType.STONE);
        live.place(new BlockCoordinate(-1, 4, 19), BlockType.GLASS);
        live.place(new BlockCoordinate(16, 0, 0), BlockType.WOOD);
        live.remove(new BlockCoordinate(16, 0, 0));
        live.place(new BlockCoordinate(2, 2, 2), BlockType.DIRT);
        WorldRevision revision = live.revision();
        int chunks = live.chunkCount();

        Path file = tmp.resolve("world-zero.daew");
        WorldStore.save(live, file);

        // Process restart: the live object is gone. Only the file remains.
        World reloaded = WorldStore.load(file);

        assertThat(reloaded.id()).isEqualTo(WorldId.ZERO);
        assertThat(reloaded.revision()).isEqualTo(revision);
        assertThat(reloaded.chunkCount()).isEqualTo(chunks);
        assertThat(reloaded.get(new BlockCoordinate(0, 0, 0))).isEqualTo(BlockType.STONE);
        assertThat(reloaded.get(new BlockCoordinate(-1, 4, 19))).isEqualTo(BlockType.GLASS);
        assertThat(reloaded.get(new BlockCoordinate(16, 0, 0))).isEqualTo(BlockType.AIR);
        assertThat(reloaded.get(new BlockCoordinate(2, 2, 2))).isEqualTo(BlockType.DIRT);
        assertThat(reloaded.contains(new BlockCoordinate(16, 0, 0))).isFalse();
        assertThat(reloaded.door().state()).isEqualTo(DoorState.CLOSED);

        Path again = tmp.resolve("world-zero-again.daew");
        WorldStore.save(reloaded, again);
        assertThat(Files.readAllBytes(again)).isEqualTo(Files.readAllBytes(file));
    }

    @Test
    void anOpenedDoorSurvivesRestart() throws Exception {
        World live = World.zero();
        live.openDoor();
        Path file = tmp.resolve("door.daew");
        WorldStore.save(live, file);
        World reloaded = WorldStore.load(file);
        assertThat(reloaded.door().state()).isEqualTo(DoorState.OPEN);
        assertThat(reloaded.door().id()).isEqualTo(Door.ZERO_ID);
    }

    @Test
    void anArmedTrapSurvivesRestart() throws Exception {
        World live = World.zero();
        live.armTrap();
        Path file = tmp.resolve("trap.daew");
        WorldStore.save(live, file);
        World reloaded = WorldStore.load(file);
        assertThat(reloaded.trap().state()).isEqualTo(TrapState.ARMED);
        assertThat(reloaded.trap().id()).isEqualTo(Trap.ZERO_ID);
    }

    @Test
    void snapshotDoesNotShareStorageWithTheLiveWorld() {
        World live = World.zero();
        live.place(new BlockCoordinate(0, 0, 0), BlockType.STONE);
        WorldSnapshot snap = live.snapshot();
        live.place(new BlockCoordinate(0, 0, 0), BlockType.DIRT);
        World restored = World.from(snap);
        assertThat(restored.get(new BlockCoordinate(0, 0, 0))).isEqualTo(BlockType.STONE);
        assertThat(live.get(new BlockCoordinate(0, 0, 0))).isEqualTo(BlockType.DIRT);
        restored.place(new BlockCoordinate(1, 0, 0), BlockType.WOOD);
        assertThat(live.get(new BlockCoordinate(1, 0, 0))).isEqualTo(BlockType.AIR);
    }

    @Test
    void snapshotIsInspectAndDoesNotBumpRevision() {
        World live = World.zero();
        live.place(new BlockCoordinate(0, 0, 0), BlockType.STONE);
        long before = live.revision().value();
        live.snapshot();
        assertThat(live.revision().value()).isEqualTo(before);
    }

    @Test
    void badMagicIsRefused() throws Exception {
        Path file = tmp.resolve("not-a-world.bin");
        Files.write(file, "XXXX".getBytes());
        assertThatThrownBy(() -> WorldStore.load(file))
                .isInstanceOf(IOException.class)
                .hasMessageContaining("Not a Daedalus world snapshot");
    }

    @Test
    void unknownChunkOrdinalIsRefused() {
        byte[] payload = new byte[Chunk.VOLUME];
        payload[0] = 99;
        assertThatThrownBy(() -> Chunk.ofPayload(payload, 0))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Unknown block ordinal");
    }

    @Test
    void nullStorePathIsRefused() {
        assertThatThrownBy(() -> WorldStore.save(World.zero(), null))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
