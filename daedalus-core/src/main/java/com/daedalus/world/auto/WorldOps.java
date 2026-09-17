// SPDX-License-Identifier: MIT

package com.daedalus.world.auto;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.Chunk;
import com.daedalus.world.ChunkCoordinate;
import com.daedalus.world.Door;
import com.daedalus.world.DoorResult;
import com.daedalus.world.Portal;
import com.daedalus.world.PortalResult;
import com.daedalus.world.Trap;
import com.daedalus.world.TrapResult;
import com.daedalus.world.World;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Shared drive table for human REST and automation. Discovery lives on
 * {@link CapabilityRegistry}, not here.
 */
public final class WorldOps {

    private WorldOps() {
    }

    public static Object drive(World world, String capability, BlockCoordinate at, BlockType type) {
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
}
