// SPDX-License-Identifier: MIT

package com.daedalus.world;

import com.daedalus.world.stamp.StampResult;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Sparse voxel volume. Each instance owns its chunk map — two worlds never share storage.
 * Missing chunks read as AIR. Place and remove advance {@link WorldRevision}; get does not.
 */
public final class World {

    private final WorldId id;
    private final ConcurrentHashMap<ChunkCoordinate, Chunk> chunks = new ConcurrentHashMap<>();
    private final AtomicLong revision = new AtomicLong();
    /**
     * Private lock so factories that publish a {@code World} do not expose the monitor
     * callers would otherwise share with {@code synchronized} methods.
     */
    private final Object lock = new Object();
    /** Assigned once; open/close mutate {@link Door} under {@link #lock}. */
    private final Door door;
    /** Assigned once; arm/disarm mutate {@link Trap} under {@link #lock}. */
    private final Trap trap;
    /** Assigned once; open/seal mutate {@link Portal} under {@link #lock}. */
    private final Portal portal;
    /** Assigned once; talk/hush mutate {@link Npc} under {@link #lock}. */
    private final Npc npc;
    private final List<Parcel> parcels = new ArrayList<>();
    private final ConcurrentHashMap<ParcelId, ParcelAcl> acls = new ConcurrentHashMap<>();
    private int nextParcelNumber;

    public World(WorldId id) {
        this(id, WorldId.ZERO.equals(Objects.requireNonNull(id, "WorldId is required"))
                ? Door.zero()
                : null,
                WorldId.ZERO.equals(id) ? Trap.zero() : null,
                WorldId.ZERO.equals(id) ? Portal.zero() : null,
                WorldId.ZERO.equals(id) ? Npc.zero() : null,
                0L, Map.of(), List.of());
    }

    private World(WorldId id, Door door, Trap trap, Portal portal, Npc npc, long revision,
            Map<ChunkCoordinate, Chunk> seeded, List<Parcel> seededParcels) {
        this.id = Objects.requireNonNull(id, "WorldId is required");
        this.door = door;
        this.trap = trap;
        this.portal = portal;
        this.npc = npc;
        this.revision.set(revision);
        for (Map.Entry<ChunkCoordinate, Chunk> e : seeded.entrySet()) {
            this.chunks.put(e.getKey(), e.getValue().copy());
        }
        if (seededParcels != null) {
            this.parcels.addAll(seededParcels);
            this.nextParcelNumber = maxParcelNumber(this.parcels);
        }
    }

    public static World zero() {
        return new World(WorldId.ZERO);
    }

    public WorldId id() {
        return id;
    }

    public WorldRevision revision() {
        return new WorldRevision(revision.get());
    }

    public BlockType get(BlockCoordinate at) {
        Objects.requireNonNull(at, "BlockCoordinate is required");
        Chunk chunk = chunks.get(at.chunk());
        if (chunk == null) {
            return BlockType.AIR;
        }
        return chunk.get(at.localX(), at.localY(), at.localZ());
    }

    /**
     * Occupied when a chunk is present and the local cube is not AIR.
     */
    public boolean contains(BlockCoordinate at) {
        return get(at) != BlockType.AIR;
    }

    /**
     * Writes {@code type} at {@code at}. {@link BlockType#AIR} is {@link #remove}.
     * Always a mutation: the world revision advances even when the cube already held
     * that type.
     */
    public BlockType place(BlockCoordinate at, BlockType type) {
        Objects.requireNonNull(at, "BlockCoordinate is required");
        Objects.requireNonNull(type, "BlockType is required");
        if (type == BlockType.AIR) {
            return remove(at);
        }
        synchronized (lock) {
            Chunk chunk = chunks.computeIfAbsent(at.chunk(), key -> new Chunk());
            BlockType previous = chunk.set(at.localX(), at.localY(), at.localZ(), type);
            revision.incrementAndGet();
            return previous;
        }
    }

    /**
     * Returns the cube to AIR and drops the chunk when it becomes empty.
     */
    public BlockType remove(BlockCoordinate at) {
        Objects.requireNonNull(at, "BlockCoordinate is required");
        synchronized (lock) {
            ChunkCoordinate cc = at.chunk();
            Chunk chunk = chunks.get(cc);
            if (chunk == null) {
                revision.incrementAndGet();
                return BlockType.AIR;
            }
            BlockType previous = chunk.set(at.localX(), at.localY(), at.localZ(), BlockType.AIR);
            if (chunk.isEmpty()) {
                chunks.remove(cc);
            }
            revision.incrementAndGet();
            return previous;
        }
    }

    public int chunkCount() {
        return chunks.size();
    }

    /**
     * Snapshot of one chunk, or {@code null} when the world has no payload there.
     */
    public Chunk chunk(ChunkCoordinate at) {
        Objects.requireNonNull(at, "ChunkCoordinate is required");
        Chunk chunk = chunks.get(at);
        return chunk == null ? null : chunk.copy();
    }

    public Set<ChunkCoordinate> chunkKeys() {
        return Collections.unmodifiableSet(chunks.keySet());
    }

    public Door door() {
        synchronized (lock) {
            return door == null ? null : door.copy();
        }
    }

    public DoorResult openDoor() {
        synchronized (lock) {
            if (door == null) {
                throw new IllegalStateException("This world has no door");
            }
            DoorResult result = door.open();
            if (result == DoorResult.OPENED) {
                revision.incrementAndGet();
            }
            return result;
        }
    }

    public DoorResult closeDoor() {
        synchronized (lock) {
            if (door == null) {
                throw new IllegalStateException("This world has no door");
            }
            DoorResult result = door.close();
            if (result == DoorResult.CLOSED) {
                revision.incrementAndGet();
            }
            return result;
        }
    }

    public Trap trap() {
        synchronized (lock) {
            return trap == null ? null : trap.copy();
        }
    }

    public TrapResult armTrap() {
        synchronized (lock) {
            if (trap == null) {
                throw new IllegalStateException("This world has no trap");
            }
            TrapResult result = trap.arm();
            if (result == TrapResult.ARMED) {
                revision.incrementAndGet();
            }
            return result;
        }
    }

    public TrapResult disarmTrap() {
        synchronized (lock) {
            if (trap == null) {
                throw new IllegalStateException("This world has no trap");
            }
            TrapResult result = trap.disarm();
            if (result == TrapResult.DISARMED) {
                revision.incrementAndGet();
            }
            return result;
        }
    }

    public Portal portal() {
        synchronized (lock) {
            return portal == null ? null : portal.copy();
        }
    }

    public PortalResult openPortal() {
        synchronized (lock) {
            if (portal == null) {
                throw new IllegalStateException("This world has no portal");
            }
            PortalResult result = portal.open();
            if (result == PortalResult.OPENED) {
                revision.incrementAndGet();
            }
            return result;
        }
    }

    public PortalResult sealPortal() {
        synchronized (lock) {
            if (portal == null) {
                throw new IllegalStateException("This world has no portal");
            }
            PortalResult result = portal.seal();
            if (result == PortalResult.SEALED) {
                revision.incrementAndGet();
            }
            return result;
        }
    }

    public Npc npc() {
        synchronized (lock) {
            return npc == null ? null : npc.copy();
        }
    }

    public NpcResult talkNpc() {
        synchronized (lock) {
            if (npc == null) {
                throw new IllegalStateException("This world has no npc");
            }
            NpcResult result = npc.talk();
            if (result == NpcResult.SPOKE) {
                revision.incrementAndGet();
            }
            return result;
        }
    }

    public NpcResult hushNpc() {
        synchronized (lock) {
            if (npc == null) {
                throw new IllegalStateException("This world has no npc");
            }
            NpcResult result = npc.hush();
            if (result == NpcResult.HUSHED) {
                revision.incrementAndGet();
            }
            return result;
        }
    }

    /**
     * Deep copy for a snapshot. Inspect: revision does not move.
     */
    public WorldSnapshot snapshot() {
        synchronized (lock) {
            Map<ChunkCoordinate, Chunk> copy = new LinkedHashMap<>();
            for (Map.Entry<ChunkCoordinate, Chunk> e : chunks.entrySet()) {
                copy.put(e.getKey(), e.getValue().copy());
            }
            return new WorldSnapshot(id, revision(), Map.copyOf(copy),
                    door == null ? null : door.copy(),
                    trap == null ? null : trap.copy(),
                    portal == null ? null : portal.copy(),
                    npc == null ? null : npc.copy(),
                    List.copyOf(parcels));
        }
    }

    public List<Parcel> parcels() {
        synchronized (lock) {
            return List.copyOf(parcels);
        }
    }

    /**
     * Unparceled cubes stay open (World Zero place). A stamped parcel uses
     * {@link ParcelGate}: owner allowed, listed deny wins, grants for others.
     */
    public ParcelAccess may(String actorId, ParcelVerb verb, BlockCoordinate at) {
        Objects.requireNonNull(at, "BlockCoordinate is required");
        Objects.requireNonNull(verb, "verb is required");
        Parcel parcel = parcelAt(at);
        if (parcel == null) {
            return ParcelAccess.ALLOWED;
        }
        return ParcelGate.check(parcel, acls.get(parcel.id()), actorId, verb);
    }

    public void grant(ParcelId id, String actorId, ParcelVerb verb) {
        requireParcel(id);
        synchronized (lock) {
            acls.merge(id, ParcelAcl.empty().grant(actorId, verb),
                    (old, ignored) -> old.grant(actorId, verb));
        }
    }

    public void deny(ParcelId id, String actorId, ParcelVerb verb) {
        requireParcel(id);
        synchronized (lock) {
            acls.merge(id, ParcelAcl.empty().deny(actorId, verb),
                    (old, ignored) -> old.deny(actorId, verb));
        }
    }

    private Parcel parcelAt(BlockCoordinate at) {
        synchronized (lock) {
            for (Parcel parcel : parcels) {
                if (parcel.bounds().contains(at)) {
                    return parcel;
                }
            }
            return null;
        }
    }

    private void requireParcel(ParcelId id) {
        Objects.requireNonNull(id, "ParcelId is required");
        synchronized (lock) {
            for (Parcel parcel : parcels) {
                if (parcel.id().equals(id)) {
                    return;
                }
            }
        }
        throw new IllegalArgumentException("Unknown parcel " + id.value());
    }

    /**
     * Atomically refuse overlapping parcels, then place cubes and register one parcel.
     * Overlap does not call {@link #place} and does not bump revision.
     */
    public StampResult applyStamp(ParcelBounds bounds, String ownerId,
            List<BlockCoordinate> positions, List<BlockType> types) {
        Objects.requireNonNull(bounds, "ParcelBounds is required");
        Objects.requireNonNull(ownerId, "ownerId is required");
        Objects.requireNonNull(positions, "stamp positions are required");
        Objects.requireNonNull(types, "stamp types are required");
        if (ownerId.isBlank()) {
            throw new IllegalArgumentException("ownerId is required");
        }
        if (positions.size() != types.size()) {
            throw new IllegalArgumentException("stamp positions and types must match");
        }
        synchronized (lock) {
            for (Parcel existing : parcels) {
                if (existing.bounds().overlaps(bounds)) {
                    return StampResult.overlap(revision());
                }
            }
            for (int i = 0; i < positions.size(); i++) {
                place(positions.get(i), types.get(i));
            }
            ParcelId id = new ParcelId("parcel-" + (++nextParcelNumber));
            parcels.add(new Parcel(id, this.id, ownerId, bounds, 1L));
            return StampResult.applied(id, bounds, revision());
        }
    }

    /**
     * Rebuild a world from a snapshot. The live map is a new copy — not the
     * snapshot's chunks and not another world's storage.
     */
    public static World from(WorldSnapshot snapshot) {
        Objects.requireNonNull(snapshot, "WorldSnapshot is required");
        return new World(
                snapshot.id(),
                snapshot.door() == null ? null : snapshot.door().copy(),
                snapshot.trap() == null ? null : snapshot.trap().copy(),
                snapshot.portal() == null ? null : snapshot.portal().copy(),
                snapshot.npc() == null ? null : snapshot.npc().copy(),
                snapshot.revision().value(),
                snapshot.chunks(),
                snapshot.parcels());
    }

    private static int maxParcelNumber(List<Parcel> existing) {
        int max = 0;
        for (Parcel parcel : existing) {
            String value = parcel.id().value();
            if (value.startsWith("parcel-")) {
                try {
                    max = Math.max(max, Integer.parseInt(value.substring("parcel-".length())));
                } catch (NumberFormatException ignored) {
                    // keep going; non-numeric ids do not advance the sequence
                }
            }
        }
        return max;
    }
}
