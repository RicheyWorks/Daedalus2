// SPDX-License-Identifier: MIT

package com.daedalus.world;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * File-backed world snapshot. No Jackson, no maze Caffeine, no Spring.
 * Bytes are deterministic: chunks are written in (x, y, z) order.
 */
public final class WorldStore {

    static final byte[] MAGIC = "DAEW".getBytes(StandardCharsets.US_ASCII);
    static final int VERSION = 10;
    static final int VERSION_CHUNKS_ONLY = 1;
    static final int VERSION_WITH_DOOR = 2;
    static final int VERSION_WITH_PARCELS = 3;
    static final int VERSION_WITH_TRAP = 4;
    static final int VERSION_WITH_PORTAL = 5;
    static final int VERSION_WITH_NPC = 6;
    static final int VERSION_WITH_PLACE_NAME = 7;
    static final int VERSION_WITH_LEASE = 8;
    static final int VERSION_WITH_MAZE_REF = 9;
    static final int VERSION_WITH_ACL = 10;

    private WorldStore() {
    }

    public static void save(World world, Path file) throws IOException {
        requirePath(file);
        save(world.snapshot(), file);
    }

    public static void save(WorldSnapshot snapshot, Path file) throws IOException {
        requirePath(file);
        Path parent = file.getParent();
        if (parent != null) {
            Files.createDirectories(parent);
        }
        try (OutputStream raw = Files.newOutputStream(file);
             DataOutputStream out = new DataOutputStream(raw)) {
            write(snapshot, out);
        }
    }

    public static World load(Path file) throws IOException {
        return World.from(loadSnapshot(file));
    }

    public static WorldSnapshot loadSnapshot(Path file) throws IOException {
        requirePath(file);
        try (InputStream raw = Files.newInputStream(file);
             DataInputStream in = new DataInputStream(raw)) {
            return read(in);
        }
    }

    static void write(WorldSnapshot snapshot, DataOutputStream out) throws IOException {
        out.write(MAGIC);
        out.writeByte(VERSION);
        out.writeUTF(snapshot.id().value());
        out.writeLong(snapshot.revision().value());
        List<Map.Entry<ChunkCoordinate, Chunk>> ordered = new ArrayList<>(snapshot.chunks().entrySet());
        ordered.sort(Comparator.comparingInt((Map.Entry<ChunkCoordinate, Chunk> e) -> e.getKey().x())
                .thenComparingInt(e -> e.getKey().y())
                .thenComparingInt(e -> e.getKey().z()));
        out.writeInt(ordered.size());
        for (Map.Entry<ChunkCoordinate, Chunk> e : ordered) {
            ChunkCoordinate c = e.getKey();
            Chunk chunk = e.getValue();
            out.writeInt(c.x());
            out.writeInt(c.y());
            out.writeInt(c.z());
            out.writeLong(chunk.revision());
            out.write(chunk.payload());
        }
        Door door = snapshot.door();
        out.writeBoolean(door != null);
        if (door != null) {
            out.writeUTF(door.id());
            out.writeInt(door.at().x());
            out.writeInt(door.at().y());
            out.writeInt(door.at().z());
            out.writeUTF(door.state().name());
        }
        List<Parcel> parcels = new ArrayList<>(snapshot.parcels());
        parcels.sort(Comparator.comparing(p -> p.id().value()));
        out.writeInt(parcels.size());
        for (Parcel parcel : parcels) {
            out.writeUTF(parcel.id().value());
            out.writeUTF(parcel.worldId().value());
            out.writeUTF(parcel.ownerId());
            ParcelBounds bounds = parcel.bounds();
            out.writeInt(bounds.minX());
            out.writeInt(bounds.minY());
            out.writeInt(bounds.minZ());
            out.writeInt(bounds.maxX());
            out.writeInt(bounds.maxY());
            out.writeInt(bounds.maxZ());
            out.writeLong(parcel.version());
            out.writeUTF(parcel.placeName());
            out.writeUTF(parcel.leaseId());
            out.writeUTF(parcel.mazeRef());
        }
        Trap trap = snapshot.trap();
        out.writeBoolean(trap != null);
        if (trap != null) {
            out.writeUTF(trap.id());
            out.writeInt(trap.at().x());
            out.writeInt(trap.at().y());
            out.writeInt(trap.at().z());
            out.writeUTF(trap.state().name());
        }
        Portal portal = snapshot.portal();
        out.writeBoolean(portal != null);
        if (portal != null) {
            out.writeUTF(portal.id());
            out.writeInt(portal.at().x());
            out.writeInt(portal.at().y());
            out.writeInt(portal.at().z());
            out.writeUTF(portal.state().name());
        }
        Npc npc = snapshot.npc();
        out.writeBoolean(npc != null);
        if (npc != null) {
            out.writeUTF(npc.id());
            out.writeInt(npc.at().x());
            out.writeInt(npc.at().y());
            out.writeInt(npc.at().z());
            out.writeUTF(npc.state().name());
        }
        List<Map.Entry<ParcelId, ParcelAcl>> acls = new ArrayList<>();
        for (Map.Entry<ParcelId, ParcelAcl> e : snapshot.acls().entrySet()) {
            ParcelAcl acl = e.getValue();
            if (acl != null && (!acl.grants().isEmpty() || !acl.denials().isEmpty())) {
                acls.add(e);
            }
        }
        acls.sort(Comparator.comparing(e -> e.getKey().value()));
        out.writeInt(acls.size());
        for (Map.Entry<ParcelId, ParcelAcl> e : acls) {
            out.writeUTF(e.getKey().value());
            writeGrants(out, e.getValue().grants());
            writeGrants(out, e.getValue().denials());
        }
    }

    static WorldSnapshot read(DataInputStream in) throws IOException {
        byte[] magic = in.readNBytes(MAGIC.length);
        if (magic.length != MAGIC.length || !java.util.Arrays.equals(magic, MAGIC)) {
            throw new IOException("Not a Daedalus world snapshot");
        }
        int version = in.readUnsignedByte();
        if (version != VERSION && version != VERSION_WITH_ACL
                && version != VERSION_WITH_MAZE_REF
                && version != VERSION_WITH_NPC
                && version != VERSION_WITH_PORTAL
                && version != VERSION_WITH_TRAP
                && version != VERSION_WITH_PARCELS
                && version != VERSION_WITH_PLACE_NAME
                && version != VERSION_WITH_LEASE
                && version != VERSION_WITH_DOOR && version != VERSION_CHUNKS_ONLY) {
            throw new IOException("Unsupported world snapshot version " + version);
        }
        WorldId id = new WorldId(in.readUTF());
        WorldRevision revision = new WorldRevision(in.readLong());
        int count = in.readInt();
        if (count < 0) {
            throw new IOException("Negative chunk count");
        }
        Map<ChunkCoordinate, Chunk> chunks = new LinkedHashMap<>();
        for (int i = 0; i < count; i++) {
            ChunkCoordinate coord = new ChunkCoordinate(in.readInt(), in.readInt(), in.readInt());
            long chunkRevision = in.readLong();
            byte[] payload = in.readNBytes(Chunk.VOLUME);
            if (payload.length != Chunk.VOLUME) {
                throw new IOException("Truncated chunk payload at " + coord);
            }
            chunks.put(coord, Chunk.ofPayload(payload, chunkRevision));
        }
        Door door = null;
        if (version >= VERSION_WITH_DOOR) {
            if (in.readBoolean()) {
                String doorId = in.readUTF();
                BlockCoordinate at = new BlockCoordinate(in.readInt(), in.readInt(), in.readInt());
                DoorState state = DoorState.valueOf(in.readUTF());
                door = new Door(doorId, id, at, state);
            }
        }
        List<Parcel> parcels = new ArrayList<>();
        if (version >= VERSION_WITH_PARCELS) {
            int parcelCount = in.readInt();
            if (parcelCount < 0) {
                throw new IOException("Negative parcel count");
            }
            for (int i = 0; i < parcelCount; i++) {
                ParcelId parcelId = new ParcelId(in.readUTF());
                WorldId parcelWorld = new WorldId(in.readUTF());
                String ownerId = in.readUTF();
                ParcelBounds bounds = new ParcelBounds(
                        in.readInt(), in.readInt(), in.readInt(),
                        in.readInt(), in.readInt(), in.readInt());
                long parcelVersion = in.readLong();
                String placeName = version >= VERSION_WITH_PLACE_NAME ? in.readUTF() : "";
                String leaseId = version >= VERSION_WITH_LEASE ? in.readUTF() : "";
                String mazeRef = version >= VERSION_WITH_MAZE_REF ? in.readUTF() : "";
                parcels.add(new Parcel(parcelId, parcelWorld, ownerId, bounds,
                        parcelVersion, placeName, leaseId, mazeRef));
            }
        }
        Trap trap = null;
        if (version >= VERSION_WITH_TRAP) {
            if (in.readBoolean()) {
                String trapId = in.readUTF();
                BlockCoordinate at = new BlockCoordinate(in.readInt(), in.readInt(), in.readInt());
                TrapState state = TrapState.valueOf(in.readUTF());
                trap = new Trap(trapId, id, at, state);
            }
        } else if (WorldId.ZERO.equals(id)) {
            trap = Trap.zero();
        }
        Portal portal = null;
        if (version >= VERSION_WITH_PORTAL) {
            if (in.readBoolean()) {
                String portalId = in.readUTF();
                BlockCoordinate at = new BlockCoordinate(in.readInt(), in.readInt(), in.readInt());
                PortalState state = PortalState.valueOf(in.readUTF());
                portal = new Portal(portalId, id, at, state);
            }
        } else if (WorldId.ZERO.equals(id)) {
            portal = Portal.zero();
        }
        Npc npc = null;
        if (version >= VERSION_WITH_NPC) {
            if (in.readBoolean()) {
                String npcId = in.readUTF();
                BlockCoordinate at = new BlockCoordinate(in.readInt(), in.readInt(), in.readInt());
                NpcState state = NpcState.valueOf(in.readUTF());
                npc = new Npc(npcId, id, at, state);
            }
        } else if (WorldId.ZERO.equals(id)) {
            npc = Npc.zero();
        }
        Map<ParcelId, ParcelAcl> acls = new LinkedHashMap<>();
        if (version >= VERSION_WITH_ACL) {
            int aclCount = in.readInt();
            if (aclCount < 0) {
                throw new IOException("Negative ACL count");
            }
            for (int i = 0; i < aclCount; i++) {
                ParcelId parcelId = new ParcelId(in.readUTF());
                List<ParcelAcl.Grant> grants = readGrants(in);
                List<ParcelAcl.Grant> denials = readGrants(in);
                acls.put(parcelId, new ParcelAcl(grants, denials));
            }
        }
        return new WorldSnapshot(id, revision, chunks, door, trap, portal, npc, parcels, acls);
    }

    private static void writeGrants(DataOutputStream out, List<ParcelAcl.Grant> rows)
            throws IOException {
        out.writeInt(rows.size());
        for (ParcelAcl.Grant row : rows) {
            out.writeUTF(row.actorId());
            out.writeUTF(row.verb().name());
        }
    }

    private static List<ParcelAcl.Grant> readGrants(DataInputStream in) throws IOException {
        int count = in.readInt();
        if (count < 0) {
            throw new IOException("Negative grant count");
        }
        List<ParcelAcl.Grant> rows = new ArrayList<>();
        for (int i = 0; i < count; i++) {
            rows.add(new ParcelAcl.Grant(in.readUTF(), ParcelVerb.valueOf(in.readUTF())));
        }
        return rows;
    }

    private static void requirePath(Path file) {
        if (file == null) {
            throw new IllegalArgumentException("World store path is required");
        }
    }
}
