// SPDX-License-Identifier: MIT

package com.daedalus.world.auto;

import com.daedalus.engine.MazeGrid;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.Chunk;
import com.daedalus.world.ChunkCoordinate;
import com.daedalus.world.Door;
import com.daedalus.world.DoorResult;
import com.daedalus.world.Npc;
import com.daedalus.world.NpcResult;
import com.daedalus.world.Parcel;
import com.daedalus.world.ParcelId;
import com.daedalus.world.ParcelLeaseResult;
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
        if (world == null || capability == null) {
            throw new IllegalArgumentException("World and capability are required");
        }
        return switch (capability) {
            case "world.inspect" -> inspectWorld(world);
            case "chunk.inspect" -> inspectChunk(world, at);
            case "block.inspect" -> inspectBlock(world, at);
            case "block.place" -> world.place(at, type == null ? BlockType.STONE : type);
            case "block.remove" -> world.remove(at);
            case "door.inspect" -> inspectDoor(world);
            case "door.open" -> world.openDoor();
            case "door.close" -> world.closeDoor();
            case "trap.inspect" -> inspectTrap(world);
            case "trap.arm" -> world.armTrap();
            case "trap.disarm" -> world.disarmTrap();
            case "portal.inspect" -> inspectPortal(world);
            case "portal.open" -> world.openPortal();
            case "portal.seal" -> world.sealPortal();
            case "npc.inspect" -> inspectNpc(world);
            case "npc.talk" -> world.talkNpc();
            case "npc.hush" -> world.hushNpc();
            case "parcel.lease" -> leaseParcel(world);
            case "stamp.apply" -> stampApply(world, at, maze, mazeRef);
            default -> throw new IllegalArgumentException("Unknown capability " + capability);
        };
    }

    private static Map<String, Object> inspectWorld(World world) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", world.id().value());
        out.put("revision", world.revision().value());
        out.put("chunkCount", world.chunkCount());
        return out;
    }

    private static Map<String, Object> inspectBlock(World world, BlockCoordinate at) {
        BlockCoordinate cell = at == null ? new BlockCoordinate(0, 0, 0) : at;
        BlockType type = world.get(cell);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("x", cell.x());
        out.put("y", cell.y());
        out.put("z", cell.z());
        out.put("type", type.name());
        return out;
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
        return out;
    }

    private static Map<String, Object> inspectDoor(World world) {
        Door door = world.door();
        if (door == null) {
            throw new IllegalStateException("This world has no door");
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", door.id());
        out.put("state", door.state().name());
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
        return out;
    }

    public static DoorResult asDoorResult(Object value) {
        return (DoorResult) value;
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
        return out;
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
        return out;
    }

    public static NpcResult asNpcResult(Object value) {
        return (NpcResult) value;
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

    /** Newest slab origin as {@code x,z}. Empty when the street has no plots. */
    public static String lastLot(World world) {
        if (world == null || world.parcels().isEmpty()) {
            return "";
        }
        Parcel last = world.parcels().get(world.parcels().size() - 1);
        return last.bounds().minX() + "," + last.bounds().minZ();
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
                                         String mazeRef) {
        BlockCoordinate origin = at == null ? new BlockCoordinate(0, 0, 0) : at;
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
