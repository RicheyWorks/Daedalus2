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
import com.daedalus.world.ParcelAcl;
import com.daedalus.world.ParcelBounds;
import com.daedalus.world.ParcelDenyResult;
import com.daedalus.world.ParcelForgiveResult;
import com.daedalus.world.ParcelGrantResult;
import com.daedalus.world.ParcelLeaseResult;
import com.daedalus.world.ParcelReleaseResult;
import com.daedalus.world.ParcelRevokeResult;
import com.daedalus.world.ParcelVerb;
import com.daedalus.world.Portal;
import com.daedalus.world.PortalResult;
import com.daedalus.world.Trap;
import com.daedalus.world.TrapResult;
import com.daedalus.world.World;
import com.daedalus.world.WorldId;
import com.daedalus.world.ark.Ark;
import com.daedalus.world.ark.ArkOps;
import com.daedalus.world.ark.ArkFleet;
import com.daedalus.world.ark.Voyage;
import com.daedalus.world.ark.VoyageResult;
import com.daedalus.plugin.events.ArkVoyageEvent;
import com.daedalus.plugin.events.IslandLifeEvent;
import com.daedalus.world.ecology.Community;
import com.daedalus.world.ecology.Diversity;
import com.daedalus.world.ecology.EcologyLedger;
import com.daedalus.world.ecology.Ecosystem;
import com.daedalus.world.ecology.Habitat;
import com.daedalus.world.ecology.Hold;
import com.daedalus.world.ecology.SpeciesCanon;
import com.daedalus.world.island.IslandGenerator;
import com.daedalus.world.island.IslandOps;
import com.daedalus.world.island.IslandPlan;
import com.daedalus.world.island.IslandRaiseResult;
import com.daedalus.world.island.IslandTraits;
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
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.attribute.FileTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Consumer;
import java.util.function.LongSupplier;

/**
 * One persistent world. File-backed. Does not touch {@link MazeGenerationService} or the maze
 * Caffeine cache. The Spring bean serves {@code world-zero}; {@link WorldHub} mounts more worlds,
 * each its own instance with its own file and sidecars (ADR-030).
 */
@Service
public class WorldService {

    private final Path file;
    private final WorldId id;
    private final World world;
    private final Consumer<WorldBlockEvent> events;
    /** Every other event this service publishes (ark voyages, ADR-020). */
    private final Consumer<Object> published;
    /** Server clock for voyages; tests drive it. */
    private LongSupplier clock = System::currentTimeMillis;
    private ArkFleet fleet = new ArkFleet();

    /** Live ecology (ADR-023): every island's community and every ark's hold, under {@link #lock}. */
    private final SpeciesCanon canon = SpeciesCanon.get();
    private Ecosystem eco = new Ecosystem(canon);
    private final TreeMap<String, Hold> holds = new TreeMap<>();
    /** Server time ecological day 0 began; -1 until the first tick reads the clock. */
    private long ecoEpoch = -1;
    private volatile long dayMs = DEFAULT_DAY_MS;
    /** One ecological day of real time, unless {@code daedalus.realm.day-ms} says otherwise. */
    public static final long DEFAULT_DAY_MS = 10_000;
    /** Days stepped per tick at most, so a long-stopped server catches up over seconds, not at once. */
    public static final int MAX_CATCH_UP = 64;
    /** World Zero's ecology seed: drift, rain and catastrophe replay from it. */
    public static final long ECOLOGY_SEED = 0x5EEDL;
    private final DriveTrace log = new DriveTrace();
    private final Object lock = new Object();
    private final Map<UUID, SlabBind> slabs = new ConcurrentHashMap<>();
    /** Island lane: slot → (seed, radius). Persisted beside the DAEW file (ADR-018). */
    private final TreeMap<Integer, IslandEntry> islands = new TreeMap<>();

    /** Traits by "seed/radius". A pure function's answers; regrowing an island costs ~50 ms. */
    private static final Map<String, IslandTraits> TRAITS = new ConcurrentHashMap<>();

    /** A raised island as the lane remembers it. Traits are regrown from the seed on demand. */
    public record IslandEntry(int slot, long seed, int radius) {
        public BlockCoordinate origin() {
            return IslandOps.slot(slot);
        }

        public IslandTraits traits() {
            return TRAITS.computeIfAbsent(seed + "/" + radius,
                    k -> IslandGenerator.generate(seed, radius).traits());
        }
    }

    /** Outcome of {@link #raiseIsland}. {@code island} is null unless {@code result} is RAISED. */
    public record IslandWrite(String result, long revision, IslandEntry island, IslandTraits traits) {
    }

    private record SlabBind(BlockCoordinate origin, int floorY, int wallHeight, ParcelBounds bounds) {
    }

    public WorldService(Path file) {
        this(file, WorldId.ZERO, event -> { });
    }

    @Autowired
    public WorldService(@Value("${daedalus.world.file}") Path file,
                        ApplicationEventPublisher publisher) {
        this(file, WorldId.ZERO, publisher);
    }

    /** A world other than World Zero (ADR-030): its own id, its own file, the same event stream. */
    public WorldService(Path file, WorldId id, ApplicationEventPublisher publisher) {
        this.file = file;
        this.id = id;
        this.events = publisher::publishEvent;
        this.published = publisher::publishEvent;
        this.world = open(file, id);
        seedTrace(this.world);
        rebindSlabs();
        loadIslands();
        loadFleet();
        loadEcology();
    }

    public WorldId id() {
        return id;
    }

    /** Each world's ecology replays from its own seed; World Zero keeps the one it always had. */
    private long ecologySeed() {
        return WorldId.ZERO.equals(id) ? ECOLOGY_SEED : ECOLOGY_SEED ^ (id.value().hashCode() * 0x9E3779B97F4A7C15L);
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
            if (onClaimedIsland(live, at)) {
                return ParcelGrantResult.NO_PARCEL; // islands answer to their owner: /islands/{slot}/builders
            }
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
            if (onClaimedIsland(live, at)) {
                return ParcelDenyResult.NO_PARCEL; // islands answer to their owner: /islands/{slot}/builders
            }
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
            if (onClaimedIsland(live, at)) {
                return ParcelRevokeResult.NO_PARCEL; // islands answer to their owner: /islands/{slot}/builders
            }
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
            if (onClaimedIsland(live, at)) {
                return ParcelForgiveResult.NO_PARCEL;
            }
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
                BlockCoordinate at = slab.lastWritten();
                emit(id, slab.lastWrittenNow().solid()
                                ? WorldBlockEvent.Kind.BLOCK_PLACED
                                : WorldBlockEvent.Kind.BLOCK_REMOVED,
                        at.x(), at.y(), at.z(), slab.lastWrittenNow(),
                        slab.lastWrittenPrevious(), live);
            }
            return written;
        }
    }

    /**
     * Raise a seeded island into the first free slot of the island lane. All or nothing: the
     * plan lands whole or the lane is full and nothing changes. One persist, one revision event
     * for the whole island — not sixteen thousand block frames.
     */
    public IslandWrite raiseIsland(String id, long seed, int radius) {
        World live = require(id);
        if (live == null) {
            return null;
        }
        IslandPlan plan = IslandGenerator.generate(seed, radius);
        synchronized (lock) {
            int slot = IslandOps.firstFreeSlot(live, plan);
            if (slot < 0) {
                return new IslandWrite("LANE_FULL", live.revision().value(), null, plan.traits());
            }
            BlockCoordinate origin = IslandOps.slot(slot);
            IslandRaiseResult raised = IslandOps.raise(live, origin, plan);
            if (raised != IslandRaiseResult.RAISED) {
                // firstFreeSlot just said it fits and we hold the lock; anything else is a bug.
                throw new IllegalStateException("Island slot " + slot + " stopped fitting: " + raised);
            }
            IslandEntry entry = new IslandEntry(slot, seed, radius);
            islands.put(slot, entry);
            eco.addIsle(isleOf(entry));
            holds.put(Ark.idFor(slot), Hold.founders(seed, canon));
            persist();
            persistIslands();
            persistEcology();
            long revision = live.revision().value();
            events.accept(new WorldBlockEvent(this, id, WorldBlockEvent.Kind.WORLD_REVISION_CHANGED,
                    origin.x(), origin.y(), origin.z(), "ISLAND", BlockType.AIR.name(), revision));
            return new IslandWrite("RAISED", revision, entry, plan.traits());
        }
    }

    /** Who holds an island (ADR-026): owner "" when the island is open to everyone. */
    public record IslandClaim(String result, int slot, String owner, List<String> builders, long revision) {

        /** Copy on construct. */
        public IslandClaim {
            builders = builders == null ? List.of() : List.copyOf(builders);
        }
    }

    /** The claim parcel over a slot, or null when the island is unclaimed. Caller holds the lock. */
    private Parcel claimOf(World live, int slot) {
        ParcelBounds box = IslandOps.claimBounds(slot);
        for (Parcel p : live.parcels()) {
            if (p.bounds().equals(box)) {
                return p;
            }
        }
        return null;
    }

    /**
     * True when {@code at} lies in a claimed island's box (ADR-026). The generic parcel ACL routes
     * act on whatever parcel is under a cube and never ask who is calling; on an owned island that
     * would let anyone grant themselves the owner's rights, or deny the owner. Islands are managed
     * only through their own routes, which check the owner.
     */
    private boolean onClaimedIsland(World live, BlockCoordinate at) {
        if (at == null) {
            return false;
        }
        for (IslandEntry e : islands.values()) {
            if (IslandOps.claimBounds(e.slot()).contains(at) && claimOf(live, e.slot()) != null) {
                return true;
            }
        }
        return false;
    }

    private IslandClaim claimView(World live, String result, int slot) {
        Parcel p = claimOf(live, slot);
        List<String> builders = new ArrayList<>();
        if (p != null) {
            for (ParcelAcl.Grant g : live.acl(p.id()).grants()) {
                if (g.verb() == ParcelVerb.BLOCK_PLACE) {
                    builders.add(g.actorId());
                }
            }
        }
        return new IslandClaim(result, slot, p == null ? "" : p.ownerId(), builders, live.revision().value());
    }

    /** Who holds every island, in slot order; empty for an unknown world. */
    public Map<Integer, IslandClaim> claims(String id) {
        World live = require(id);
        if (live == null) {
            return Map.of();
        }
        synchronized (lock) {
            Map<Integer, IslandClaim> out = new TreeMap<>();
            for (IslandEntry e : islands.values()) {
                out.put(e.slot(), claimView(live, "", e.slot()));
            }
            return out;
        }
    }

    private static boolean badActor(String actor) {
        return actor == null || actor.isBlank() || actor.length() > 64
                || Parcel.SYSTEM_OWNER.equals(actor.trim()) || !actor.trim().matches("[A-Za-z0-9._@-]+");
    }

    /**
     * Claim an island for {@code owner} (ADR-026). Results: CLAIMED, ALREADY_CLAIMED (by anyone,
     * including the caller), NO_SUCH_ISLAND, BAD_OWNER, BLOCKED (another parcel overlaps the box).
     * Null for an unknown world.
     */
    public IslandClaim claimIsland(String id, int slot, String owner) {
        World live = require(id);
        if (live == null) {
            return null;
        }
        synchronized (lock) {
            if (!islands.containsKey(slot)) {
                return claimView(live, "NO_SUCH_ISLAND", slot);
            }
            if (badActor(owner)) {
                return claimView(live, "BAD_OWNER", slot);
            }
            if (claimOf(live, slot) != null) {
                return claimView(live, "ALREADY_CLAIMED", slot);
            }
            if (live.claimParcel(IslandOps.claimBounds(slot), owner.trim(), "Isle " + slot) == null) {
                return claimView(live, "BLOCKED", slot);
            }
            persist();
            announceClaim(id, live, slot);
            return claimView(live, "CLAIMED", slot);
        }
    }

    /** Give an island back. Results: ABANDONED, NOT_OWNER, NOT_CLAIMED, NO_SUCH_ISLAND. */
    public IslandClaim abandonIsland(String id, int slot, String actor) {
        World live = require(id);
        if (live == null) {
            return null;
        }
        synchronized (lock) {
            if (!islands.containsKey(slot)) {
                return claimView(live, "NO_SUCH_ISLAND", slot);
            }
            Parcel p = claimOf(live, slot);
            if (p == null) {
                return claimView(live, "NOT_CLAIMED", slot);
            }
            if (actor == null || !p.ownerId().equals(actor.trim())) {
                return claimView(live, "NOT_OWNER", slot);
            }
            live.dropParcel(p.id());
            persist();
            announceClaim(id, live, slot);
            return claimView(live, "ABANDONED", slot);
        }
    }

    /**
     * The owner lets {@code builder} build on their island, or stops them. Results: GRANTED,
     * REVOKED, NOT_OWNER, NOT_CLAIMED, NO_SUCH_ISLAND, BAD_BUILDER.
     */
    public IslandClaim setBuilder(String id, int slot, String actor, String builder, boolean allow) {
        World live = require(id);
        if (live == null) {
            return null;
        }
        synchronized (lock) {
            if (!islands.containsKey(slot)) {
                return claimView(live, "NO_SUCH_ISLAND", slot);
            }
            Parcel p = claimOf(live, slot);
            if (p == null) {
                return claimView(live, "NOT_CLAIMED", slot);
            }
            if (actor == null || !p.ownerId().equals(actor.trim())) {
                return claimView(live, "NOT_OWNER", slot);
            }
            if (badActor(builder) || p.ownerId().equals(builder.trim())) {
                return claimView(live, "BAD_BUILDER", slot);
            }
            if (allow) {
                live.grant(p.id(), builder.trim(), ParcelVerb.BLOCK_PLACE);
            } else {
                live.revoke(p.id(), builder.trim(), ParcelVerb.BLOCK_PLACE);
            }
            persist();
            announceClaim(id, live, slot);
            return claimView(live, allow ? "GRANTED" : "REVOKED", slot);
        }
    }

    private void announceClaim(String id, World live, int slot) {
        BlockCoordinate o = IslandOps.slot(slot);
        events.accept(new WorldBlockEvent(this, id, WorldBlockEvent.Kind.WORLD_REVISION_CHANGED,
                o.x(), o.y(), o.z(), "CLAIM", BlockType.AIR.name(), live.revision().value()));
    }

    /** Islands in slot order, or null for an unknown world. */
    public List<IslandEntry> islands(String id) {
        if (require(id) == null) {
            return null;
        }
        synchronized (lock) {
            return List.copyOf(islands.values());
        }
    }

    /** Replace the voyage clock (tests). Production uses the wall clock. */
    public void useClock(LongSupplier clock) {
        this.clock = clock;
    }

    public long now() {
        return clock.getAsLong();
    }

    /** An ark where it is now, with its voyage when underway (ADR-020). */
    public record ArkView(Ark ark, Voyage voyage, Map<String, Double> hold) {

        /** Copy on construct: a view is what the hold carried when it was taken. */
        public ArkView {
            hold = hold == null ? Map.of() : Map.copyOf(hold);
        }
    }

    /** Outcome of an order to sail; {@code view} is the ark after the order, null if no such ark. */
    public record SailWrite(VoyageResult result, ArkView view) {
    }

    /**
     * One ark per raised island (ADR-019), each where the fleet says it is: moored at a pier or
     * sailing toward one (ADR-020). Settles any arrival that is due first. Null for an unknown world.
     */
    public List<ArkView> arks(String id) {
        if (require(id) == null) {
            return null;
        }
        settleArrivals(id);
        synchronized (lock) {
            List<ArkView> out = new ArrayList<>();
            for (IslandEntry home : islands.values()) {
                out.add(view(home));
            }
            return out;
        }
    }

    private ArkView view(IslandEntry home) {
        String arkId = Ark.idFor(home.slot());
        int at = fleet.slotOf(arkId, home.slot());
        IslandEntry where = islands.get(at);
        Ark launched = ArkOps.launch(home.slot(), home.traits());
        Ark placed = new Ark(arkId, launched.name(), home.slot(), at,
                where == null ? launched.berth() : ArkOps.berth(at, where.traits()));
        Hold hold = holds.get(arkId);
        return new ArkView(placed, fleet.voyageOf(arkId), hold == null ? Map.of() : hold.cargo());
    }

    /** Order an ark to the island in {@code toSlot}. Null result means the world is unknown. */
    public SailWrite sail(String id, String arkId, int toSlot) {
        if (require(id) == null) {
            return null;
        }
        settleArrivals(id);
        synchronized (lock) {
            IslandEntry home = homeOf(arkId);
            if (home == null) {
                return new SailWrite(null, null);
            }
            ArkFleet.Outcome out = fleet.sail(arkId, home.slot(), toSlot, slot -> {
                IslandEntry isle = islands.get(slot);
                return isle == null ? null : ArkOps.berth(slot, isle.traits());
            }, now());
            if (out.result() == VoyageResult.SAILING) {
                persistFleet();
                Voyage v = out.voyage();
                Community leaving = eco.community(v.fromSlot());
                if (leaving != null) {
                    List<String> boarded = holdOf(arkId).board(leaving, v.departAt() * 31 + v.fromSlot());
                    persistEcology();
                    if (!boarded.isEmpty()) {
                        published.accept(new IslandLifeEvent(this, id, IslandLifeEvent.Kind.BOARDED, eco.day(),
                                v.fromSlot(), arkId, boarded, richness()));
                    }
                }
                published.accept(new ArkVoyageEvent(this, id, ArkVoyageEvent.Kind.DEPARTED, arkId,
                        v.fromSlot(), v.toSlot(), v.departAt(), v.arriveAt()));
            }
            return new SailWrite(out.result(), view(home));
        }
    }

    /** Tie up every ark whose voyage is due. Called by the harbour clock and before every read. */
    public List<Voyage> settleArrivals(String id) {
        if (require(id) == null) {
            return List.of();
        }
        synchronized (lock) {
            List<Voyage> arrived = fleet.settle(now());
            if (!arrived.isEmpty()) {
                persistFleet();
                List<IslandLifeEvent> landings = new ArrayList<>();
                for (Voyage v : arrived) {
                    Community landing = eco.community(v.toSlot());
                    if (landing != null) {
                        List<String> landed = holdOf(v.arkId()).land(landing, eco.isle(v.toSlot()).habitat(), canon);
                        if (!landed.isEmpty()) {
                            landings.add(new IslandLifeEvent(this, id, IslandLifeEvent.Kind.LANDED, eco.day(),
                                    v.toSlot(), v.arkId(), landed, richness()));
                        }
                    }
                }
                persistEcology();
                landings.forEach(published);
                for (Voyage v : arrived) {
                    published.accept(new ArkVoyageEvent(this, id, ArkVoyageEvent.Kind.ARRIVED,
                            v.arkId(), v.fromSlot(), v.toSlot(), v.departAt(), v.arriveAt()));
                }
            }
            return arrived;
        }
    }

    private IslandEntry homeOf(String arkId) {
        for (IslandEntry e : islands.values()) {
            if (Ark.idFor(e.slot()).equals(arkId)) {
                return e;
            }
        }
        return null;
    }

    /** Kinds living on every island, by slot. Caller holds the lock. */
    private Map<Integer, Integer> richness() {
        Map<Integer, Integer> out = new TreeMap<>();
        eco.communities().forEach((slot, c) -> out.put(slot, c.abundance().size()));
        return out;
    }

    private Hold holdOf(String arkId) {
        return holds.computeIfAbsent(arkId, k -> new Hold());
    }

    private static Ecosystem.Isle isleOf(IslandEntry e) {
        BlockCoordinate o = e.origin();
        return new Ecosystem.Isle(e.slot(), Habitat.of(e.traits()), o.x(), o.z());
    }

    /** Length of one ecological day in ms. Set from {@code daedalus.realm.day-ms}; tests shorten it. */
    @Autowired(required = false)
    public void useDayLength(@Value("${daedalus.realm.day-ms:10000}") long ms) {
        if (ms < 1) {
            throw new IllegalArgumentException("day length must be >= 1 ms");
        }
        synchronized (lock) {
            this.dayMs = ms;
        }
    }

    public long dayLength() {
        return dayMs;
    }

    /**
     * Step the ecology up to the server clock (ADR-023): one day per {@link #dayLength()} since the
     * epoch, at most {@link #MAX_CATCH_UP} per call. Called by the harbour clock and before every
     * ecology read. Returns the day reports stepped, oldest first; empty for an unknown world.
     */
    public List<Ecosystem.DayReport> tickEcology(String id) {
        if (require(id) == null) {
            return List.of();
        }
        synchronized (lock) {
            long t = now();
            if (ecoEpoch < 0) {
                ecoEpoch = t;
                persistEcology();
                return List.of();
            }
            long due = Math.max(0, (t - ecoEpoch) / dayMs - eco.day());
            List<Ecosystem.DayReport> reports = new ArrayList<>();
            for (long d = 0; d < Math.min(due, MAX_CATCH_UP); d++) {
                reports.add(eco.step(ecologySeed()));
            }
            if (!reports.isEmpty()) {
                persistEcology();
                published.accept(new IslandLifeEvent(this, id, IslandLifeEvent.Kind.DAY, eco.day(), -1, null,
                        List.of(), richness()));
            }
            return reports;
        }
    }

    /** One island's life right now (ADR-023). */
    public record IslandEcology(int slot, long day, Habitat habitat, Diversity diversity,
                                Map<String, Double> abundance) {

        /** Copy on construct: a snapshot, not a live view. */
        public IslandEcology {
            abundance = abundance == null ? Map.of() : Map.copyOf(abundance);
        }
    }

    /** An island's community, stepped to now first; null if the world or the slot is unknown. */
    public IslandEcology ecology(String id, int slot) {
        if (require(id) == null) {
            return null;
        }
        settleArrivals(id);
        tickEcology(id);
        synchronized (lock) {
            Community c = eco.community(slot);
            if (c == null) {
                return null;
            }
            return new IslandEcology(slot, eco.day(), eco.isle(slot).habitat(), c.diversity(), c.abundance());
        }
    }

    Path ecologyFile() {
        return file.resolveSibling(file.getFileName() + ".ecology");
    }

    private void loadEcology() {
        eco = new Ecosystem(canon);
        holds.clear();
        ecoEpoch = -1;
        for (IslandEntry e : islands.values()) {
            eco.addIsle(isleOf(e));
        }
        Path f = ecologyFile();
        if (Files.exists(f)) {
            try {
                EcologyLedger.State state = EcologyLedger.fromLines(Files.readAllLines(f, StandardCharsets.UTF_8));
                ecoEpoch = state.epoch();
                eco.setDay(state.day());
                state.isles().forEach((slot, counts) -> {
                    Community c = eco.community(slot);
                    if (c != null) {
                        counts.forEach(c::put);
                    }
                });
                state.holds().forEach((arkId, counts) -> {
                    Hold h = new Hold();
                    counts.forEach(h::put);
                    holds.put(arkId, h);
                });
            } catch (IOException | RuntimeException e) {
                throw new IllegalStateException("Cannot read ecology " + f, e);
            }
        }
        // Islands raised before ADR-023 launched their arks empty; give them their founders now.
        for (IslandEntry e : islands.values()) {
            holds.computeIfAbsent(Ark.idFor(e.slot()), k -> Hold.founders(e.seed(), canon));
        }
    }

    private void persistEcology() {
        Path f = ecologyFile();
        try {
            Path tmp = f.resolveSibling(f.getFileName() + ".tmp");
            Files.write(tmp, EcologyLedger.toLines(ecoEpoch, eco, holds), StandardCharsets.UTF_8);
            Files.move(tmp, f, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException e) {
            throw new UncheckedIOException("Cannot persist ecology " + f, e);
        }
    }

    Path fleetFile() {
        return file.resolveSibling(file.getFileName() + ".arks");
    }

    private void loadFleet() {
        Path f = fleetFile();
        if (!Files.exists(f)) {
            fleet = new ArkFleet();
            return;
        }
        try {
            fleet = ArkFleet.fromLines(Files.readAllLines(f, StandardCharsets.UTF_8));
        } catch (IOException | RuntimeException e) {
            throw new IllegalStateException("Cannot read ark fleet " + f, e);
        }
    }

    private void persistFleet() {
        Path f = fleetFile();
        List<String> rows = new ArrayList<>();
        rows.add("# Daedalus ark fleet (ADR-020): arkId slot [fromSlot toSlot departAt arriveAt]");
        rows.addAll(fleet.toLines());
        try {
            Path tmp = f.resolveSibling(f.getFileName() + ".tmp");
            Files.write(tmp, rows, StandardCharsets.UTF_8);
            Files.move(tmp, f, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException e) {
            throw new UncheckedIOException("Cannot persist ark fleet " + f, e);
        }
    }

    Path islandsFile() {
        return file.resolveSibling(file.getFileName() + ".islands");
    }

    private void loadIslands() {
        islands.clear();
        Path lane = islandsFile();
        if (!Files.exists(lane)) {
            return;
        }
        try {
            for (String line : Files.readAllLines(lane, StandardCharsets.UTF_8)) {
                String trimmed = line.trim();
                if (trimmed.isEmpty() || trimmed.startsWith("#")) {
                    continue;
                }
                String[] f = trimmed.split("\\s+");
                if (f.length != 3) {
                    throw new IOException("Bad island lane row: " + trimmed);
                }
                IslandEntry e = new IslandEntry(Integer.parseInt(f[0]), Long.parseLong(f[1]),
                        Integer.parseInt(f[2]));
                islands.put(e.slot(), e);
            }
        } catch (IOException | NumberFormatException e) {
            throw new IllegalStateException("Cannot read island lane " + lane, e);
        }
    }

    private void persistIslands() {
        Path lane = islandsFile();
        List<String> rows = new ArrayList<>();
        rows.add("# Daedalus island lane (ADR-018): slot seed radius. Terrain regrows from the seed.");
        for (IslandEntry e : islands.values()) {
            rows.add(e.slot() + " " + e.seed() + " " + e.radius());
        }
        try {
            Path tmp = lane.resolveSibling(lane.getFileName() + ".tmp");
            Files.write(tmp, rows, StandardCharsets.UTF_8);
            Files.move(tmp, lane, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException e) {
            throw new UncheckedIOException("Cannot persist island lane " + lane, e);
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
        if (id == null || !this.id.value().equals(id)) {
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
            long before = Files.exists(file)
                    ? Files.getLastModifiedTime(file).toMillis()
                    : Long.MIN_VALUE;
            WorldStore.save(world, file);
            long after = Files.getLastModifiedTime(file).toMillis();
            if (after <= before) {
                Files.setLastModifiedTime(file, FileTime.fromMillis(before + 1));
            }
        } catch (IOException e) {
            throw new UncheckedIOException("Cannot persist " + id.value(), e);
        }
    }

    private static World open(Path file, WorldId id) {
        try {
            if (Files.exists(file)) {
                World loaded = WorldStore.load(file);
                if (!id.equals(loaded.id())) {
                    throw new IllegalStateException("World file is not " + id.value() + ": " + loaded.id());
                }
                return loaded;
            }
            World fresh = WorldId.ZERO.equals(id) ? World.zero() : new World(id);
            WorldStore.save(fresh, file);
            return fresh;
        } catch (IOException e) {
            throw new UncheckedIOException("Cannot open world store at " + file, e);
        }
    }
}
