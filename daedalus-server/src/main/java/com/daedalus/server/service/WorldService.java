// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.plugin.events.WorldBlockEvent;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockPlaceResult;
import com.daedalus.world.BlockType;
import com.daedalus.world.Chunk;
import com.daedalus.world.ChunkCoordinate;
import com.daedalus.world.Door;
import com.daedalus.world.DoorResult;
import com.daedalus.world.Npc;
import com.daedalus.world.NpcResult;
import com.daedalus.world.Parcel;
import com.daedalus.world.ParcelBounds;
import com.daedalus.world.ParcelDenyResult;
import com.daedalus.world.ParcelForgiveResult;
import com.daedalus.world.ParcelGrantResult;
import com.daedalus.world.ParcelLeaseResult;
import com.daedalus.world.ParcelReleaseResult;
import com.daedalus.world.ParcelRevokeResult;
import com.daedalus.world.Portal;
import com.daedalus.world.PortalResult;
import com.daedalus.world.Trap;
import com.daedalus.world.TrapResult;
import com.daedalus.world.World;
import com.daedalus.world.WorldId;
import com.daedalus.world.WorldStore;
import com.daedalus.world.auto.DriveTrace;
import com.daedalus.world.auto.Observation;
import com.daedalus.world.auto.WorldAddress;
import com.daedalus.world.auto.WorldOps;
import com.daedalus.world.living.LivingSlab;
import com.daedalus.world.stamp.StampOps;
import com.daedalus.world.stamp.StampRequest;
import com.daedalus.world.stamp.StampResult;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Consumer;

/**
 * One persistent world ({@code world-zero}). File-backed. Does not touch
 * {@link MazeGenerationService} or the maze Caffeine cache.
 */
@Service
public class WorldService {

    private final Path file;
    private final World world;
    private final Consumer<WorldBlockEvent> events;
    private final DriveTrace log = new DriveTrace();
    private final Object lock = new Object();
    private final Map<UUID, SlabBind> slabs = new ConcurrentHashMap<>();

    private record SlabBind(BlockCoordinate origin, int floorY, int wallHeight, ParcelBounds bounds) {
    }

    public WorldService(Path file) {
        this.file = file;
        this.events = event -> { };
        this.world = open(file);
        seedTrace(this.world);
        rebindSlabs();
    }

    @Autowired
    public WorldService(@Value("${daedalus.world.file}") Path file,
                        ApplicationEventPublisher publisher) {
        this.file = file;
        this.events = publisher::publishEvent;
        this.world = open(file);
        seedTrace(this.world);
        rebindSlabs();
    }

    public Path file() {
        return file;
    }

    public World inspect(String id) {
        return require(id);
    }

    public BlockType inspectBlock(String id, int x, int y, int z) {
        return require(id).get(new BlockCoordinate(x, y, z));
    }

    public Chunk inspectChunk(String id, int cx, int cy, int cz) {
        return require(id).chunk(new ChunkCoordinate(cx, cy, cz));
    }

    public Door inspectDoor(String id) {
        World live = require(id);
        return live == null ? null : live.door();
    }

    public Trap inspectTrap(String id) {
        World live = require(id);
        return live == null ? null : live.trap();
    }

    public Portal inspectPortal(String id) {
        World live = require(id);
        return live == null ? null : live.portal();
    }

    public Npc inspectNpc(String id) {
        World live = require(id);
        return live == null ? null : live.npc();
    }

    public BlockType place(String id, int x, int y, int z, BlockType type) {
        return place(id, x, y, z, type, null).previous();
    }

    public BlockWrite place(String id, int x, int y, int z, BlockType type, String actorId) {
        World live = require(id);
        synchronized (lock) {
            BlockCoordinate at = new BlockCoordinate(x, y, z);
            Object driven = WorldOps.drive(live, "block.place", at, type, null, actorId);
            BlockType now = live.get(at);
            if (driven == BlockPlaceResult.DENIED) {
                persist();
                account(live, "block.place", driven);
                return new BlockWrite(now, now, live.revision().value(), "DENIED");
            }
            BlockType previous = (BlockType) driven;
            persist();
            emit(id, now.solid() ? WorldBlockEvent.Kind.BLOCK_PLACED
                    : WorldBlockEvent.Kind.BLOCK_REMOVED, x, y, z, now, previous, live);
            account(live, now.solid() ? "block.place" : "block.remove", previous);
            return new BlockWrite(previous, now, live.revision().value(), "PLACED");
        }
    }

    /** Place outcome. {@code result} is never silent success. */
    public record BlockWrite(BlockType previous, BlockType now, long revision, String result) {
    }

    public BlockType remove(String id, int x, int y, int z) {
        return remove(id, x, y, z, null).previous();
    }

    public BlockWrite remove(String id, int x, int y, int z, String actorId) {
        World live = require(id);
        synchronized (lock) {
            BlockCoordinate at = new BlockCoordinate(x, y, z);
            Object driven = WorldOps.drive(live, "block.remove", at, null, null, actorId);
            BlockType now = live.get(at);
            if (driven == BlockPlaceResult.DENIED) {
                persist();
                account(live, "block.remove", driven);
                return new BlockWrite(now, now, live.revision().value(), "DENIED");
            }
            BlockType previous = (BlockType) driven;
            persist();
            emit(id, WorldBlockEvent.Kind.BLOCK_REMOVED, x, y, z, BlockType.AIR, previous, live);
            account(live, "block.remove", previous);
            return new BlockWrite(previous, now, live.revision().value(), "REMOVED");
        }
    }

    public DoorResult openDoor(String id) {
        return openDoor(id, null);
    }

    public DoorResult openDoor(String id, String actorId) {
        World live = require(id);
        synchronized (lock) {
            DoorResult result = WorldOps.asDoorResult(
                    WorldOps.drive(live, "door.open",
                            live.door() == null ? new BlockCoordinate(0, 0, 0) : live.door().at(),
                            null, null, actorId));
            persist();
            account(live, "door.open", result);
            return result;
        }
    }

    public DoorResult closeDoor(String id) {
        return closeDoor(id, null);
    }

    public DoorResult closeDoor(String id, String actorId) {
        World live = require(id);
        synchronized (lock) {
            DoorResult result = WorldOps.asDoorResult(
                    WorldOps.drive(live, "door.close",
                            live.door() == null ? new BlockCoordinate(0, 0, 0) : live.door().at(),
                            null, null, actorId));
            persist();
            account(live, "door.close", result);
            return result;
        }
    }

    public TrapResult armTrap(String id) {
        return armTrap(id, null);
    }

    public TrapResult armTrap(String id, String actorId) {
        World live = require(id);
        synchronized (lock) {
            TrapResult result = WorldOps.asTrapResult(
                    WorldOps.drive(live, "trap.arm",
                            live.trap() == null ? new BlockCoordinate(0, 0, 0) : live.trap().at(),
                            null, null, actorId));
            persist();
            account(live, "trap.arm", result);
            return result;
        }
    }

    public TrapResult disarmTrap(String id) {
        return disarmTrap(id, null);
    }

    public TrapResult disarmTrap(String id, String actorId) {
        World live = require(id);
        synchronized (lock) {
            TrapResult result = WorldOps.asTrapResult(
                    WorldOps.drive(live, "trap.disarm",
                            live.trap() == null ? new BlockCoordinate(0, 0, 0) : live.trap().at(),
                            null, null, actorId));
            persist();
            account(live, "trap.disarm", result);
            return result;
        }
    }

    public PortalResult openPortal(String id) {
        return openPortal(id, null);
    }

    public PortalResult openPortal(String id, String actorId) {
        World live = require(id);
        synchronized (lock) {
            PortalResult result = WorldOps.asPortalResult(
                    WorldOps.drive(live, "portal.open",
                            live.portal() == null ? new BlockCoordinate(0, 0, 0) : live.portal().at(),
                            null, null, actorId));
            persist();
            account(live, "portal.open", result);
            return result;
        }
    }

    public PortalResult sealPortal(String id) {
        return sealPortal(id, null);
    }

    public PortalResult sealPortal(String id, String actorId) {
        World live = require(id);
        synchronized (lock) {
            PortalResult result = WorldOps.asPortalResult(
                    WorldOps.drive(live, "portal.seal",
                            live.portal() == null ? new BlockCoordinate(0, 0, 0) : live.portal().at(),
                            null, null, actorId));
            persist();
            account(live, "portal.seal", result);
            return result;
        }
    }

    public NpcResult talkNpc(String id) {
        return talkNpc(id, null);
    }

    public NpcResult talkNpc(String id, String actorId) {
        World live = require(id);
        synchronized (lock) {
            NpcResult result = WorldOps.asNpcResult(
                    WorldOps.drive(live, "npc.talk",
                            live.npc() == null ? new BlockCoordinate(0, 0, 0) : live.npc().at(),
                            null, null, actorId));
            persist();
            account(live, "npc.talk", result);
            return result;
        }
    }

    public NpcResult hushNpc(String id) {
        return hushNpc(id, null);
    }

    public NpcResult hushNpc(String id, String actorId) {
        World live = require(id);
        synchronized (lock) {
            NpcResult result = WorldOps.asNpcResult(
                    WorldOps.drive(live, "npc.hush",
                            live.npc() == null ? new BlockCoordinate(0, 0, 0) : live.npc().at(),
                            null, null, actorId));
            persist();
            account(live, "npc.hush", result);
            return result;
        }
    }

    public ParcelLeaseResult leaseParcel(String id) {
        World live = require(id);
        synchronized (lock) {
            ParcelLeaseResult result = WorldOps.asLeaseResult(
                    WorldOps.drive(live, "parcel.lease", new BlockCoordinate(0, 0, 0), null));
            persist();
            account(live, "parcel.lease", result);
            return result;
        }
    }

    public ParcelReleaseResult releaseParcel(String id) {
        World live = require(id);
        synchronized (lock) {
            ParcelReleaseResult result = WorldOps.asReleaseResult(
                    WorldOps.drive(live, "parcel.release", new BlockCoordinate(0, 0, 0), null));
            persist();
            account(live, "parcel.release", result);
            return result;
        }
    }

    public ParcelGrantResult grantParcel(String id, BlockCoordinate at, String actorId) {
        return grantParcel(id, at, actorId, null);
    }

    public ParcelGrantResult grantParcel(String id, BlockCoordinate at, String actorId, String verb) {
        World live = require(id);
        synchronized (lock) {
            ParcelGrantResult result = WorldOps.asGrantResult(
                    WorldOps.drive(live, "parcel.grant",
                            at == null ? new BlockCoordinate(0, 0, 0) : at, null, null, actorId, verb));
            persist();
            account(live, "parcel.grant", result);
            return result;
        }
    }

    public ParcelDenyResult denyParcel(String id, BlockCoordinate at, String actorId) {
        return denyParcel(id, at, actorId, null);
    }

    public ParcelDenyResult denyParcel(String id, BlockCoordinate at, String actorId, String verb) {
        World live = require(id);
        synchronized (lock) {
            ParcelDenyResult result = WorldOps.asDenyResult(
                    WorldOps.drive(live, "parcel.deny",
                            at == null ? new BlockCoordinate(0, 0, 0) : at, null, null, actorId, verb));
            persist();
            account(live, "parcel.deny", result);
            return result;
        }
    }

    public ParcelRevokeResult revokeParcel(String id, BlockCoordinate at, String actorId) {
        return revokeParcel(id, at, actorId, null);
    }

    public ParcelRevokeResult revokeParcel(String id, BlockCoordinate at, String actorId, String verb) {
        World live = require(id);
        synchronized (lock) {
            ParcelRevokeResult result = WorldOps.asRevokeResult(
                    WorldOps.drive(live, "parcel.revoke",
                            at == null ? new BlockCoordinate(0, 0, 0) : at, null, null, actorId, verb));
            persist();
            account(live, "parcel.revoke", result);
            return result;
        }
    }

    public ParcelForgiveResult forgiveParcel(String id, BlockCoordinate at, String actorId) {
        return forgiveParcel(id, at, actorId, null);
    }

    public ParcelForgiveResult forgiveParcel(String id, BlockCoordinate at, String actorId,
            String verb) {
        World live = require(id);
        synchronized (lock) {
            ParcelForgiveResult result = WorldOps.asForgiveResult(
                    WorldOps.drive(live, "parcel.forgive",
                            at == null ? new BlockCoordinate(0, 0, 0) : at, null, null, actorId,
                            verb));
            persist();
            account(live, "parcel.forgive", result);
            return result;
        }
    }

    public StampResult stamp(String id, BlockCoordinate at) {
        return stamp(id, at, null);
    }

    /**
     * Project {@code maze} at {@code at}. A null maze is the WorldOps 1×1 slab.
     * This method does not look up the maze cache.
     */
    public StampResult stamp(String id, BlockCoordinate at, MazeGrid maze) {
        return stamp(id, at, maze, null);
    }

    /**
     * Project {@code maze} at {@code at}. When {@code mazeId} is present the
     * slab listens for later living snapshots of that maze. This method does
     * not look up the maze cache.
     */
    public StampResult stamp(String id, BlockCoordinate at, MazeGrid maze, UUID mazeId) {
        return stamp(id, at, maze, mazeId, false);
    }

    /**
     * {@code nextFree} walks +X past overlapping parcels. An explicit
     * address without that flag still returns {@code PARCEL_OVERLAP}.
     */
    public StampResult stamp(String id, BlockCoordinate at, MazeGrid maze, UUID mazeId,
                             boolean nextFree) {
        return stamp(id, at, maze, mazeId, nextFree, null);
    }

    public StampResult stamp(String id, BlockCoordinate at, MazeGrid maze, UUID mazeId,
                             boolean nextFree, String actorId) {
        World live = require(id);
        synchronized (lock) {
            BlockCoordinate origin = at;
            if (nextFree) {
                origin = StampOps.nextOrigin(live, maze, at, 1);
            }
            StampResult result = WorldOps.asStampResult(
                    WorldOps.drive(live, "stamp.apply", origin, null, maze,
                            mazeId == null ? null : mazeId.toString(), actorId));
            if (result.ok() && mazeId != null && result.parcelId() != null) {
                rebindSlabs();
            }
            persist();
            account(live, "stamp.apply", result);
            return result;
        }
    }

    /**
     * Re-project a living maze snapshot into its stamped AABB. Unknown maze
     * ids and inspect-quiet grids write nothing.
     */
    public int syncSlab(String id, UUID mazeId, MazeGrid snapshot) {
        World live = require(id);
        if (live == null || mazeId == null || snapshot == null) {
            return 0;
        }
        synchronized (lock) {
            SlabBind bind = slabs.get(mazeId);
            if (bind == null) {
                return 0;
            }
            LivingSlab slab = new LivingSlab(live, new StampRequest(
                    live.id(), bind.origin(), snapshot, bind.floorY(), bind.wallHeight()),
                    bind.bounds());
            int written = slab.sync();
            if (written > 0) {
                live.recordDrive("living.sync", Integer.toString(written),
                        Parcel.SYSTEM_OWNER, slab.lastWritten());
                persist();
                account(live, "living.sync", written);
            }
            return written;
        }
    }

    private void emit(String id, WorldBlockEvent.Kind kind, int x, int y, int z,
                      BlockType now, BlockType previous, World live) {
        long revision = live.revision().value();
        events.accept(new WorldBlockEvent(this, id, kind, x, y, z,
                now.name(), previous.name(), revision));
        events.accept(new WorldBlockEvent(this, id, WorldBlockEvent.Kind.WORLD_REVISION_CHANGED,
                x, y, z, now.name(), previous.name(), revision));
    }

    public Observation observe(String id, int x, int y, int z) {
        World live = require(id);
        if (live == null) {
            return null;
        }
        return Observation.take(live, new WorldAddress(live.id(), new BlockCoordinate(x, y, z)));
    }

    public List<DriveTrace.Step> trace(String id) {
        if (require(id) == null) {
            return null;
        }
        return log.steps();
    }

    private World require(String id) {
        if (id == null || !WorldId.ZERO.value().equals(id)) {
            return null;
        }
        return world;
    }

    private void rebindSlabs() {
        slabs.clear();
        for (Parcel parcel : world.parcels()) {
            if (parcel == null || parcel.mazeRef().isEmpty()) {
                continue;
            }
            try {
                UUID mazeId = UUID.fromString(parcel.mazeRef());
                ParcelBounds box = parcel.bounds();
                int height = Math.max(1, box.maxY() - box.minY());
                slabs.put(mazeId, new SlabBind(
                        new BlockCoordinate(box.minX(), box.minY(), box.minZ()),
                        box.minY(), height, box));
            } catch (IllegalArgumentException ignored) {
                // mazeRef is a lab id string; junk refs do not bind.
            }
        }
    }

    /**
     * Last drive survives the DAEW file. The in-memory account log does
     * not. Seed one step so GET /trace is not empty after restart.
     */
    private void seedTrace(World live) {
        if (live == null || live.lastDriveCapability().isBlank()) {
            return;
        }
        log.append(live.lastDriveCapability(), live.lastDriveResult(),
                live.revision().value(), live.lastDriveActor(), WorldOps.atLine(live));
    }

    private void account(World live, String capability, Object result) {
        log.append(capability, result, live.revision().value(), live.lastDriveActor(),
                WorldOps.atLine(live));
    }

    private void persist() {
        try {
            WorldStore.save(world, file);
        } catch (IOException e) {
            throw new UncheckedIOException("Cannot persist " + WorldId.ZERO, e);
        }
    }

    private static World open(Path file) {
        try {
            if (Files.exists(file)) {
                World loaded = WorldStore.load(file);
                if (!WorldId.ZERO.equals(loaded.id())) {
                    throw new IllegalStateException("World file is not world-zero: " + loaded.id());
                }
                return loaded;
            }
            World fresh = World.zero();
            WorldStore.save(fresh, file);
            return fresh;
        } catch (IOException e) {
            throw new UncheckedIOException("Cannot open world store at " + file, e);
        }
    }
}
