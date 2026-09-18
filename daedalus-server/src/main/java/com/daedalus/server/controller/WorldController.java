// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.BlockInspectResponse;
import com.daedalus.api.dto.BlockMutationResponse;
import com.daedalus.api.dto.ChunkInspectResponse;
import com.daedalus.api.dto.DoorInspectResponse;
import com.daedalus.api.dto.DoorMutationResponse;
import com.daedalus.api.dto.NpcInspectResponse;
import com.daedalus.api.dto.NpcMutationResponse;
import com.daedalus.api.dto.ParcelLeaseResponse;
import com.daedalus.api.dto.PlaceBlockRequest;
import com.daedalus.api.dto.PortalInspectResponse;
import com.daedalus.api.dto.PortalMutationResponse;
import com.daedalus.api.dto.StampMutationResponse;
import com.daedalus.api.dto.StampWorldRequest;
import com.daedalus.api.dto.TrapInspectResponse;
import com.daedalus.api.dto.TrapMutationResponse;
import com.daedalus.api.dto.WorldCapabilitiesResponse;
import com.daedalus.api.dto.WorldInspectResponse;
import com.daedalus.api.dto.WorldObserveResponse;
import com.daedalus.api.dto.WorldParcelRow;
import com.daedalus.api.dto.WorldParcelsResponse;
import com.daedalus.api.dto.WorldTraceResponse;
import com.daedalus.api.dto.WorldTraceStepResponse;
import com.daedalus.world.auto.DriveTrace;
import com.daedalus.world.auto.Observation;
import com.daedalus.plugin.runtime.PluginRegistry;
import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.engine.MazeGrid;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.server.service.WorldService;
import com.daedalus.world.auto.WorldOps;
import com.daedalus.world.auto.WorldZeroCapabilities;
import com.daedalus.server.web.ResourceNotFoundException;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.Chunk;
import com.daedalus.world.ChunkCoordinate;
import com.daedalus.world.Door;
import com.daedalus.world.DoorResult;
import com.daedalus.world.Npc;
import com.daedalus.world.NpcResult;
import com.daedalus.world.Parcel;
import com.daedalus.world.ParcelLeaseResult;
import com.daedalus.world.Portal;
import com.daedalus.world.PortalResult;
import com.daedalus.world.stamp.StampResult;
import com.daedalus.world.Trap;
import com.daedalus.world.TrapResult;
import com.daedalus.world.World;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * Persistent voxel volume. Maze routes stay on {@code /api/v1/maze/**}.
 */
@RestController
@RequestMapping("/api/v1")
@Tag(name = "World", description = "Inspect, place, and remove cubes in world-zero.")
@Validated
public class WorldController {

    private final WorldService worlds;
    private final PluginRegistry plugins;
    private final MazeGenerationService mazes;

    public WorldController(WorldService worlds, PluginRegistry plugins,
            MazeGenerationService mazes) {
        this.worlds = worlds;
        this.plugins = plugins;
        this.mazes = mazes;
    }

    @GetMapping("/world/{id}")
    @Operation(summary = "Inspect a world: id, revision, street directory.")
    public ResponseEntity<WorldInspectResponse> inspect(@PathVariable String id) {
        World world = mounted(id);
        return ResponseEntity.ok(new WorldInspectResponse(
                world.id().value(), world.revision().value(), world.chunkCount(),
                world.parcels().size(), WorldOps.streetLine(world), WorldOps.streetLots(world),
                WorldOps.streetMazes(world), WorldOps.lastLeaseId(world),
                WorldOps.lastPlaceName(world), WorldOps.occupantsLine(world),
                WorldOps.standsLine(world), WorldOps.aclLine(world)));
    }

    @GetMapping("/world/{id}/parcels")
    @Operation(summary = "Inspect parcels and their place names.")
    public ResponseEntity<WorldParcelsResponse> inspectParcels(@PathVariable String id) {
        World world = mounted(id);
        List<WorldParcelRow> rows = new ArrayList<>();
        for (Parcel parcel : world.parcels()) {
            rows.add(new WorldParcelRow(
                    parcel.id().value(), parcel.ownerId(), parcel.placeName(),
                    parcel.leaseId(), parcel.mazeRef(),
                    parcel.bounds().minX(), parcel.bounds().minZ(), parcel.version()));
        }
        return ResponseEntity.ok(new WorldParcelsResponse(world.id().value(), rows));
    }

    @PostMapping("/world/{id}/parcels/lease")
    @Operation(summary = "Lease the first vacant parcel as tenant-zero. NO_PARCEL is a result, not silence.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<ParcelLeaseResponse> leaseParcel(@PathVariable String id) {
        mounted(id);
        ParcelLeaseResult result = worlds.leaseParcel(id);
        World world = mounted(id);
        return ResponseEntity.ok(new ParcelLeaseResponse(
                result.name(), WorldOps.lastLeaseId(world), world.revision().value()));
    }

    @PostMapping("/world/{id}/stamp")
    @Operation(summary = "Stamp a maze slab. Optional mazeId from the lab cache. Overlap is a named result.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<StampMutationResponse> stamp(
            @PathVariable String id, @Valid @RequestBody StampWorldRequest body) {
        mounted(id);
        BlockCoordinate at = new BlockCoordinate(body.x(), body.y(), body.z());
        UUID mazeId = mazeKey(body.mazeId());
        StampResult result = worlds.stamp(id, at, mazeId == null ? null : mazeGrid(mazeId), mazeId,
                Boolean.TRUE.equals(body.next()));
        String parcelId = result.parcelId() == null ? "" : result.parcelId().value();
        int minX = 0;
        int maxX = 0;
        int minZ = 0;
        int maxZ = 0;
        if (result.bounds() != null) {
            minX = result.bounds().minX();
            maxX = result.bounds().maxX();
            minZ = result.bounds().minZ();
            maxZ = result.bounds().maxZ();
        }
        return ResponseEntity.ok(new StampMutationResponse(
                result.ok(), result.outcome(), parcelId, result.revision().value(),
                minX, maxX, minZ, maxZ));
    }

    @GetMapping("/world/{id}/capabilities")
    @Operation(summary = "Discover world capabilities. Not the drive script.")
    public ResponseEntity<WorldCapabilitiesResponse> capabilities(@PathVariable String id) {
        mounted(id);
        return ResponseEntity.ok(new WorldCapabilitiesResponse(
                id, new ArrayList<>(WorldZeroCapabilities.registry(
                        plugins.worldCapabilities()).discover())));
    }

    @GetMapping("/world/{id}/observe")
    @Operation(summary = "Observe a cube and the door. Does not bump revision.")
    public ResponseEntity<WorldObserveResponse> observe(
            @PathVariable String id,
            @RequestParam @NotNull Integer x,
            @RequestParam @NotNull Integer y,
            @RequestParam @NotNull Integer z) {
        mounted(id);
        Observation seen = worlds.observe(id, x, y, z);
        return ResponseEntity.ok(new WorldObserveResponse(
                seen.worldId(), seen.revision(), seen.x(), seen.y(), seen.z(),
                seen.blockType(), seen.doorState(), seen.place(), seen.lot(),
                seen.occupant(), seen.acl()));
    }

    @GetMapping("/world/{id}/trace")
    @Operation(summary = "Trace driven world ops. Discover does not write this.")
    public ResponseEntity<WorldTraceResponse> trace(@PathVariable String id) {
        mounted(id);
        List<WorldTraceStepResponse> steps = new ArrayList<>();
        for (DriveTrace.Step step : worlds.trace(id)) {
            steps.add(new WorldTraceStepResponse(
                    step.capability(), step.result(), step.revisionAfter()));
        }
        return ResponseEntity.ok(new WorldTraceResponse(id, steps));
    }

    @GetMapping("/world/{id}/block")
    @Operation(summary = "Inspect one cube.")
    public ResponseEntity<BlockInspectResponse> inspectBlock(
            @PathVariable String id,
            @RequestParam @NotNull Integer x,
            @RequestParam @NotNull Integer y,
            @RequestParam @NotNull Integer z) {
        World world = mounted(id);
        BlockCoordinate at = new BlockCoordinate(x, y, z);
        BlockType type = world.get(at);
        return ResponseEntity.ok(new BlockInspectResponse(
                x, y, z, type.name(), type.solid(),
                WorldOps.placeAt(world, at), WorldOps.lotAt(world, at),
                WorldOps.leaseAt(world, at), WorldOps.mazeAt(world, at),
                WorldOps.occupantAt(world, at), WorldOps.aclAt(world, at)));
    }

    @GetMapping("/world/{id}/chunk")
    @Operation(summary = "Inspect one 16³ chunk.")
    public ResponseEntity<ChunkInspectResponse> inspectChunk(
            @PathVariable String id,
            @RequestParam @NotNull Integer x,
            @RequestParam @NotNull Integer y,
            @RequestParam @NotNull Integer z) {
        World world = mounted(id);
        Chunk chunk = worlds.inspectChunk(id, x, y, z);
        ChunkCoordinate cc = new ChunkCoordinate(x, y, z);
        int plots = WorldOps.plotsInChunk(world, cc);
        String street = WorldOps.streetInChunk(world, cc);
        String lot = WorldOps.lotsInChunk(world, cc);
        String occupants = WorldOps.occupantsInChunk(world, cc);
        String stands = WorldOps.standsInChunk(world, cc);
        if (chunk == null) {
            return ResponseEntity.ok(new ChunkInspectResponse(
                    x, y, z, false, null, 0, plots, street, lot, occupants, stands));
        }
        return ResponseEntity.ok(new ChunkInspectResponse(
                x, y, z, true, chunk.revision(), chunk.occupied(), plots, street, lot,
                occupants, stands));
    }

    @PutMapping("/world/{id}/block")
    @Operation(summary = "Place a cube. AIR is remove.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<BlockMutationResponse> place(
            @PathVariable String id, @Valid @RequestBody PlaceBlockRequest body) {
        mounted(id);
        BlockType type = parseType(body.type());
        BlockType previous = worlds.place(id, body.x(), body.y(), body.z(), type);
        World world = mounted(id);
        return ResponseEntity.ok(new BlockMutationResponse(
                body.x(), body.y(), body.z(), previous.name(),
                world.get(new BlockCoordinate(body.x(), body.y(), body.z())).name(),
                world.revision().value()));
    }

    @DeleteMapping("/world/{id}/block")
    @Operation(summary = "Remove a cube (set AIR).")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<BlockMutationResponse> remove(
            @PathVariable String id,
            @RequestParam @NotNull Integer x,
            @RequestParam @NotNull Integer y,
            @RequestParam @NotNull Integer z) {
        mounted(id);
        BlockType previous = worlds.remove(id, x, y, z);
        World world = mounted(id);
        return ResponseEntity.ok(new BlockMutationResponse(
                x, y, z, previous.name(), BlockType.AIR.name(), world.revision().value()));
    }

    @GetMapping("/world/{id}/door")
    @Operation(summary = "Inspect the programmable door.")
    public ResponseEntity<DoorInspectResponse> inspectDoor(@PathVariable String id) {
        World world = mounted(id);
        Door door = worlds.inspectDoor(id);
        if (door == null) {
            throw ResourceNotFoundException.world(id);
        }
        return ResponseEntity.ok(new DoorInspectResponse(
                door.id(), door.worldId().value(),
                door.at().x(), door.at().y(), door.at().z(), door.state().name(),
                WorldOps.placeAt(world, door.at()), WorldOps.lotAt(world, door.at()),
                WorldOps.aclAt(world, door.at())));
    }

    @PostMapping("/world/{id}/door/open")
    @Operation(summary = "Open the door. ALREADY_OPEN is a result, not silence.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<DoorMutationResponse> openDoor(@PathVariable String id) {
        mounted(id);
        DoorResult result = worlds.openDoor(id);
        Door door = worlds.inspectDoor(id);
        World world = mounted(id);
        return ResponseEntity.ok(new DoorMutationResponse(
                door.id(), door.state().name(), result.name(), world.revision().value()));
    }

    @PostMapping("/world/{id}/door/close")
    @Operation(summary = "Close the door. ALREADY_CLOSED is a result, not silence.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<DoorMutationResponse> closeDoor(@PathVariable String id) {
        mounted(id);
        DoorResult result = worlds.closeDoor(id);
        Door door = worlds.inspectDoor(id);
        World world = mounted(id);
        return ResponseEntity.ok(new DoorMutationResponse(
                door.id(), door.state().name(), result.name(), world.revision().value()));
    }

    @GetMapping("/world/{id}/trap")
    @Operation(summary = "Inspect the programmable trap.")
    public ResponseEntity<TrapInspectResponse> inspectTrap(@PathVariable String id) {
        World world = mounted(id);
        Trap trap = worlds.inspectTrap(id);
        if (trap == null) {
            throw ResourceNotFoundException.world(id);
        }
        return ResponseEntity.ok(new TrapInspectResponse(
                trap.id(), trap.worldId().value(),
                trap.at().x(), trap.at().y(), trap.at().z(), trap.state().name(),
                WorldOps.placeAt(world, trap.at()), WorldOps.lotAt(world, trap.at()),
                WorldOps.aclAt(world, trap.at())));
    }

    @PostMapping("/world/{id}/trap/arm")
    @Operation(summary = "Arm the trap. ALREADY_ARMED is a result, not silence.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<TrapMutationResponse> armTrap(@PathVariable String id) {
        mounted(id);
        TrapResult result = worlds.armTrap(id);
        Trap trap = worlds.inspectTrap(id);
        World world = mounted(id);
        return ResponseEntity.ok(new TrapMutationResponse(
                trap.id(), trap.state().name(), result.name(), world.revision().value()));
    }

    @PostMapping("/world/{id}/trap/disarm")
    @Operation(summary = "Disarm the trap. ALREADY_DISARMED is a result, not silence.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<TrapMutationResponse> disarmTrap(@PathVariable String id) {
        mounted(id);
        TrapResult result = worlds.disarmTrap(id);
        Trap trap = worlds.inspectTrap(id);
        World world = mounted(id);
        return ResponseEntity.ok(new TrapMutationResponse(
                trap.id(), trap.state().name(), result.name(), world.revision().value()));
    }

    @GetMapping("/world/{id}/portal")
    @Operation(summary = "Inspect the programmable portal.")
    public ResponseEntity<PortalInspectResponse> inspectPortal(@PathVariable String id) {
        World world = mounted(id);
        Portal portal = worlds.inspectPortal(id);
        if (portal == null) {
            throw ResourceNotFoundException.world(id);
        }
        return ResponseEntity.ok(new PortalInspectResponse(
                portal.id(), portal.worldId().value(),
                portal.at().x(), portal.at().y(), portal.at().z(), portal.state().name(),
                WorldOps.placeAt(world, portal.at()), WorldOps.lotAt(world, portal.at())));
    }

    @PostMapping("/world/{id}/portal/open")
    @Operation(summary = "Open the portal. ALREADY_OPEN is a result, not silence.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<PortalMutationResponse> openPortal(@PathVariable String id) {
        mounted(id);
        PortalResult result = worlds.openPortal(id);
        Portal portal = worlds.inspectPortal(id);
        World world = mounted(id);
        return ResponseEntity.ok(new PortalMutationResponse(
                portal.id(), portal.state().name(), result.name(), world.revision().value()));
    }

    @PostMapping("/world/{id}/portal/seal")
    @Operation(summary = "Seal the portal. ALREADY_SEALED is a result, not silence.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<PortalMutationResponse> sealPortal(@PathVariable String id) {
        mounted(id);
        PortalResult result = worlds.sealPortal(id);
        Portal portal = worlds.inspectPortal(id);
        World world = mounted(id);
        return ResponseEntity.ok(new PortalMutationResponse(
                portal.id(), portal.state().name(), result.name(), world.revision().value()));
    }

    @GetMapping("/world/{id}/npc")
    @Operation(summary = "Inspect the programmable NPC.")
    public ResponseEntity<NpcInspectResponse> inspectNpc(@PathVariable String id) {
        World world = mounted(id);
        Npc npc = worlds.inspectNpc(id);
        if (npc == null) {
            throw ResourceNotFoundException.world(id);
        }
        return ResponseEntity.ok(new NpcInspectResponse(
                npc.id(), npc.worldId().value(),
                npc.at().x(), npc.at().y(), npc.at().z(), npc.state().name(),
                WorldOps.placeAt(world, npc.at()), WorldOps.lotAt(world, npc.at())));
    }

    @PostMapping("/world/{id}/npc/talk")
    @Operation(summary = "Talk to the NPC. ALREADY_SPEAKING is a result, not silence.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<NpcMutationResponse> talkNpc(@PathVariable String id) {
        mounted(id);
        NpcResult result = worlds.talkNpc(id);
        Npc npc = worlds.inspectNpc(id);
        World world = mounted(id);
        return ResponseEntity.ok(new NpcMutationResponse(
                npc.id(), npc.state().name(), result.name(), world.revision().value()));
    }

    @PostMapping("/world/{id}/npc/hush")
    @Operation(summary = "Hush the NPC. ALREADY_IDLE is a result, not silence.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<NpcMutationResponse> hushNpc(@PathVariable String id) {
        mounted(id);
        NpcResult result = worlds.hushNpc(id);
        Npc npc = worlds.inspectNpc(id);
        World world = mounted(id);
        return ResponseEntity.ok(new NpcMutationResponse(
                npc.id(), npc.state().name(), result.name(), world.revision().value()));
    }

    private static UUID mazeKey(String mazeId) {
        if (mazeId == null || mazeId.isBlank()) {
            return null;
        }
        try {
            return UUID.fromString(mazeId.trim());
        } catch (IllegalArgumentException ex) {
            throw new IllegalArgumentException("mazeId must be a UUID");
        }
    }

    private MazeGrid mazeGrid(UUID mazeId) {
        MazeGenerationService.Cached cached = mazes.find(mazeId);
        if (cached == null) {
            throw ResourceNotFoundException.maze(mazeId);
        }
        return cached.grid();
    }

    private World mounted(String id) {
        World world = worlds.inspect(id);
        if (world == null) {
            throw ResourceNotFoundException.world(id);
        }
        return world;
    }

    private static BlockType parseType(String raw) {
        try {
            return BlockType.valueOf(raw.trim().toUpperCase());
        } catch (IllegalArgumentException ex) {
            throw new IllegalArgumentException(
                    "Unknown block type '" + raw + "'. Use AIR, STONE, DIRT, WOOD, or GLASS.");
        }
    }
}
