// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.ArkRow;
import com.daedalus.api.dto.BlockInspectResponse;
import com.daedalus.api.dto.BlockMutationResponse;
import com.daedalus.api.dto.CargoRow;
import com.daedalus.api.dto.ChunkBlocksResponse;
import com.daedalus.api.dto.ChunkInspectResponse;
import com.daedalus.api.dto.ChunkRow;
import com.daedalus.api.dto.DenyParcelRequest;
import com.daedalus.api.dto.DoorInspectResponse;
import com.daedalus.api.dto.DoorMutationResponse;
import com.daedalus.api.dto.ForgiveParcelRequest;
import com.daedalus.api.dto.GrantParcelRequest;
import com.daedalus.api.dto.IslandClaimRequest;
import com.daedalus.api.dto.IslandClaimResponse;
import com.daedalus.api.dto.IslandEcologyResponse;
import com.daedalus.api.dto.IslandRaiseResponse;
import com.daedalus.api.dto.IslandRow;
import com.daedalus.api.dto.IslandTokenMetadata;
import com.daedalus.api.dto.TokenAttribute;
import com.daedalus.api.dto.NpcInspectResponse;
import com.daedalus.api.dto.NpcMutationResponse;
import com.daedalus.api.dto.ParcelDenyResponse;
import com.daedalus.api.dto.ParcelForgiveResponse;
import com.daedalus.api.dto.ParcelGrantResponse;
import com.daedalus.api.dto.ParcelLeaseResponse;
import com.daedalus.api.dto.ParcelReleaseResponse;
import com.daedalus.api.dto.ParcelRevokeResponse;
import com.daedalus.api.dto.PlaceBlockRequest;
import com.daedalus.api.dto.PortalInspectResponse;
import com.daedalus.api.dto.PortalMutationResponse;
import com.daedalus.api.dto.RaiseIslandRequest;
import com.daedalus.api.dto.RevokeParcelRequest;
import com.daedalus.api.dto.StampMutationResponse;
import com.daedalus.api.dto.StampWorldRequest;
import com.daedalus.api.dto.TrapInspectResponse;
import com.daedalus.api.dto.TrapMutationResponse;
import com.daedalus.api.dto.VoyageRequest;
import com.daedalus.api.dto.VoyageResponse;
import com.daedalus.api.dto.WorldArksResponse;
import com.daedalus.api.dto.WorldCapabilitiesResponse;
import com.daedalus.api.dto.WorldChunksResponse;
import com.daedalus.api.dto.WorldInspectResponse;
import com.daedalus.api.dto.WorldIslandsResponse;
import com.daedalus.api.dto.WorldObserveResponse;
import com.daedalus.api.dto.WorldParcelRow;
import com.daedalus.api.dto.WorldParcelsResponse;
import com.daedalus.api.dto.WorldTraceResponse;
import com.daedalus.api.dto.WorldTraceStepResponse;
import com.daedalus.engine.MazeGrid;
import com.daedalus.plugin.runtime.PluginRegistry;
import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.server.service.WorldHub;
import com.daedalus.server.service.WorldService;
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
import com.daedalus.world.ark.Ark;
import com.daedalus.world.auto.DriveTrace;
import com.daedalus.world.auto.Observation;
import com.daedalus.world.auto.WorldOps;
import com.daedalus.world.auto.WorldZeroCapabilities;
import com.daedalus.world.ecology.Diversity;
import com.daedalus.world.ecology.Guild;
import com.daedalus.world.ecology.Species;
import com.daedalus.world.ecology.SpeciesCanon;
import com.daedalus.world.island.IslandGenerator;
import com.daedalus.world.island.IslandPortrait;
import com.daedalus.world.island.IslandTraits;
import com.daedalus.world.stamp.StampResult;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.CacheControl;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;

import java.security.Principal;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.UUID;

/**
 * Persistent voxel volume. Maze routes stay on {@code /api/v1/maze/**}.
 */
@RestController
@RequestMapping("/api/v1")
@Tag(name = "World", description = "Inspect, place, and remove cubes in world-zero.")
@Validated
public class WorldController {

    private final WorldHub hub;
    private final PluginRegistry plugins;
    private final MazeGenerationService mazes;

    /** World Zero alone (tests, and code that never mounts another world). */
    public WorldController(WorldService worlds, PluginRegistry plugins,
            MazeGenerationService mazes) {
        this(WorldHub.of(worlds), plugins, mazes);
    }

    @Autowired
    public WorldController(WorldHub hub, PluginRegistry plugins, MazeGenerationService mazes) {
        this.hub = hub;
        this.plugins = plugins;
        this.mazes = mazes;
    }

    /**
     * The world a route names (ADR-030). An unknown id resolves to World Zero's service, which answers
     * null for any id but its own, so every route keeps its 404.
     */
    private WorldService world(String id) {
        return hub.resolve(id);
    }

    @GetMapping("/world/{id}")
    @Operation(summary = "Inspect a world: id, revision, street directory.")
    public ResponseEntity<WorldInspectResponse> inspect(@PathVariable String id) {
        World world = mounted(id);
        return ResponseEntity.ok(new WorldInspectResponse(
                world.id().value(), world.revision().value(), world.chunkCount(),
                world.parcels().size(), WorldOps.streetLine(world), WorldOps.lastLot(world),
                WorldOps.lastMaze(world), WorldOps.lastLeaseId(world),
                WorldOps.lastPlaceName(world), WorldOps.occupantsLine(world),
                WorldOps.standsLine(world), WorldOps.lastAcl(world),
                WorldOps.driveLine(world), WorldOps.actorLine(world),
                WorldOps.atLine(world), WorldOps.lastBox(world),
                WorldOps.streetBoxes(world), WorldOps.streetLeases(world),
                WorldOps.streetMazes(world), WorldOps.streetLots(world),
                WorldOps.aclLine(world), WorldOps.streetLine(world)));
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
                    parcel.bounds().minX(), parcel.bounds().minZ(), parcel.version(),
                    WorldOps.boxLine(parcel.bounds()),
                    WorldOps.aclOf(world, parcel.id())));
        }
        return ResponseEntity.ok(new WorldParcelsResponse(world.id().value(), rows));
    }

    @PostMapping("/world/{id}/parcels/lease")
    @Operation(summary = "Lease the first vacant parcel as tenant-zero. NO_PARCEL is a result, not silence.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<ParcelLeaseResponse> leaseParcel(@PathVariable String id) {
        mounted(id);
        ParcelLeaseResult result = world(id).leaseParcel(id);
        World world = mounted(id);
        return ResponseEntity.ok(new ParcelLeaseResponse(
                result.name(), WorldOps.lastLeaseId(world), world.revision().value(),
                WorldOps.lastLeaseMaze(world), WorldOps.lastLeasePlace(world),
                WorldOps.lastLeaseLot(world), WorldOps.lastLeaseBox(world)));
    }

    @PostMapping("/world/{id}/parcels/release")
    @Operation(summary = "Release the first leased parcel. NOT_LEASED and NO_PARCEL are named results.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<ParcelReleaseResponse> releaseParcel(@PathVariable String id) {
        mounted(id);
        ParcelReleaseResult result = world(id).releaseParcel(id);
        World world = mounted(id);
        return ResponseEntity.ok(new ParcelReleaseResponse(
                result.name(), WorldOps.lastLeaseId(world), world.revision().value(),
                WorldOps.lastLeaseMaze(world), WorldOps.lastLeasePlace(world),
                WorldOps.lastLeaseLot(world), WorldOps.lastLeaseBox(world)));
    }

    @PostMapping("/world/{id}/parcels/grant")
    @Operation(summary = "Grant block.place on the slab under the cube, or the first plot.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<ParcelGrantResponse> grantParcel(
            @PathVariable String id, @Valid @RequestBody GrantParcelRequest body) {
        mounted(id);
        BlockCoordinate at = new BlockCoordinate(
                body.x() == null ? 0 : body.x(),
                body.y() == null ? 0 : body.y(),
                body.z() == null ? 0 : body.z());
        ParcelGrantResult result = world(id).grantParcel(id, at, body.actorId(), body.verb());
        World world = mounted(id);
        return ResponseEntity.ok(new ParcelGrantResponse(
                result.name(), WorldOps.aclLine(world), world.revision().value(),
                WorldOps.mazeAt(world, at), WorldOps.leaseAt(world, at),
                WorldOps.placeAt(world, at), WorldOps.lotAt(world, at),
                WorldOps.boxAt(world, at)));
    }

    @PostMapping("/world/{id}/parcels/deny")
    @Operation(summary = "Deny block.place on the slab under the cube, or the first plot.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<ParcelDenyResponse> denyParcel(
            @PathVariable String id, @Valid @RequestBody DenyParcelRequest body) {
        mounted(id);
        BlockCoordinate at = new BlockCoordinate(
                body.x() == null ? 0 : body.x(),
                body.y() == null ? 0 : body.y(),
                body.z() == null ? 0 : body.z());
        ParcelDenyResult result = world(id).denyParcel(id, at, body.actorId(), body.verb());
        World world = mounted(id);
        return ResponseEntity.ok(new ParcelDenyResponse(
                result.name(), WorldOps.aclLine(world), world.revision().value(),
                WorldOps.mazeAt(world, at), WorldOps.leaseAt(world, at),
                WorldOps.placeAt(world, at), WorldOps.lotAt(world, at),
                WorldOps.boxAt(world, at)));
    }

    @PostMapping("/world/{id}/parcels/revoke")
    @Operation(summary = "Revoke an extra grant on the slab under the cube, or the first plot.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<ParcelRevokeResponse> revokeParcel(
            @PathVariable String id, @Valid @RequestBody RevokeParcelRequest body) {
        mounted(id);
        BlockCoordinate at = new BlockCoordinate(
                body.x() == null ? 0 : body.x(),
                body.y() == null ? 0 : body.y(),
                body.z() == null ? 0 : body.z());
        ParcelRevokeResult result = world(id).revokeParcel(id, at, body.actorId(), body.verb());
        World world = mounted(id);
        return ResponseEntity.ok(new ParcelRevokeResponse(
                result.name(), WorldOps.aclLine(world), world.revision().value(),
                WorldOps.mazeAt(world, at), WorldOps.leaseAt(world, at),
                WorldOps.placeAt(world, at), WorldOps.lotAt(world, at),
                WorldOps.boxAt(world, at)));
    }

    @PostMapping("/world/{id}/parcels/forgive")
    @Operation(summary = "Forgive an extra denial on the slab under the cube, or the first plot.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<ParcelForgiveResponse> forgiveParcel(
            @PathVariable String id, @Valid @RequestBody ForgiveParcelRequest body) {
        mounted(id);
        BlockCoordinate at = new BlockCoordinate(
                body.x() == null ? 0 : body.x(),
                body.y() == null ? 0 : body.y(),
                body.z() == null ? 0 : body.z());
        ParcelForgiveResult result = world(id).forgiveParcel(id, at, body.actorId(), body.verb());
        World world = mounted(id);
        return ResponseEntity.ok(new ParcelForgiveResponse(
                result.name(), WorldOps.aclLine(world), world.revision().value(),
                WorldOps.mazeAt(world, at), WorldOps.leaseAt(world, at),
                WorldOps.placeAt(world, at), WorldOps.lotAt(world, at),
                WorldOps.boxAt(world, at)));
    }

    @PostMapping("/world/{id}/stamp")
    @Operation(summary = "Stamp a maze slab. Optional mazeId from the lab cache. Overlap is a named result.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<StampMutationResponse> stamp(
            @PathVariable String id, @Valid @RequestBody StampWorldRequest body) {
        mounted(id);
        BlockCoordinate at = new BlockCoordinate(body.x(), body.y(), body.z());
        UUID mazeId = mazeKey(body.mazeId());
        StampResult result = world(id).stamp(id, at, mazeId == null ? null : mazeGrid(mazeId), mazeId,
                Boolean.TRUE.equals(body.next()), body.actorId());
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
        String maze = result.ok() && mazeId != null ? mazeId.toString() : "";
        String place = result.ok() ? WorldOps.lastPlaceName(mounted(id)) : "";
        String lot = result.ok() ? WorldOps.lastLot(mounted(id)) : "";
        return ResponseEntity.ok(new StampMutationResponse(
                result.ok(), result.outcome(), parcelId, result.revision().value(),
                minX, maxX, minZ, maxZ, WorldOps.boxLine(result.bounds()), maze, place, lot));
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
        Observation seen = world(id).observe(id, x, y, z);
        return ResponseEntity.ok(new WorldObserveResponse(
                seen.worldId(), seen.revision(), seen.x(), seen.y(), seen.z(),
                seen.blockType(), seen.doorState(), seen.place(), seen.lot(),
                seen.occupant(), seen.acl(), seen.drive(), seen.driveActor(),
                seen.driveAt(), seen.lease(), seen.maze()));
    }

    @GetMapping("/world/{id}/trace")
    @Operation(summary = "Trace driven world ops. Discover does not write this.")
    public ResponseEntity<WorldTraceResponse> trace(@PathVariable String id) {
        World world = mounted(id);
        List<WorldTraceStepResponse> steps = new ArrayList<>();
        for (DriveTrace.Step step : world(id).trace(id)) {
            steps.add(new WorldTraceStepResponse(
                    step.capability(), step.result(), step.revisionAfter(), step.actor(),
                    step.at(), WorldOps.mazeOn(world, step.at()),
                    WorldOps.leaseOn(world, step.at()),
                    WorldOps.placeOn(world, step.at()),
                    WorldOps.lotOn(world, step.at()),
                    WorldOps.boxOn(world, step.at()),
                    WorldOps.aclOn(world, step.at())));
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
                WorldOps.occupantAt(world, at), WorldOps.aclAt(world, at),
                WorldOps.driveOn(world, at), WorldOps.actorOn(world, at),
                WorldOps.atOn(world, at), WorldOps.boxAt(world, at)));
    }

    @GetMapping("/world/{id}/chunk")
    @Operation(summary = "Inspect one 16³ chunk.")
    public ResponseEntity<ChunkInspectResponse> inspectChunk(
            @PathVariable String id,
            @RequestParam @NotNull Integer x,
            @RequestParam @NotNull Integer y,
            @RequestParam @NotNull Integer z) {
        World world = mounted(id);
        Chunk chunk = world(id).inspectChunk(id, x, y, z);
        ChunkCoordinate cc = new ChunkCoordinate(x, y, z);
        int plots = WorldOps.plotsInChunk(world, cc);
        String street = WorldOps.streetInChunk(world, cc);
        String place = WorldOps.placeInChunk(world, cc);
        String places = WorldOps.streetInChunk(world, cc);
        String lot = WorldOps.lotInChunk(world, cc);
        String lots = WorldOps.lotsInChunk(world, cc);
        String occupants = WorldOps.occupantsInChunk(world, cc);
        String stands = WorldOps.standsInChunk(world, cc);
        String drive = WorldOps.driveInChunk(world, cc);
        String driveActor = WorldOps.actorInChunk(world, cc);
        String driveAt = WorldOps.atInChunk(world, cc);
        String maze = WorldOps.mazeInChunk(world, cc);
        String mazes = WorldOps.mazesInChunk(world, cc);
        String lease = WorldOps.leaseInChunk(world, cc);
        String leases = WorldOps.leasesInChunk(world, cc);
        String acl = WorldOps.lastAclInChunk(world, cc);
        String acls = WorldOps.aclInChunk(world, cc);
        String box = WorldOps.boxInChunk(world, cc);
        String boxes = WorldOps.boxesInChunk(world, cc);
        if (chunk == null) {
            return ResponseEntity.ok(new ChunkInspectResponse(
                    x, y, z, false, null, 0, plots, street, lot, occupants, stands,
                    drive, driveActor, driveAt, maze, lease, acl, place, lots, mazes, leases,
                    acls, box, boxes, places));
        }
        return ResponseEntity.ok(new ChunkInspectResponse(
                x, y, z, true, chunk.revision(), chunk.occupied(), plots, street, lot,
                occupants, stands, drive, driveActor, driveAt, maze, lease, acl, place, lots,
                mazes, leases, acls, box, boxes, places));
    }

    @PutMapping("/world/{id}/block")
    @Operation(summary = "Place a cube. AIR is remove.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<BlockMutationResponse> place(
            @PathVariable String id, @Valid @RequestBody PlaceBlockRequest body, Principal principal) {
        mounted(id);
        BlockType type = parseType(body.type());
        WorldService.BlockWrite write = world(id).place(id, body.x(), body.y(), body.z(), type,
                actor(principal, body.actorId()));
        World world = mounted(id);
        BlockCoordinate at = new BlockCoordinate(body.x(), body.y(), body.z());
        return ResponseEntity.ok(new BlockMutationResponse(
                body.x(), body.y(), body.z(), write.previous().name(),
                write.now().name(), write.revision(), write.result(),
                WorldOps.mazeAt(world, at), WorldOps.leaseAt(world, at),
                WorldOps.placeAt(world, at), WorldOps.lotAt(world, at),
                WorldOps.boxAt(world, at), WorldOps.aclAt(world, at)));
    }

    @DeleteMapping("/world/{id}/block")
    @Operation(summary = "Remove a cube (set AIR).")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<BlockMutationResponse> remove(
            @PathVariable String id,
            @RequestParam @NotNull Integer x,
            @RequestParam @NotNull Integer y,
            @RequestParam @NotNull Integer z,
            @RequestParam(required = false) String actorId, Principal principal) {
        mounted(id);
        WorldService.BlockWrite write = world(id).remove(id, x, y, z, actor(principal, actorId));
        World world = mounted(id);
        BlockCoordinate at = new BlockCoordinate(x, y, z);
        return ResponseEntity.ok(new BlockMutationResponse(
                x, y, z, write.previous().name(), write.now().name(),
                write.revision(), write.result(),
                WorldOps.mazeAt(world, at), WorldOps.leaseAt(world, at),
                WorldOps.placeAt(world, at), WorldOps.lotAt(world, at),
                WorldOps.boxAt(world, at), WorldOps.aclAt(world, at)));
    }

    @GetMapping("/world/{id}/door")
    @Operation(summary = "Inspect the programmable door.")
    public ResponseEntity<DoorInspectResponse> inspectDoor(@PathVariable String id) {
        World world = mounted(id);
        Door door = world(id).inspectDoor(id);
        if (door == null) {
            throw ResourceNotFoundException.world(id);
        }
        return ResponseEntity.ok(new DoorInspectResponse(
                door.id(), door.worldId().value(),
                door.at().x(), door.at().y(), door.at().z(), door.state().name(),
                WorldOps.placeAt(world, door.at()), WorldOps.lotAt(world, door.at()),
                WorldOps.aclAt(world, door.at()),
                WorldOps.driveOn(world, door.at()), WorldOps.actorOn(world, door.at()),
                WorldOps.atOn(world, door.at()), WorldOps.boxAt(world, door.at()),
                WorldOps.mazeAt(world, door.at()), WorldOps.leaseAt(world, door.at())));
    }

    @PostMapping("/world/{id}/door/open")
    @Operation(summary = "Open the door. ALREADY_OPEN is a result, not silence.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<DoorMutationResponse> openDoor(
            @PathVariable String id, @RequestParam(required = false) String actorId) {
        mounted(id);
        DoorResult result = world(id).openDoor(id, actorId);
        Door door = world(id).inspectDoor(id);
        World world = mounted(id);
        return ResponseEntity.ok(new DoorMutationResponse(
                door.id(), door.state().name(), result.name(), world.revision().value(),
                WorldOps.mazeAt(world, door.at()), WorldOps.leaseAt(world, door.at()),
                WorldOps.placeAt(world, door.at()), WorldOps.lotAt(world, door.at()),
                WorldOps.boxAt(world, door.at()), WorldOps.aclAt(world, door.at())));
    }

    @PostMapping("/world/{id}/door/close")
    @Operation(summary = "Close the door. ALREADY_CLOSED is a result, not silence.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<DoorMutationResponse> closeDoor(
            @PathVariable String id, @RequestParam(required = false) String actorId) {
        mounted(id);
        DoorResult result = world(id).closeDoor(id, actorId);
        Door door = world(id).inspectDoor(id);
        World world = mounted(id);
        return ResponseEntity.ok(new DoorMutationResponse(
                door.id(), door.state().name(), result.name(), world.revision().value(),
                WorldOps.mazeAt(world, door.at()), WorldOps.leaseAt(world, door.at()),
                WorldOps.placeAt(world, door.at()), WorldOps.lotAt(world, door.at()),
                WorldOps.boxAt(world, door.at()), WorldOps.aclAt(world, door.at())));
    }

    @GetMapping("/world/{id}/trap")
    @Operation(summary = "Inspect the programmable trap.")
    public ResponseEntity<TrapInspectResponse> inspectTrap(@PathVariable String id) {
        World world = mounted(id);
        Trap trap = world(id).inspectTrap(id);
        if (trap == null) {
            throw ResourceNotFoundException.world(id);
        }
        return ResponseEntity.ok(new TrapInspectResponse(
                trap.id(), trap.worldId().value(),
                trap.at().x(), trap.at().y(), trap.at().z(), trap.state().name(),
                WorldOps.placeAt(world, trap.at()), WorldOps.lotAt(world, trap.at()),
                WorldOps.aclAt(world, trap.at()),
                WorldOps.driveOn(world, trap.at()), WorldOps.actorOn(world, trap.at()),
                WorldOps.atOn(world, trap.at()), WorldOps.boxAt(world, trap.at()),
                WorldOps.mazeAt(world, trap.at()), WorldOps.leaseAt(world, trap.at())));
    }

    @PostMapping("/world/{id}/trap/arm")
    @Operation(summary = "Arm the trap. ALREADY_ARMED is a result, not silence.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<TrapMutationResponse> armTrap(
            @PathVariable String id, @RequestParam(required = false) String actorId) {
        mounted(id);
        TrapResult result = world(id).armTrap(id, actorId);
        Trap trap = world(id).inspectTrap(id);
        World world = mounted(id);
        return ResponseEntity.ok(new TrapMutationResponse(
                trap.id(), trap.state().name(), result.name(), world.revision().value(),
                WorldOps.mazeAt(world, trap.at()), WorldOps.leaseAt(world, trap.at()),
                WorldOps.placeAt(world, trap.at()), WorldOps.lotAt(world, trap.at()),
                WorldOps.boxAt(world, trap.at()), WorldOps.aclAt(world, trap.at())));
    }

    @PostMapping("/world/{id}/trap/disarm")
    @Operation(summary = "Disarm the trap. ALREADY_DISARMED is a result, not silence.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<TrapMutationResponse> disarmTrap(
            @PathVariable String id, @RequestParam(required = false) String actorId) {
        mounted(id);
        TrapResult result = world(id).disarmTrap(id, actorId);
        Trap trap = world(id).inspectTrap(id);
        World world = mounted(id);
        return ResponseEntity.ok(new TrapMutationResponse(
                trap.id(), trap.state().name(), result.name(), world.revision().value(),
                WorldOps.mazeAt(world, trap.at()), WorldOps.leaseAt(world, trap.at()),
                WorldOps.placeAt(world, trap.at()), WorldOps.lotAt(world, trap.at()),
                WorldOps.boxAt(world, trap.at()), WorldOps.aclAt(world, trap.at())));
    }

    @GetMapping("/world/{id}/portal")
    @Operation(summary = "Inspect the programmable portal.")
    public ResponseEntity<PortalInspectResponse> inspectPortal(@PathVariable String id) {
        World world = mounted(id);
        Portal portal = world(id).inspectPortal(id);
        if (portal == null) {
            throw ResourceNotFoundException.world(id);
        }
        return ResponseEntity.ok(new PortalInspectResponse(
                portal.id(), portal.worldId().value(),
                portal.at().x(), portal.at().y(), portal.at().z(), portal.state().name(),
                WorldOps.placeAt(world, portal.at()), WorldOps.lotAt(world, portal.at()),
                WorldOps.aclAt(world, portal.at()),
                WorldOps.driveOn(world, portal.at()), WorldOps.actorOn(world, portal.at()),
                WorldOps.atOn(world, portal.at()), WorldOps.boxAt(world, portal.at()),
                WorldOps.mazeAt(world, portal.at()), WorldOps.leaseAt(world, portal.at())));
    }

    @PostMapping("/world/{id}/portal/open")
    @Operation(summary = "Open the portal. ALREADY_OPEN is a result, not silence.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<PortalMutationResponse> openPortal(
            @PathVariable String id, @RequestParam(required = false) String actorId) {
        mounted(id);
        PortalResult result = world(id).openPortal(id, actorId);
        Portal portal = world(id).inspectPortal(id);
        World world = mounted(id);
        return ResponseEntity.ok(new PortalMutationResponse(
                portal.id(), portal.state().name(), result.name(), world.revision().value(),
                WorldOps.mazeAt(world, portal.at()), WorldOps.leaseAt(world, portal.at()),
                WorldOps.placeAt(world, portal.at()), WorldOps.lotAt(world, portal.at()),
                WorldOps.boxAt(world, portal.at()), WorldOps.aclAt(world, portal.at())));
    }

    @PostMapping("/world/{id}/portal/seal")
    @Operation(summary = "Seal the portal. ALREADY_SEALED is a result, not silence.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<PortalMutationResponse> sealPortal(
            @PathVariable String id, @RequestParam(required = false) String actorId) {
        mounted(id);
        PortalResult result = world(id).sealPortal(id, actorId);
        Portal portal = world(id).inspectPortal(id);
        World world = mounted(id);
        return ResponseEntity.ok(new PortalMutationResponse(
                portal.id(), portal.state().name(), result.name(), world.revision().value(),
                WorldOps.mazeAt(world, portal.at()), WorldOps.leaseAt(world, portal.at()),
                WorldOps.placeAt(world, portal.at()), WorldOps.lotAt(world, portal.at()),
                WorldOps.boxAt(world, portal.at()), WorldOps.aclAt(world, portal.at())));
    }

    @GetMapping("/world/{id}/npc")
    @Operation(summary = "Inspect the programmable NPC.")
    public ResponseEntity<NpcInspectResponse> inspectNpc(@PathVariable String id) {
        World world = mounted(id);
        Npc npc = world(id).inspectNpc(id);
        if (npc == null) {
            throw ResourceNotFoundException.world(id);
        }
        return ResponseEntity.ok(new NpcInspectResponse(
                npc.id(), npc.worldId().value(),
                npc.at().x(), npc.at().y(), npc.at().z(), npc.state().name(),
                WorldOps.placeAt(world, npc.at()), WorldOps.lotAt(world, npc.at()),
                WorldOps.aclAt(world, npc.at()),
                WorldOps.driveOn(world, npc.at()), WorldOps.actorOn(world, npc.at()),
                WorldOps.atOn(world, npc.at()), WorldOps.boxAt(world, npc.at()),
                WorldOps.mazeAt(world, npc.at()), WorldOps.leaseAt(world, npc.at())));
    }

    @PostMapping("/world/{id}/npc/talk")
    @Operation(summary = "Talk to the NPC. ALREADY_SPEAKING is a result, not silence.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<NpcMutationResponse> talkNpc(
            @PathVariable String id, @RequestParam(required = false) String actorId) {
        mounted(id);
        NpcResult result = world(id).talkNpc(id, actorId);
        Npc npc = world(id).inspectNpc(id);
        World world = mounted(id);
        return ResponseEntity.ok(new NpcMutationResponse(
                npc.id(), npc.state().name(), result.name(), world.revision().value(),
                WorldOps.mazeAt(world, npc.at()), WorldOps.leaseAt(world, npc.at()),
                WorldOps.placeAt(world, npc.at()), WorldOps.lotAt(world, npc.at()),
                WorldOps.boxAt(world, npc.at()), WorldOps.aclAt(world, npc.at())));
    }

    @PostMapping("/world/{id}/npc/hush")
    @Operation(summary = "Hush the NPC. ALREADY_IDLE is a result, not silence.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<NpcMutationResponse> hushNpc(
            @PathVariable String id, @RequestParam(required = false) String actorId) {
        mounted(id);
        NpcResult result = world(id).hushNpc(id, actorId);
        Npc npc = world(id).inspectNpc(id);
        World world = mounted(id);
        return ResponseEntity.ok(new NpcMutationResponse(
                npc.id(), npc.state().name(), result.name(), world.revision().value(),
                WorldOps.mazeAt(world, npc.at()), WorldOps.leaseAt(world, npc.at()),
                WorldOps.placeAt(world, npc.at()), WorldOps.lotAt(world, npc.at()),
                WorldOps.boxAt(world, npc.at()), WorldOps.aclAt(world, npc.at())));
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

    @GetMapping("/world/{id}/chunks")
    @Operation(summary = "List every non-empty chunk, for a renderer to fetch.")
    public ResponseEntity<WorldChunksResponse> listChunks(@PathVariable String id) {
        World world = mounted(id);
        List<ChunkRow> rows = new ArrayList<>();
        List<ChunkCoordinate> keys = new ArrayList<>(world.chunkKeys());
        keys.sort(Comparator.comparingInt(ChunkCoordinate::y)
                .thenComparingInt(ChunkCoordinate::z)
                .thenComparingInt(ChunkCoordinate::x));
        for (ChunkCoordinate cc : keys) {
            Chunk chunk = world.chunk(cc);
            if (chunk != null && !chunk.isEmpty()) {
                rows.add(new ChunkRow(cc.x(), cc.y(), cc.z(), chunk.revision(), chunk.occupied()));
            }
        }
        return ResponseEntity.ok(new WorldChunksResponse(id, world.revision().value(), Chunk.SIZE, rows));
    }

    @GetMapping("/world/{id}/chunk/blocks")
    @Operation(summary = "One chunk's cubes as a base64 ordinal payload, for meshing.")
    public ResponseEntity<ChunkBlocksResponse> chunkBlocks(
            @PathVariable String id,
            @RequestParam @NotNull Integer x,
            @RequestParam @NotNull Integer y,
            @RequestParam @NotNull Integer z) {
        mounted(id);
        Chunk chunk = world(id).inspectChunk(id, x, y, z);
        List<String> palette = new ArrayList<>();
        for (BlockType t : BlockType.values()) {
            palette.add(t.name());
        }
        if (chunk == null || chunk.isEmpty()) {
            return ResponseEntity.ok(new ChunkBlocksResponse(x, y, z, false, 0L, palette, ""));
        }
        return ResponseEntity.ok(new ChunkBlocksResponse(x, y, z, true, chunk.revision(), palette,
                Base64.getEncoder().encodeToString(chunk.ordinals())));
    }

    @GetMapping("/world/{id}/islands")
    @Operation(summary = "List raised islands with their seeds and traits.")
    public ResponseEntity<WorldIslandsResponse> listIslands(@PathVariable String id) {
        mounted(id);
        List<IslandRow> rows = new ArrayList<>();
        Map<Integer, WorldService.IslandClaim> claims = world(id).claims(id);
        for (WorldService.IslandEntry e : world(id).islands(id)) {
            rows.add(islandRow(e, e.traits(), claims.get(e.slot())));
        }
        return ResponseEntity.ok(new WorldIslandsResponse(id, rows));
    }

    @PostMapping("/world/{id}/islands")
    @Operation(summary = "Raise a seeded floating island into the next free lane slot.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<IslandRaiseResponse> raiseIsland(
            @PathVariable String id, @Valid @RequestBody RaiseIslandRequest body) {
        mounted(id);
        int radius = body.radius() == null ? IslandGenerator.DEFAULT_RADIUS : body.radius();
        WorldService.IslandWrite write = world(id).raiseIsland(id, body.seed(), radius);
        IslandRow row = write.island() == null ? null
                : islandRow(write.island(), write.traits(), world(id).claims(id).get(write.island().slot()));
        return ResponseEntity.ok(new IslandRaiseResponse(write.result(), write.revision(), row));
    }

    @GetMapping("/world/{id}/arks")
    @Operation(summary = "List the arks: moored at a pier or sailing between islands.")
    public ResponseEntity<WorldArksResponse> listArks(@PathVariable String id) {
        mounted(id);
        List<ArkRow> rows = new ArrayList<>();
        for (WorldService.ArkView view : world(id).arks(id)) {
            rows.add(arkRow(view));
        }
        return ResponseEntity.ok(new WorldArksResponse(id, world(id).now(), rows));
    }

    @PostMapping("/world/{id}/arks/{arkId}/voyage")
    @Operation(summary = "Order an ark to sail to another island.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<VoyageResponse> sail(@PathVariable String id, @PathVariable String arkId,
                                               @Valid @RequestBody VoyageRequest body) {
        mounted(id);
        WorldService.SailWrite write = world(id).sail(id, arkId, body.toSlot());
        if (write.view() == null) {
            throw ResourceNotFoundException.ark(arkId);
        }
        return ResponseEntity.ok(new VoyageResponse(write.result().name(), world(id).now(), arkRow(write.view())));
    }

    private static ArkRow arkRow(WorldService.ArkView view) {
        Ark ark = view.ark();
        BlockCoordinate b = ark.berth();
        if (view.voyage() == null) {
            return new ArkRow(ark.id(), ark.name(), ark.homeSlot(), ark.slot(), b.x(), b.y(), b.z(),
                    "MOORED", -1, -1, 0L, 0L, cargo(view.hold()));
        }
        return new ArkRow(ark.id(), ark.name(), ark.homeSlot(), ark.slot(), b.x(), b.y(), b.z(),
                "SAILING", view.voyage().fromSlot(), view.voyage().toSlot(),
                view.voyage().departAt(), view.voyage().arriveAt(), cargo(view.hold()));
    }

    /** Kinds by count, most numerous first, ties by key: the order a reader scans. */
    private static List<CargoRow> cargo(Map<String, Double> counts) {
        SpeciesCanon canon = SpeciesCanon.get();
        List<CargoRow> rows = new ArrayList<>();
        for (Map.Entry<String, Double> e : counts.entrySet()) {
            Species s = canon.byKey(e.getKey());
            rows.add(new CargoRow(e.getKey(), s == null ? e.getKey() : s.name(),
                    s == null ? "UNKNOWN" : s.guild().name(), e.getValue()));
        }
        rows.sort(Comparator.comparingDouble(CargoRow::count).reversed().thenComparing(CargoRow::key));
        return rows;
    }

    @GetMapping("/world/{id}/islands/{slot}/ecology")
    @Operation(summary = "One island's living community: habitat, diversity and every kind there.")
    public ResponseEntity<IslandEcologyResponse> islandEcology(@PathVariable String id, @PathVariable int slot) {
        mounted(id);
        WorldService.IslandEcology life = world(id).ecology(id, slot);
        if (life == null) {
            throw ResourceNotFoundException.island(slot);
        }
        Map<String, Double> habitat = new TreeMap<>();
        for (Guild g : Guild.values()) {
            habitat.put(g.name(), life.habitat().of(g));
        }
        Diversity d = life.diversity();
        return ResponseEntity.ok(new IslandEcologyResponse(id, slot, life.day(), world(id).dayLength(),
                life.habitat().area(), habitat, d.richness(), d.total(), d.shannon(), d.evenness(),
                d.simpson(), cargo(life.abundance())));
    }

    private static IslandRow islandRow(WorldService.IslandEntry e, IslandTraits t, WorldService.IslandClaim claim) {
        BlockCoordinate o = e.origin();
        return new IslandRow(e.slot(), o.x(), o.y(), o.z(), e.seed(), e.radius(), t.columns(),
                t.blocks(), t.trees(), t.blossomTrees(), t.pondColumns(), t.streamLength(),
                t.waterfall(), t.crystals(), t.boulders(), t.top(), t.bottom(),
                o.x() + t.dockX(), o.y() + t.dockY(), o.z() + t.dockZ(),
                claim == null ? "" : claim.owner(), claim == null ? List.of() : claim.builders());
    }

    /**
     * Who is acting (ADR-026): the signed-in user when there is one — a body field cannot speak for
     * someone else — otherwise the {@code actorId} the caller names, as World Zero always allowed.
     */
    private static String actor(Principal principal, String claimed) {
        if (principal != null && principal.getName() != null && !principal.getName().isBlank()) {
            return principal.getName();
        }
        return claimed;
    }

    @PostMapping("/world/{id}/islands/{slot}/claim")
    @Operation(summary = "Claim an island: only its owner, and builders they name, can change its cubes.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<IslandClaimResponse> claimIsland(@PathVariable String id, @PathVariable int slot,
            @Valid @RequestBody(required = false) IslandClaimRequest body, Principal principal) {
        mounted(id);
        return ResponseEntity.ok(claimResponse(world(id).claimIsland(id, slot,
                actor(principal, body == null ? null : body.actorId()))));
    }

    @PostMapping("/world/{id}/islands/{slot}/abandon")
    @Operation(summary = "Give an island back: its cubes stay, anyone may build there again.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<IslandClaimResponse> abandonIsland(@PathVariable String id, @PathVariable int slot,
            @Valid @RequestBody(required = false) IslandClaimRequest body, Principal principal) {
        mounted(id);
        return ResponseEntity.ok(claimResponse(world(id).abandonIsland(id, slot,
                actor(principal, body == null ? null : body.actorId()))));
    }

    @PostMapping("/world/{id}/islands/{slot}/builders")
    @Operation(summary = "The owner lets someone build on their island (allow=true) or stops them.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<IslandClaimResponse> islandBuilder(@PathVariable String id, @PathVariable int slot,
            @Valid @RequestBody IslandClaimRequest body, Principal principal) {
        mounted(id);
        return ResponseEntity.ok(claimResponse(world(id).setBuilder(id, slot, actor(principal, body.actorId()),
                body.builder(), body.allow() == null || body.allow())));
    }

    /** Portraits by "seed/radius": a pure function of the seed, so one render serves forever. */
    private static final Map<String, byte[]> PORTRAITS = new java.util.concurrent.ConcurrentHashMap<>();

    @GetMapping(value = "/world/{id}/islands/{slot}/portrait.png", produces = MediaType.IMAGE_PNG_VALUE)
    @Operation(summary = "The island's isometric portrait as its seed grows it: the token image.")
    public ResponseEntity<byte[]> islandPortrait(@PathVariable String id, @PathVariable int slot) {
        mounted(id);
        WorldService.IslandEntry isle = island(id, slot);
        byte[] png = PORTRAITS.computeIfAbsent(isle.seed() + "/" + isle.radius(), k ->
                IslandPortrait.of(IslandGenerator.generate(isle.seed(), isle.radius())).png());
        return ResponseEntity.ok()
                .cacheControl(CacheControl.maxAge(java.time.Duration.ofDays(1)).cachePublic())
                .eTag("\"" + isle.seed() + "-" + isle.radius() + "\"")
                .contentType(MediaType.IMAGE_PNG)
                .body(png.clone());
    }

    @GetMapping("/world/{id}/tokens/{tokenId}")
    @Operation(summary = "ERC-721 metadata for an island; the token id is the island's lane slot.")
    public ResponseEntity<IslandTokenMetadata> islandToken(@PathVariable String id, @PathVariable int tokenId) {
        mounted(id);
        WorldService.IslandEntry isle = island(id, tokenId);
        IslandTraits t = isle.traits();
        String base = ServletUriComponentsBuilder.fromCurrentContextPath().build().toUriString();
        String arkName = com.daedalus.world.ark.ArkNames.of(isle.seed());
        WorldService.IslandEcology life = world(id).ecology(id, tokenId);
        List<TokenAttribute> attrs = new ArrayList<>();
        attrs.add(TokenAttribute.of("Seed", Long.toString(isle.seed())));
        attrs.add(TokenAttribute.number("Radius", isle.radius()));
        attrs.add(TokenAttribute.number("Ground columns", t.columns()));
        attrs.add(TokenAttribute.number("Trees", t.trees()));
        attrs.add(TokenAttribute.number("Blossom trees", t.blossomTrees()));
        attrs.add(TokenAttribute.number("Crystals", t.crystals()));
        attrs.add(TokenAttribute.of("Waterfall", t.waterfall() ? "Yes" : "No"));
        attrs.add(TokenAttribute.of("Pond", t.pondColumns() > 0 ? "Yes" : "No"));
        attrs.add(TokenAttribute.of("Ark", arkName));
        attrs.add(TokenAttribute.number("Kinds living", life == null ? 0 : life.diversity().richness()));
        String name = "Isle " + tokenId + " · " + arkName;
        String description = "A floating island in the Daedalus Realm, grown from seed " + isle.seed()
                + ". The meteor broke the world into islands; " + arkName + " sails from this one's pier"
                + " carrying life to the others. The same seed always grows the same island.";
        return ResponseEntity.ok(new IslandTokenMetadata(name, description,
                base + "/api/v1/world/" + id + "/islands/" + tokenId + "/portrait.png",
                base + "/realm.html#isle=" + tokenId, attrs));
    }

    private WorldService.IslandEntry island(String id, int slot) {
        for (WorldService.IslandEntry e : world(id).islands(id)) {
            if (e.slot() == slot) {
                return e;
            }
        }
        throw ResourceNotFoundException.island(slot);
    }

    private static IslandClaimResponse claimResponse(WorldService.IslandClaim c) {
        return new IslandClaimResponse(c.result(), c.slot(), c.owner(), c.builders(), c.revision());
    }

    private World mounted(String id) {
        World world = world(id).inspect(id);
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
                    "Unknown block type '" + raw + "'. Use one of " + BlockType.names() + ".");
        }
    }
}
