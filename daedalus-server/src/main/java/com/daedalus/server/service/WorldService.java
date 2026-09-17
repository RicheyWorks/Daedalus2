// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.plugin.events.WorldBlockEvent;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.Chunk;
import com.daedalus.world.ChunkCoordinate;
import com.daedalus.world.Door;
import com.daedalus.world.DoorResult;
import com.daedalus.world.Npc;
import com.daedalus.world.NpcResult;
import com.daedalus.world.ParcelLeaseResult;
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

    public WorldService(Path file) {
        this.file = file;
        this.events = event -> { };
        this.world = open(file);
    }

    @Autowired
    public WorldService(@Value("${daedalus.world.file}") Path file,
                        ApplicationEventPublisher publisher) {
        this.file = file;
        this.events = publisher::publishEvent;
        this.world = open(file);
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
        World live = require(id);
        synchronized (lock) {
            BlockCoordinate at = new BlockCoordinate(x, y, z);
            BlockType previous = live.place(at, type);
            persist();
            BlockType now = live.get(at);
            emit(id, now.solid() ? WorldBlockEvent.Kind.BLOCK_PLACED
                    : WorldBlockEvent.Kind.BLOCK_REMOVED, x, y, z, now, previous, live);
            log.append(now.solid() ? "block.place" : "block.remove", previous, live.revision().value());
            return previous;
        }
    }

    public BlockType remove(String id, int x, int y, int z) {
        World live = require(id);
        synchronized (lock) {
            BlockType previous = live.remove(new BlockCoordinate(x, y, z));
            persist();
            emit(id, WorldBlockEvent.Kind.BLOCK_REMOVED, x, y, z, BlockType.AIR, previous, live);
            log.append("block.remove", previous, live.revision().value());
            return previous;
        }
    }

    public DoorResult openDoor(String id) {
        World live = require(id);
        synchronized (lock) {
            DoorResult result = live.openDoor();
            persist();
            log.append("door.open", result, live.revision().value());
            return result;
        }
    }

    public DoorResult closeDoor(String id) {
        World live = require(id);
        synchronized (lock) {
            DoorResult result = live.closeDoor();
            persist();
            log.append("door.close", result, live.revision().value());
            return result;
        }
    }

    public TrapResult armTrap(String id) {
        World live = require(id);
        synchronized (lock) {
            TrapResult result = live.armTrap();
            persist();
            log.append("trap.arm", result, live.revision().value());
            return result;
        }
    }

    public TrapResult disarmTrap(String id) {
        World live = require(id);
        synchronized (lock) {
            TrapResult result = live.disarmTrap();
            persist();
            log.append("trap.disarm", result, live.revision().value());
            return result;
        }
    }

    public PortalResult openPortal(String id) {
        World live = require(id);
        synchronized (lock) {
            PortalResult result = live.openPortal();
            persist();
            log.append("portal.open", result, live.revision().value());
            return result;
        }
    }

    public PortalResult sealPortal(String id) {
        World live = require(id);
        synchronized (lock) {
            PortalResult result = live.sealPortal();
            persist();
            log.append("portal.seal", result, live.revision().value());
            return result;
        }
    }

    public NpcResult talkNpc(String id) {
        World live = require(id);
        synchronized (lock) {
            NpcResult result = live.talkNpc();
            persist();
            log.append("npc.talk", result, live.revision().value());
            return result;
        }
    }

    public NpcResult hushNpc(String id) {
        World live = require(id);
        synchronized (lock) {
            NpcResult result = live.hushNpc();
            persist();
            log.append("npc.hush", result, live.revision().value());
            return result;
        }
    }

    public ParcelLeaseResult leaseParcel(String id) {
        World live = require(id);
        synchronized (lock) {
            ParcelLeaseResult result = WorldOps.asLeaseResult(
                    WorldOps.drive(live, "parcel.lease", new BlockCoordinate(0, 0, 0), null));
            persist();
            log.append("parcel.lease", result, live.revision().value());
            return result;
        }
    }

    public StampResult stamp(String id, BlockCoordinate at) {
        World live = require(id);
        synchronized (lock) {
            StampResult result = WorldOps.asStampResult(
                    WorldOps.drive(live, "stamp.apply", at, null));
            persist();
            log.append("stamp.apply", result, live.revision().value());
            return result;
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
