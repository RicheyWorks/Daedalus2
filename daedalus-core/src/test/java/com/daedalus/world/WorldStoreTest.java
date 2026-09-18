// SPDX-License-Identifier: MIT

package com.daedalus.world;

import com.daedalus.engine.MazeGrid;
import com.daedalus.world.auto.WorldOps;
import com.daedalus.world.stamp.StampOps;
import com.daedalus.world.stamp.StampRequest;
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
    void anOpenedPortalSurvivesRestart() throws Exception {
        World live = World.zero();
        live.openPortal();
        Path file = tmp.resolve("portal.daew");
        WorldStore.save(live, file);
        World reloaded = WorldStore.load(file);
        assertThat(reloaded.portal().state()).isEqualTo(PortalState.OPEN);
        assertThat(reloaded.portal().id()).isEqualTo(Portal.ZERO_ID);
    }

    @Test
    void aSpeakingNpcSurvivesRestart() throws Exception {
        World live = World.zero();
        live.talkNpc();
        Path file = tmp.resolve("npc.daew");
        WorldStore.save(live, file);
        World reloaded = WorldStore.load(file);
        assertThat(reloaded.npc().state()).isEqualTo(NpcState.SPEAKING);
        assertThat(reloaded.npc().id()).isEqualTo(Npc.ZERO_ID);
    }

    @Test
    void extraGrantsAndDenialsSurviveRestart() throws Exception {
        World live = World.zero();
        StampOps.apply(live, new StampRequest(live.id(),
                new BlockCoordinate(0, 0, 0), new MazeGrid(1, 1), 0, 1));
        ParcelId id = live.parcels().get(0).id();
        live.grant(id, "bob", ParcelVerb.BLOCK_PLACE);
        live.deny(id, "alice", ParcelVerb.BLOCK_PLACE);
        Path file = tmp.resolve("acl.daew");
        WorldStore.save(live, file);
        World reloaded = WorldStore.load(file);
        assertThat(reloaded.acl(id).grants("bob", ParcelVerb.BLOCK_PLACE)).isTrue();
        assertThat(reloaded.acl(id).denies("alice", ParcelVerb.BLOCK_PLACE)).isTrue();
        assertThat(reloaded.acl(id).grants("alice", ParcelVerb.BLOCK_PLACE)).isFalse();
        Path again = tmp.resolve("acl-again.daew");
        WorldStore.save(reloaded, again);
        assertThat(Files.readAllBytes(again)).isEqualTo(Files.readAllBytes(file));
    }

    @Test
    void lastDriveSurvivesRestart() throws Exception {
        World live = World.zero();
        StampOps.apply(live, new StampRequest(live.id(),
                new BlockCoordinate(0, 0, 0), new MazeGrid(1, 1), 0, 1));
        assertThat(WorldOps.drive(live, "trap.arm", Trap.ZERO_AT, null, null, "carol"))
                .isEqualTo(TrapResult.DENIED);
        assertThat(WorldOps.driveLine(live)).isEqualTo("trap.arm DENIED");
        assertThat(WorldOps.actorLine(live)).isEqualTo("carol");
        Path file = tmp.resolve("drive.daew");
        WorldStore.save(live, file);
        World reloaded = WorldStore.load(file);
        assertThat(WorldOps.driveLine(reloaded)).isEqualTo("trap.arm DENIED");
        assertThat(WorldOps.actorLine(reloaded)).isEqualTo("carol");
        Path again = tmp.resolve("drive-again.daew");
        WorldStore.save(reloaded, again);
        assertThat(Files.readAllBytes(again)).isEqualTo(Files.readAllBytes(file));
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
