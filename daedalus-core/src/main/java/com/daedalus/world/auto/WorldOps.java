// SPDX-License-Identifier: MIT

package com.daedalus.world.auto;

import com.daedalus.engine.MazeGrid;
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
import com.daedalus.world.ParcelAccess;
import com.daedalus.world.ParcelAcl;
import com.daedalus.world.ParcelBounds;
import com.daedalus.world.ParcelDenyResult;
import com.daedalus.world.ParcelForgiveResult;
import com.daedalus.world.ParcelGrantResult;
import com.daedalus.world.ParcelId;
import com.daedalus.world.ParcelLeaseResult;
import com.daedalus.world.ParcelReleaseResult;
import com.daedalus.world.ParcelRevokeResult;
import com.daedalus.world.ParcelVerb;
import com.daedalus.world.PlaceNames;
import com.daedalus.world.Portal;
import com.daedalus.world.PortalResult;
import com.daedalus.world.stamp.StampOps;
import com.daedalus.world.stamp.StampRequest;
import com.daedalus.world.stamp.StampResult;
import com.daedalus.world.Trap;
import com.daedalus.world.TrapResult;
import com.daedalus.world.World;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Shared drive table for human REST and automation. Discovery lives on
 * {@link CapabilityRegistry}, not here.
 */
public final class WorldOps {

    /** First extra account on a grant with no actor string. Not a wallet. */
    public static final String GUEST_ACTOR = "alice";

    private WorldOps() {
    }

    public static Object drive(World world, String capability, BlockCoordinate at, BlockType type) {
        return drive(world, capability, at, type, null);
    }

    public static Object drive(World world, String capability, BlockCoordinate at, BlockType type,
                               MazeGrid maze) {
        return drive(world, capability, at, type, maze, null);
    }

    public static Object drive(World world, String capability, BlockCoordinate at, BlockType type,
                               MazeGrid maze, String mazeRef) {
        return drive(world, capability, at, type, maze, mazeRef, null);
    }

    public static Object drive(World world, String capability, BlockCoordinate at, BlockType type,
                               MazeGrid maze, String mazeRef, String actorId) {
        if (world == null || capability == null) {
            throw new IllegalArgumentException("World and capability are required");
        }
        Object out = switch (capability) {
            case "world.inspect" -> inspectWorld(world);
            case "chunk.inspect" -> inspectChunk(world, at);
            case "block.inspect" -> inspectBlock(world, at);
            case "block.place" -> placeBlock(world, at, type, mazeRef);
            case "block.remove" -> removeBlock(world, at, mazeRef);
            case "door.inspect" -> inspectDoor(world);
            case "door.open" -> openDoor(world, mazeRef);
            case "door.close" -> closeDoor(world, mazeRef);
            case "trap.inspect" -> inspectTrap(world);
            case "trap.arm" -> armTrap(world, mazeRef);
            case "trap.disarm" -> disarmTrap(world, mazeRef);
            case "portal.inspect" -> inspectPortal(world);
            case "portal.open" -> openPortal(world, mazeRef);
            case "portal.seal" -> sealPortal(world, mazeRef);
            case "npc.inspect" -> inspectNpc(world);
            case "npc.talk" -> talkNpc(world, mazeRef);
            case "npc.hush" -> hushNpc(world, mazeRef);
            case "parcel.lease" -> leaseParcel(world);
            case "parcel.release" -> releaseParcel(world);
            case "parcel.grant" -> grantParcel(world, at, mazeRef, actorId);
            case "parcel.deny" -> denyParcel(world, at, mazeRef, actorId);
            case "parcel.revoke" -> revokeParcel(world, at, mazeRef, actorId);
            case "parcel.forgive" -> forgiveParcel(world, at, mazeRef, actorId);
            case "stamp.apply" -> stampApply(world, at, maze, mazeRef, actorId);
            default -> throw new IllegalArgumentException("Unknown capability " + capability);
        };
        if (!(out instanceof Map)) {
            recordDrive(world, capability, out, actorFor(capability, mazeRef, actorId), at);
        }
        return out;
    }

    /**
     * Last driven capability and named result. Inspect stays off this line.
     */
    public static String driveLine(World world) {
        if (world == null) {
            return "";
        }
        return driveLine(world.lastDriveCapability(), world.lastDriveResult());
    }

    public static String driveLine(String capability, String result) {
        if (capability == null || capability.isBlank()) {
            return "";
        }
        if (result == null || result.isBlank()) {
            return capability;
        }
        return capability + " " + result;
    }

    public static String driveLine(DriveTrace.Step last) {
        if (last == null) {
            return "";
        }
        return driveLine(last.capability(), last.result());
    }

    /**
     * Account key that last drove a mutation. Empty until a mutation.
     * Never a wallet type.
     */
    public static String actorLine(World world) {
        if (world == null) {
            return "";
        }
        String actor = world.lastDriveActor();
        return actor == null ? "" : actor;
    }

    /**
     * Cube address of the last mutation. Empty until a mutation.
     */
    public static String atLine(World world) {
        if (world == null || world.lastDriveAt() == null) {
            return "";
        }
        BlockCoordinate at = world.lastDriveAt();
        return at.x() + "," + at.y() + "," + at.z();
    }

    private static void recordDrive(World world, String capability, Object result, String actor,
            BlockCoordinate at) {
        String rendered = result == null ? "null"
                : result instanceof StampResult stamp ? stamp.outcome()
                : result.toString();
        world.recordDrive(capability, rendered, actor, at);
    }

    private static String actorFor(String capability, String mazeRef, String actorId) {
        if ("parcel.grant".equals(capability) || "parcel.deny".equals(capability)
                || "parcel.revoke".equals(capability)
                || "parcel.forgive".equals(capability)) {
            return mazeRef == null || mazeRef.isBlank() ? GUEST_ACTOR : mazeRef.trim();
        }
        if ("stamp.apply".equals(capability)) {
            return actorId == null || actorId.isBlank() ? Parcel.SYSTEM_OWNER : actorId.trim();
        }
        if (mazeRef == null || mazeRef.isBlank()) {
            return Parcel.SYSTEM_OWNER;
        }
        return mazeRef.trim();
    }

    private static Map<String, Object> inspectWorld(World world) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", world.id().value());
        out.put("revision", world.revision().value());
        out.put("chunkCount", world.chunkCount());
        out.put("plots", world.parcels().size());
        out.put("street", streetLine(world));
        out.put("lot", streetLots(world));
        out.put("maze", streetMazes(world));
        out.put("lease", lastLeaseId(world));
        out.put("place", lastPlaceName(world));
        out.put("occupants", occupantsLine(world));
        out.put("stands", standsLine(world));
        out.put("acl", aclLine(world));
        out.put("drive", driveLine(world));
        out.put("driveActor", actorLine(world));
        out.put("driveAt", atLine(world));
        return out;
    }

    /**
     * Extra grants and denials on every plot. Owner stays implicit.
     * Actor ids are account keys — never a wallet type.
     */
    public static String aclLine(World world) {
        if (world == null) {
            return "";
        }
        List<String> rows = new ArrayList<>();
        for (Parcel parcel : world.parcels()) {
            String one = aclOf(world, parcel.id());
            if (!one.isEmpty()) {
                rows.add(one);
            }
        }
        return String.join(" · ", rows);
    }

    public static String aclAt(World world, BlockCoordinate at) {
        Parcel parcel = world == null || at == null ? null : world.parcelAt(at);
        return parcel == null ? "" : aclOf(world, parcel.id());
    }

    public static String aclOf(World world, ParcelId id) {
        if (world == null || id == null) {
            return "";
        }
        ParcelAcl acl = world.acl(id);
        List<String> rows = new ArrayList<>();
        for (ParcelAcl.Grant row : acl.grants()) {
            rows.add(row.actorId() + " " + verbName(row.verb()));
        }
        for (ParcelAcl.Grant row : acl.denials()) {
            rows.add("!" + row.actorId() + " " + verbName(row.verb()));
        }
        return String.join(" · ", rows);
    }

    private static String verbName(ParcelVerb verb) {
        return switch (verb) {
            case BLOCK_PLACE -> "block.place";
            case DOOR_OPEN -> "door.open";
            case STAMP_APPLY -> "stamp.apply";
            case TRAP_ARM -> "trap.arm";
            case PORTAL_OPEN -> "portal.open";
            case NPC_TALK -> "npc.talk";
        };
    }

    /**
     * Named parcel verbs. Blank is {@link ParcelVerb#BLOCK_PLACE}.
     * Unknown names stay unknown — not a silent default.
     */
    public static ParcelVerb parseVerb(String name) {
        if (name == null || name.isBlank()) {
            return ParcelVerb.BLOCK_PLACE;
        }
        return switch (name.trim()) {
            case "block.place" -> ParcelVerb.BLOCK_PLACE;
            case "door.open" -> ParcelVerb.DOOR_OPEN;
            case "stamp.apply" -> ParcelVerb.STAMP_APPLY;
            case "trap.arm" -> ParcelVerb.TRAP_ARM;
            case "portal.open" -> ParcelVerb.PORTAL_OPEN;
            case "npc.talk" -> ParcelVerb.NPC_TALK;
            default -> null;
        };
    }

    /** Occupancy objects that exist on this world. Not a chunk cut. */
    public static String occupantsLine(World world) {
        if (world == null) {
            return "";
        }
        List<String> rows = new ArrayList<>();
        if (world.door() != null) {
            rows.add("door");
        }
        if (world.trap() != null) {
            rows.add("trap");
        }
        if (world.portal() != null) {
            rows.add("portal");
        }
        if (world.npc() != null) {
            rows.add("npc");
        }
        return String.join(" · ", rows);
    }

    /**
     * Occupancy cells as kind + x,y,z. Occupants stay names-only.
     */
    public static String standsLine(World world) {
        if (world == null) {
            return "";
        }
        List<String> rows = new ArrayList<>();
        addStand(rows, "door", world.door() == null ? null : world.door().at());
        addStand(rows, "trap", world.trap() == null ? null : world.trap().at());
        addStand(rows, "portal", world.portal() == null ? null : world.portal().at());
        addStand(rows, "npc", world.npc() == null ? null : world.npc().at());
        return String.join(" · ", rows);
    }

    private static void addStand(List<String> rows, String kind, BlockCoordinate at) {
        if (at == null) {
            return;
        }
        rows.add(kind + " " + at.x() + "," + at.y() + "," + at.z());
    }

    private static Map<String, Object> inspectBlock(World world, BlockCoordinate at) {
        BlockCoordinate cell = at == null ? new BlockCoordinate(0, 0, 0) : at;
        BlockType type = world.get(cell);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("x", cell.x());
        out.put("y", cell.y());
        out.put("z", cell.z());
        out.put("type", type.name());
        out.put("place", placeAt(world, cell));
        out.put("lot", lotAt(world, cell));
        out.put("box", boxAt(world, cell));
        out.put("lease", leaseAt(world, cell));
        out.put("maze", mazeAt(world, cell));
        out.put("occupant", occupantAt(world, cell));
        out.put("acl", aclAt(world, cell));
        out.put("drive", driveOn(world, cell));
        out.put("driveActor", actorOn(world, cell));
        out.put("driveAt", atOn(world, cell));
        return out;
    }

    /**
     * Last driven result when {@code at} is that cube. Empty on every other cell.
     */
    public static String driveOn(World world, BlockCoordinate at) {
        if (world == null || at == null || !sameCell(world.lastDriveAt(), at)) {
            return "";
        }
        return driveLine(world);
    }

    /**
     * Account key that last drove a mutation on this cube. Empty otherwise.
     * Never a wallet type.
     */
    public static String actorOn(World world, BlockCoordinate at) {
        if (world == null || at == null || !sameCell(world.lastDriveAt(), at)) {
            return "";
        }
        return actorLine(world);
    }

    /**
     * Cube address of the last mutation when {@code at} is that cube.
     * Empty on every other cell.
     */
    public static String atOn(World world, BlockCoordinate at) {
        if (world == null || at == null || !sameCell(world.lastDriveAt(), at)) {
            return "";
        }
        return atLine(world);
    }

    public static String placeAt(World world, BlockCoordinate at) {
        Parcel parcel = world == null || at == null ? null : world.parcelAt(at);
        return parcel == null ? "" : parcel.placeName();
    }

    public static String lotAt(World world, BlockCoordinate at) {
        Parcel parcel = world == null || at == null ? null : world.parcelAt(at);
        return parcel == null ? "" : parcel.bounds().minX() + "," + parcel.bounds().minZ();
    }

    /** Inclusive slab AABB. Empty when the cube is off every plot. */
    public static String boxAt(World world, BlockCoordinate at) {
        Parcel parcel = world == null || at == null ? null : world.parcelAt(at);
        return parcel == null ? "" : boxLine(parcel.bounds());
    }

    /** Inclusive slab AABB as {@code min-max}. Empty when bounds is null. */
    public static String boxLine(ParcelBounds bounds) {
        if (bounds == null) {
            return "";
        }
        return bounds.minX() + "," + bounds.minY() + "," + bounds.minZ()
                + "-" + bounds.maxX() + "," + bounds.maxY() + "," + bounds.maxZ();
    }

    public static String leaseAt(World world, BlockCoordinate at) {
        Parcel parcel = world == null || at == null ? null : world.parcelAt(at);
        return parcel == null ? "" : parcel.leaseId();
    }

    public static String mazeAt(World world, BlockCoordinate at) {
        Parcel parcel = world == null || at == null ? null : world.parcelAt(at);
        return parcel == null ? "" : parcel.mazeRef();
    }

    /** Occupancy object on this cube. Empty when the cell is not door/trap/portal/npc. */
    public static String occupantAt(World world, BlockCoordinate at) {
        return world == null ? "" : world.occupantAt(at);
    }

    private static boolean sameCell(BlockCoordinate a, BlockCoordinate b) {
        return a != null && a.equals(b);
    }

    private static Map<String, Object> inspectChunk(World world, BlockCoordinate at) {
        BlockCoordinate cell = at == null ? new BlockCoordinate(0, 0, 0) : at;
        ChunkCoordinate cc = cell.chunk();
        Chunk chunk = world.chunk(cc);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("x", cc.x());
        out.put("y", cc.y());
        out.put("z", cc.z());
        out.put("present", chunk != null);
        out.put("plots", plotsInChunk(world, cc));
        out.put("street", streetInChunk(world, cc));
        out.put("lot", lotsInChunk(world, cc));
        out.put("occupants", occupantsInChunk(world, cc));
        out.put("stands", standsInChunk(world, cc));
        out.put("drive", driveInChunk(world, cc));
        out.put("driveActor", actorInChunk(world, cc));
        out.put("driveAt", atInChunk(world, cc));
        return out;
    }

    /**
     * Last driven result when that cube sits in this 16³. Empty otherwise.
     */
    public static String driveInChunk(World world, ChunkCoordinate cc) {
        if (world == null || cc == null || world.lastDriveAt() == null) {
            return "";
        }
        if (!chunkBox(cc).contains(world.lastDriveAt())) {
            return "";
        }
        return driveLine(world);
    }

    /**
     * Account key that last drove a mutation in this 16³. Empty otherwise.
     * Never a wallet type.
     */
    public static String actorInChunk(World world, ChunkCoordinate cc) {
        if (world == null || cc == null || world.lastDriveAt() == null) {
            return "";
        }
        if (!chunkBox(cc).contains(world.lastDriveAt())) {
            return "";
        }
        return actorLine(world);
    }

    /**
     * Cube address of the last mutation in this 16³. Empty otherwise.
     */
    public static String atInChunk(World world, ChunkCoordinate cc) {
        if (world == null || cc == null || world.lastDriveAt() == null) {
            return "";
        }
        if (!chunkBox(cc).contains(world.lastDriveAt())) {
            return "";
        }
        return atLine(world);
    }

    /** Occupancy objects whose cell sits in this 16³. Oldest object first. */
    public static String occupantsInChunk(World world, ChunkCoordinate cc) {
        if (world == null || cc == null) {
            return "";
        }
        ParcelBounds box = chunkBox(cc);
        List<String> rows = new ArrayList<>();
        addOccupantInBox(rows, "door", world.door() == null ? null : world.door().at(), box);
        addOccupantInBox(rows, "trap", world.trap() == null ? null : world.trap().at(), box);
        addOccupantInBox(rows, "portal", world.portal() == null ? null : world.portal().at(), box);
        addOccupantInBox(rows, "npc", world.npc() == null ? null : world.npc().at(), box);
        return String.join(" · ", rows);
    }

    private static void addOccupantInBox(List<String> rows, String kind, BlockCoordinate at,
                                         ParcelBounds box) {
        if (at != null && box.contains(at)) {
            rows.add(kind);
        }
    }

    /**
     * Occupancy cells in this 16³ as kind + x,y,z. Occupants stay names-only.
     */
    public static String standsInChunk(World world, ChunkCoordinate cc) {
        if (world == null || cc == null) {
            return "";
        }
        ParcelBounds box = chunkBox(cc);
        List<String> rows = new ArrayList<>();
        addStandInBox(rows, "door", world.door() == null ? null : world.door().at(), box);
        addStandInBox(rows, "trap", world.trap() == null ? null : world.trap().at(), box);
        addStandInBox(rows, "portal", world.portal() == null ? null : world.portal().at(), box);
        addStandInBox(rows, "npc", world.npc() == null ? null : world.npc().at(), box);
        return String.join(" · ", rows);
    }

    private static void addStandInBox(List<String> rows, String kind, BlockCoordinate at,
                                      ParcelBounds box) {
        if (at != null && box.contains(at)) {
            addStand(rows, kind, at);
        }
    }

    /** Inspired toponyms whose slab overlaps this 16³. Oldest first. */
    public static String streetInChunk(World world, ChunkCoordinate cc) {
        return joinInChunk(world, cc, true);
    }

    /** Slab origins whose AABB overlaps this 16³, as {@code x,z}. Oldest first. */
    public static String lotsInChunk(World world, ChunkCoordinate cc) {
        return joinInChunk(world, cc, false);
    }

    /** Plots whose AABB overlaps this 16³. */
    public static int plotsInChunk(World world, ChunkCoordinate cc) {
        if (world == null || cc == null) {
            return 0;
        }
        ParcelBounds box = chunkBox(cc);
        int n = 0;
        for (Parcel parcel : world.parcels()) {
            if (parcel != null && parcel.bounds().overlaps(box)) {
                n++;
            }
        }
        return n;
    }

    private static String joinInChunk(World world, ChunkCoordinate cc, boolean names) {
        if (world == null || cc == null) {
            return "";
        }
        ParcelBounds box = chunkBox(cc);
        List<String> rows = new ArrayList<>();
        for (Parcel parcel : world.parcels()) {
            if (parcel == null || !parcel.bounds().overlaps(box)) {
                continue;
            }
            if (names) {
                if (!parcel.placeName().isEmpty()) {
                    rows.add(parcel.placeName());
                }
            } else {
                rows.add(parcel.bounds().minX() + "," + parcel.bounds().minZ());
            }
        }
        return String.join(" · ", rows);
    }

    private static ParcelBounds chunkBox(ChunkCoordinate cc) {
        int size = Chunk.SIZE;
        int minX = cc.x() * size;
        int minY = cc.y() * size;
        int minZ = cc.z() * size;
        return new ParcelBounds(minX, minY, minZ,
                minX + size - 1, minY + size - 1, minZ + size - 1);
    }

    private static Map<String, Object> inspectDoor(World world) {
        Door door = world.door();
        if (door == null) {
            throw new IllegalStateException("This world has no door");
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", door.id());
        out.put("state", door.state().name());
        out.put("place", placeAt(world, door.at()));
        out.put("lot", lotAt(world, door.at()));
        out.put("box", boxAt(world, door.at()));
        out.put("maze", mazeAt(world, door.at()));
        out.put("acl", aclAt(world, door.at()));
        out.put("drive", driveOn(world, door.at()));
        out.put("driveActor", actorOn(world, door.at()));
        out.put("driveAt", atOn(world, door.at()));
        return out;
    }

    private static Map<String, Object> inspectTrap(World world) {
        Trap trap = world.trap();
        if (trap == null) {
            throw new IllegalStateException("This world has no trap");
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", trap.id());
        out.put("state", trap.state().name());
        out.put("place", placeAt(world, trap.at()));
        out.put("lot", lotAt(world, trap.at()));
        out.put("box", boxAt(world, trap.at()));
        out.put("maze", mazeAt(world, trap.at()));
        out.put("acl", aclAt(world, trap.at()));
        out.put("drive", driveOn(world, trap.at()));
        out.put("driveActor", actorOn(world, trap.at()));
        out.put("driveAt", atOn(world, trap.at()));
        return out;
    }

    public static DoorResult asDoorResult(Object value) {
        return (DoorResult) value;
    }

    /**
     * Open through {@link ParcelVerb#DOOR_OPEN}. Empty actor is the
     * system owner. A stranger needs a grant. DENIED leaves the door.
     */
    public static DoorResult openDoor(World world, String actorId) {
        if (world.door() == null) {
            throw new IllegalStateException("This world has no door");
        }
        String actor = actorId == null || actorId.isBlank() ? Parcel.SYSTEM_OWNER : actorId.trim();
        if (world.may(actor, ParcelVerb.DOOR_OPEN, world.door().at()) == ParcelAccess.DENIED) {
            return DoorResult.DENIED;
        }
        return world.openDoor();
    }

    /**
     * Close through the same {@link ParcelVerb#DOOR_OPEN} gate.
     * Empty actor is the system owner. DENIED leaves the door.
     */
    public static DoorResult closeDoor(World world, String actorId) {
        if (world.door() == null) {
            throw new IllegalStateException("This world has no door");
        }
        String actor = actorId == null || actorId.isBlank() ? Parcel.SYSTEM_OWNER : actorId.trim();
        if (world.may(actor, ParcelVerb.DOOR_OPEN, world.door().at()) == ParcelAccess.DENIED) {
            return DoorResult.DENIED;
        }
        return world.closeDoor();
    }

    /**
     * Arm through {@link ParcelVerb#TRAP_ARM}. Empty actor is the
     * system owner. A stranger needs a grant. DENIED leaves the trap.
     */
    public static TrapResult armTrap(World world, String actorId) {
        if (world.trap() == null) {
            throw new IllegalStateException("This world has no trap");
        }
        String actor = actorId == null || actorId.isBlank() ? Parcel.SYSTEM_OWNER : actorId.trim();
        if (world.may(actor, ParcelVerb.TRAP_ARM, world.trap().at()) == ParcelAccess.DENIED) {
            return TrapResult.DENIED;
        }
        return world.armTrap();
    }

    /**
     * Disarm through the same {@link ParcelVerb#TRAP_ARM} gate.
     * Empty actor is the system owner. DENIED leaves the trap.
     */
    public static TrapResult disarmTrap(World world, String actorId) {
        if (world.trap() == null) {
            throw new IllegalStateException("This world has no trap");
        }
        String actor = actorId == null || actorId.isBlank() ? Parcel.SYSTEM_OWNER : actorId.trim();
        if (world.may(actor, ParcelVerb.TRAP_ARM, world.trap().at()) == ParcelAccess.DENIED) {
            return TrapResult.DENIED;
        }
        return world.disarmTrap();
    }

    public static TrapResult asTrapResult(Object value) {
        return (TrapResult) value;
    }

    private static Map<String, Object> inspectPortal(World world) {
        Portal portal = world.portal();
        if (portal == null) {
            throw new IllegalStateException("This world has no portal");
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", portal.id());
        out.put("state", portal.state().name());
        out.put("place", placeAt(world, portal.at()));
        out.put("lot", lotAt(world, portal.at()));
        out.put("box", boxAt(world, portal.at()));
        out.put("maze", mazeAt(world, portal.at()));
        out.put("acl", aclAt(world, portal.at()));
        out.put("drive", driveOn(world, portal.at()));
        out.put("driveActor", actorOn(world, portal.at()));
        out.put("driveAt", atOn(world, portal.at()));
        return out;
    }

    /**
     * Open through {@link ParcelVerb#PORTAL_OPEN}. Empty actor is the
     * system owner. A stranger needs a grant. DENIED leaves the portal.
     */
    public static PortalResult openPortal(World world, String actorId) {
        if (world.portal() == null) {
            throw new IllegalStateException("This world has no portal");
        }
        String actor = actorId == null || actorId.isBlank() ? Parcel.SYSTEM_OWNER : actorId.trim();
        if (world.may(actor, ParcelVerb.PORTAL_OPEN, world.portal().at()) == ParcelAccess.DENIED) {
            return PortalResult.DENIED;
        }
        return world.openPortal();
    }

    /**
     * Seal through the same {@link ParcelVerb#PORTAL_OPEN} gate.
     * Empty actor is the system owner. DENIED leaves the portal.
     */
    public static PortalResult sealPortal(World world, String actorId) {
        if (world.portal() == null) {
            throw new IllegalStateException("This world has no portal");
        }
        String actor = actorId == null || actorId.isBlank() ? Parcel.SYSTEM_OWNER : actorId.trim();
        if (world.may(actor, ParcelVerb.PORTAL_OPEN, world.portal().at()) == ParcelAccess.DENIED) {
            return PortalResult.DENIED;
        }
        return world.sealPortal();
    }

    public static PortalResult asPortalResult(Object value) {
        return (PortalResult) value;
    }

    private static Map<String, Object> inspectNpc(World world) {
        Npc npc = world.npc();
        if (npc == null) {
            throw new IllegalStateException("This world has no npc");
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", npc.id());
        out.put("state", npc.state().name());
        out.put("place", placeAt(world, npc.at()));
        out.put("lot", lotAt(world, npc.at()));
        out.put("box", boxAt(world, npc.at()));
        out.put("acl", aclAt(world, npc.at()));
        out.put("drive", driveOn(world, npc.at()));
        out.put("driveActor", actorOn(world, npc.at()));
        out.put("driveAt", atOn(world, npc.at()));
        return out;
    }

    /**
     * Talk through {@link ParcelVerb#NPC_TALK}. Empty actor is the
     * system owner. A stranger needs a grant. DENIED leaves the NPC.
     */
    public static NpcResult talkNpc(World world, String actorId) {
        if (world.npc() == null) {
            throw new IllegalStateException("This world has no npc");
        }
        String actor = actorId == null || actorId.isBlank() ? Parcel.SYSTEM_OWNER : actorId.trim();
        if (world.may(actor, ParcelVerb.NPC_TALK, world.npc().at()) == ParcelAccess.DENIED) {
            return NpcResult.DENIED;
        }
        return world.talkNpc();
    }

    /**
     * Hush through the same {@link ParcelVerb#NPC_TALK} gate.
     * Empty actor is the system owner. DENIED leaves the NPC.
     */
    public static NpcResult hushNpc(World world, String actorId) {
        if (world.npc() == null) {
            throw new IllegalStateException("This world has no npc");
        }
        String actor = actorId == null || actorId.isBlank() ? Parcel.SYSTEM_OWNER : actorId.trim();
        if (world.may(actor, ParcelVerb.NPC_TALK, world.npc().at()) == ParcelAccess.DENIED) {
            return NpcResult.DENIED;
        }
        return world.hushNpc();
    }

    public static NpcResult asNpcResult(Object value) {
        return (NpcResult) value;
    }

    /**
     * Vacate the first leased slab. Empty street is NO_PARCEL.
     * Every plot already vacant is NOT_LEASED.
     */
    public static ParcelReleaseResult releaseParcel(World world) {
        if (world == null || world.parcels().isEmpty()) {
            return ParcelReleaseResult.NO_PARCEL;
        }
        for (Parcel parcel : world.parcels()) {
            if (parcel != null && !parcel.leaseId().isEmpty()) {
                return world.releaseParcel(parcel.id());
            }
        }
        return ParcelReleaseResult.NOT_LEASED;
    }

    public static ParcelReleaseResult asReleaseResult(Object value) {
        return (ParcelReleaseResult) value;
    }

    private static ParcelLeaseResult leaseParcel(World world) {
        if (world.parcels().isEmpty()) {
            return ParcelLeaseResult.NO_PARCEL;
        }
        for (Parcel parcel : world.parcels()) {
            if (parcel.leaseId().isEmpty()) {
                return world.leaseParcel(parcel.id(), Parcel.SYSTEM_TENANT);
            }
        }
        return world.leaseParcel(world.parcels().get(0).id(), Parcel.SYSTEM_TENANT);
    }

    /**
     * Extra grant on the slab under {@code at}, or the first plot.
     * Empty actor becomes {@link #GUEST_ACTOR}. Empty verb is block.place.
     */
    public static ParcelGrantResult grantParcel(World world, BlockCoordinate at, String actorId) {
        return grantParcel(world, at, actorId, null);
    }

    public static ParcelGrantResult grantParcel(World world, BlockCoordinate at, String actorId,
            String verbName) {
        if (world == null || world.parcels().isEmpty()) {
            return ParcelGrantResult.NO_PARCEL;
        }
        ParcelVerb verb = parseVerb(verbName);
        if (verb == null) {
            return ParcelGrantResult.UNKNOWN_VERB;
        }
        String actor = actorId == null || actorId.isBlank() ? GUEST_ACTOR : actorId.trim();
        Parcel parcel = at == null ? null : world.parcelAt(at);
        if (parcel == null) {
            parcel = world.parcels().get(0);
        }
        if (world.acl(parcel.id()).grants(actor, verb)) {
            return ParcelGrantResult.ALREADY_GRANTED;
        }
        world.grant(parcel.id(), actor, verb);
        return ParcelGrantResult.GRANTED;
    }

    public static ParcelGrantResult asGrantResult(Object value) {
        return (ParcelGrantResult) value;
    }

    /**
     * Extra deny on the slab under {@code at}, or the first plot.
     * Empty actor becomes {@link #GUEST_ACTOR}. Empty verb is block.place.
     * Deny wins.
     */
    public static ParcelDenyResult denyParcel(World world, BlockCoordinate at, String actorId) {
        return denyParcel(world, at, actorId, null);
    }

    public static ParcelDenyResult denyParcel(World world, BlockCoordinate at, String actorId,
            String verbName) {
        if (world == null || world.parcels().isEmpty()) {
            return ParcelDenyResult.NO_PARCEL;
        }
        ParcelVerb verb = parseVerb(verbName);
        if (verb == null) {
            return ParcelDenyResult.UNKNOWN_VERB;
        }
        String actor = actorId == null || actorId.isBlank() ? GUEST_ACTOR : actorId.trim();
        Parcel parcel = at == null ? null : world.parcelAt(at);
        if (parcel == null) {
            parcel = world.parcels().get(0);
        }
        if (world.acl(parcel.id()).denies(actor, verb)) {
            return ParcelDenyResult.ALREADY_DENIED;
        }
        world.deny(parcel.id(), actor, verb);
        return ParcelDenyResult.DENIED;
    }

    public static ParcelDenyResult asDenyResult(Object value) {
        return (ParcelDenyResult) value;
    }

    /**
     * Drop an extra grant on the slab under {@code at}, or the first plot.
     * Empty actor becomes {@link #GUEST_ACTOR}. Empty verb is block.place.
     * Denials stay.
     */
    public static ParcelRevokeResult revokeParcel(World world, BlockCoordinate at, String actorId) {
        return revokeParcel(world, at, actorId, null);
    }

    public static ParcelRevokeResult revokeParcel(World world, BlockCoordinate at, String actorId,
            String verbName) {
        if (world == null || world.parcels().isEmpty()) {
            return ParcelRevokeResult.NO_PARCEL;
        }
        ParcelVerb verb = parseVerb(verbName);
        if (verb == null) {
            return ParcelRevokeResult.UNKNOWN_VERB;
        }
        String actor = actorId == null || actorId.isBlank() ? GUEST_ACTOR : actorId.trim();
        Parcel parcel = at == null ? null : world.parcelAt(at);
        if (parcel == null) {
            parcel = world.parcels().get(0);
        }
        if (!world.acl(parcel.id()).grants(actor, verb)) {
            return ParcelRevokeResult.NOT_GRANTED;
        }
        world.revoke(parcel.id(), actor, verb);
        return ParcelRevokeResult.REVOKED;
    }

    public static ParcelRevokeResult asRevokeResult(Object value) {
        return (ParcelRevokeResult) value;
    }

    /**
     * Drop an extra denial on the slab under {@code at}, or the first plot.
     * Empty actor becomes {@link #GUEST_ACTOR}. Empty verb is block.place.
     * Grants stay.
     */
    public static ParcelForgiveResult forgiveParcel(World world, BlockCoordinate at,
            String actorId) {
        return forgiveParcel(world, at, actorId, null);
    }

    public static ParcelForgiveResult forgiveParcel(World world, BlockCoordinate at,
            String actorId, String verbName) {
        if (world == null || world.parcels().isEmpty()) {
            return ParcelForgiveResult.NO_PARCEL;
        }
        ParcelVerb verb = parseVerb(verbName);
        if (verb == null) {
            return ParcelForgiveResult.UNKNOWN_VERB;
        }
        String actor = actorId == null || actorId.isBlank() ? GUEST_ACTOR : actorId.trim();
        Parcel parcel = at == null ? null : world.parcelAt(at);
        if (parcel == null) {
            parcel = world.parcels().get(0);
        }
        if (!world.acl(parcel.id()).denies(actor, verb)) {
            return ParcelForgiveResult.NOT_DENIED;
        }
        world.forgive(parcel.id(), actor, verb);
        return ParcelForgiveResult.FORGIVEN;
    }

    public static ParcelForgiveResult asForgiveResult(Object value) {
        return (ParcelForgiveResult) value;
    }

    /**
     * Place through {@link World#may}. Empty actor is the system owner so
     * existing owner recipes stay allowed. A stranger needs a grant.
     */
    public static Object placeBlock(World world, BlockCoordinate at, BlockType type,
            String actorId) {
        String actor = actorId == null || actorId.isBlank() ? Parcel.SYSTEM_OWNER : actorId.trim();
        if (world.may(actor, ParcelVerb.BLOCK_PLACE, at) == ParcelAccess.DENIED) {
            return BlockPlaceResult.DENIED;
        }
        return world.place(at, type == null ? BlockType.STONE : type);
    }

    /**
     * Remove through the same {@link ParcelVerb#BLOCK_PLACE} gate.
     * Empty actor is the system owner.
     */
    public static Object removeBlock(World world, BlockCoordinate at, String actorId) {
        String actor = actorId == null || actorId.isBlank() ? Parcel.SYSTEM_OWNER : actorId.trim();
        if (world.may(actor, ParcelVerb.BLOCK_PLACE, at) == ParcelAccess.DENIED) {
            return BlockPlaceResult.DENIED;
        }
        return world.remove(at);
    }

    /** Newest non-empty lease string on the street. Not a wallet. */
    public static String lastLeaseId(World world) {
        if (world == null) {
            return "";
        }
        String found = "";
        for (Parcel parcel : world.parcels()) {
            if (parcel != null && !parcel.leaseId().isEmpty()) {
                found = parcel.leaseId();
            }
        }
        return found;
    }

    /** All inspired toponyms on the street, oldest first. Not GIS. */
    public static String streetLine(World world) {
        if (world == null) {
            return "";
        }
        List<String> names = new ArrayList<>();
        for (Parcel parcel : world.parcels()) {
            if (parcel != null && !parcel.placeName().isEmpty()) {
                names.add(parcel.placeName());
            }
        }
        return String.join(" · ", names);
    }

    /** All slab origins as {@code x,z}, oldest first. */
    public static String streetLots(World world) {
        if (world == null) {
            return "";
        }
        List<String> lots = new ArrayList<>();
        for (Parcel parcel : world.parcels()) {
            if (parcel != null) {
                lots.add(parcel.bounds().minX() + "," + parcel.bounds().minZ());
            }
        }
        return String.join(" · ", lots);
    }

    /** Newest slab origin as {@code x,z}. Empty when the street has no plots. */
    public static String lastLot(World world) {
        if (world == null || world.parcels().isEmpty()) {
            return "";
        }
        Parcel last = world.parcels().get(world.parcels().size() - 1);
        return last.bounds().minX() + "," + last.bounds().minZ();
    }

    /** All lab maze ids on the street, oldest first. Not a wallet. */
    public static String streetMazes(World world) {
        if (world == null) {
            return "";
        }
        List<String> refs = new ArrayList<>();
        for (Parcel parcel : world.parcels()) {
            if (parcel != null && !parcel.mazeRef().isEmpty()) {
                refs.add(parcel.mazeRef());
            }
        }
        return String.join(" · ", refs);
    }

    /** Newest inspired toponym on the street. Not GIS. */
    public static String lastPlaceName(World world) {
        if (world == null) {
            return "";
        }
        String found = "";
        for (Parcel parcel : world.parcels()) {
            if (parcel != null && !parcel.placeName().isEmpty()) {
                found = parcel.placeName();
            }
        }
        return found;
    }

    public static ParcelLeaseResult asLeaseResult(Object value) {
        return (ParcelLeaseResult) value;
    }

    private static StampResult stampApply(World world, BlockCoordinate at, MazeGrid maze,
                                         String mazeRef, String actorId) {
        BlockCoordinate origin = at == null ? new BlockCoordinate(0, 0, 0) : at;
        String actor = actorId == null || actorId.isBlank() ? Parcel.SYSTEM_OWNER : actorId.trim();
        if (world.may(actor, ParcelVerb.STAMP_APPLY, origin) == ParcelAccess.DENIED) {
            return StampResult.denied(world.revision());
        }
        MazeGrid slab = maze == null ? new MazeGrid(1, 1) : maze;
        StampResult result = StampOps.apply(world, new StampRequest(world.id(), origin,
                slab, origin.y(), 1));
        if (result.ok() && result.parcelId() != null) {
            if (mazeRef != null && !mazeRef.isBlank()) {
                world.bindMaze(result.parcelId(), mazeRef);
            }
            nameStampedPlot(world, result.parcelId(), mazeRef);
        }
        return result;
    }

    public static StampResult asStampResult(Object value) {
        return (StampResult) value;
    }

    private static void nameStampedPlot(World world, ParcelId id, String mazeRef) {
        Set<String> taken = new HashSet<>();
        for (Parcel parcel : world.parcels()) {
            if (parcel != null && !parcel.placeName().isEmpty()) {
                taken.add(parcel.placeName());
            }
        }
        String key = mazeRef != null && !mazeRef.isBlank() ? mazeRef.trim() : id.value();
        world.nameParcel(id, PlaceNames.of(key, taken));
    }
}
