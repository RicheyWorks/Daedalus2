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
        assertThat(WorldOps.atLine(live)).isEqualTo("1,1,0");
        Path file = tmp.resolve("drive.daew");
        WorldStore.save(live, file);
        World reloaded = WorldStore.load(file);
        assertThat(WorldOps.driveLine(reloaded)).isEqualTo("trap.arm DENIED");
        assertThat(WorldOps.actorLine(reloaded)).isEqualTo("carol");
        assertThat(WorldOps.atLine(reloaded)).isEqualTo("1,1,0");
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

    /** A world with real terrain: a 40x40 slab, a hill, and a few glass and wood cubes. */
    private static World terrain() {
        World w = World.zero();
        for (int x = -20; x < 20; x++) {
            for (int z = -20; z < 20; z++) {
                int h = 3 + Math.max(0, 6 - (Math.abs(x) + Math.abs(z)) / 3);
                for (int y = 0; y < h; y++) {
                    w.place(new BlockCoordinate(x, y, z), y == h - 1 ? BlockType.GRASS : y < 2 ? BlockType.STONE : BlockType.DIRT);
                }
            }
        }
        w.place(new BlockCoordinate(5, 12, 5), BlockType.GLASS);
        w.place(new BlockCoordinate(-7, 9, 3), BlockType.WOOD);
        return w;
    }

    /** The same snapshot in the version-13 layout: dense 4,096-byte chunks. Everything after the chunks is unchanged. */
    private static byte[] asVersion13(byte[] v14) throws IOException {
        java.io.DataInputStream in = new java.io.DataInputStream(new java.io.ByteArrayInputStream(v14));
        java.io.ByteArrayOutputStream bytes = new java.io.ByteArrayOutputStream();
        java.io.DataOutputStream out = new java.io.DataOutputStream(bytes);
        out.write(in.readNBytes(4));
        assertThat(in.readUnsignedByte()).isEqualTo(14);
        out.writeByte(13);
        out.writeUTF(in.readUTF());
        out.writeLong(in.readLong());
        int count = in.readInt();
        out.writeInt(count);
        for (int i = 0; i < count; i++) {
            out.writeInt(in.readInt());
            out.writeInt(in.readInt());
            out.writeInt(in.readInt());
            out.writeLong(in.readLong());
            int runs = in.readUnsignedShort();
            out.write(Chunk.ofRuns(in.readNBytes(runs * 3)));
        }
        out.write(in.readAllBytes());
        return bytes.toByteArray();
    }

    @Test
    void chunksAreStoredAsRunsAndTheFileShrinks() throws Exception {
        World live = terrain();
        Path file = tmp.resolve("terrain.daew");
        WorldStore.save(live, file);
        byte[] v14 = Files.readAllBytes(file);
        byte[] v13 = asVersion13(v14);
        assertThat(v14.length * 5L).as("runs vs dense: %d vs %d bytes", v14.length, v13.length).isLessThan(v13.length);
        World reloaded = WorldStore.load(file);
        assertThat(reloaded.chunkCount()).isEqualTo(live.chunkCount());
        for (ChunkCoordinate cc : live.chunkKeys()) {
            assertThat(reloaded.chunk(cc).ordinals()).isEqualTo(live.chunk(cc).ordinals());
            assertThat(reloaded.chunk(cc).revision()).isEqualTo(live.chunk(cc).revision());
        }
    }

    @Test
    void aVersion13FileStillLoadsAndSavesForwardIdentically() throws Exception {
        World live = terrain();
        Path file = tmp.resolve("new.daew");
        WorldStore.save(live, file);
        Path old = tmp.resolve("old.daew");
        Files.write(old, asVersion13(Files.readAllBytes(file)));
        World fromOld = WorldStore.load(old);
        Path again = tmp.resolve("again.daew");
        WorldStore.save(fromOld, again);
        assertThat(Files.readAllBytes(again)).isEqualTo(Files.readAllBytes(file));
    }

    @Test
    void brokenRunsAreRefusedNotHalfLoaded() throws Exception {
        World live = World.zero();
        live.place(new BlockCoordinate(1, 1, 1), BlockType.STONE);
        Path file = tmp.resolve("one.daew");
        WorldStore.save(live, file);
        byte[] b = Files.readAllBytes(file);
        // header: magic 4 + version 1 + UTF (2 + 10 "world-zero") + revision 8 + count 4; chunk: xyz 12 + rev 8, then runs
        int runCountAt = 4 + 1 + 2 + "world-zero".length() + 8 + 4 + 12 + 8;
        int runs = ((b[runCountAt] & 0xff) << 8) | (b[runCountAt + 1] & 0xff);
        assertThat(runs).isEqualTo(3);
        b[runCountAt + 2 + 1] = 0;   // first run's length low byte -> the runs no longer cover 4,096 cubes
        Files.write(file, b);
        assertThatThrownBy(() -> WorldStore.load(file)).isInstanceOf(IOException.class).hasMessageContaining("Bad chunk runs");
    }
}
