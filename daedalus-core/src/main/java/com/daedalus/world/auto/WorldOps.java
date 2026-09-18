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
import com.daedalus.world.ParcelBounds;
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
        out.put("plots", world.parcels().size());
        out.put("street", streetLine(world));
        out.put("lot", streetLots(world));
        out.put("maze", streetMazes(world));
        out.put("lease", lastLeaseId(world));
        out.put("place", lastPlaceName(world));
        out.put("occupants", occupantsLine(world));
        return out;
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
        out.put("lease", leaseAt(world, cell));
        out.put("maze", mazeAt(world, cell));
        out.put("occupant", occupantAt(world, cell));
        return out;
    }

    public static String placeAt(World world, BlockCoordinate at) {
        Parcel parcel = world == null || at == null ? null : world.parcelAt(at);
        return parcel == null ? "" : parcel.placeName();
    }

    public static String lotAt(World world, BlockCoordinate at) {
        Parcel parcel = world == null || at == null ? null : world.parcelAt(at);
        return parcel == null ? "" : parcel.bounds().minX() + "," + parcel.bounds().minZ();
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
        if (world == null || at == null) {
            return "";
        }
        if (sameCell(world.door() == null ? null : world.door().at(), at)) {
            return "door";
        }
        if (sameCell(world.trap() == null ? null : world.trap().at(), at)) {
            return "trap";
        }
        if (sameCell(world.portal() == null ? null : world.portal().at(), at)) {
            return "portal";
        }
        if (sameCell(world.npc() == null ? null : world.npc().at(), at)) {
            return "npc";
        }
        return "";
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
        return out;
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
        out.put("place", placeAt(world, portal.at()));
        out.put("lot", lotAt(world, portal.at()));
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
        out.put("place", placeAt(world, npc.at()));
        out.put("lot", lotAt(world, npc.at()));
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
