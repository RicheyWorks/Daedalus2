// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.CreateWorldRequest;
import com.daedalus.api.dto.CreateWorldResponse;
import com.daedalus.api.dto.GateRow;
import com.daedalus.api.dto.OpenGateRequest;
import com.daedalus.api.dto.OpenGateResponse;
import com.daedalus.api.dto.WorldGatesResponse;
import com.daedalus.api.dto.WorldRow;
import com.daedalus.api.dto.WorldsResponse;
import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.server.service.WorldHub;
import com.daedalus.server.service.WorldService;
import com.daedalus.server.web.ResourceNotFoundException;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.gate.GateOps;
import com.daedalus.world.gate.Mount;
import com.daedalus.world.WorldStyle;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/** The multiverse's index (ADR-030): which worlds this server mounts, and mounting a new one. */
@RestController
@RequestMapping("/api/v1")
@Tag(name = "Worlds", description = "Every mounted world; mount a new one.")
public class WorldsController {

    private final WorldHub hub;

    public WorldsController(WorldHub hub) {
        this.hub = hub;
    }

    @GetMapping("/worlds")
    @Operation(summary = "Every mounted world, World Zero first, and every world style.")
    public WorldsResponse worlds() {
        List<WorldRow> rows = new ArrayList<>();
        for (WorldHub.WorldEntry e : hub.worlds()) {
            rows.add(row(e));
        }
        List<WorldsResponse.StyleRow> styles = new ArrayList<>();
        for (WorldStyle s : WorldStyle.values()) {
            styles.add(new WorldsResponse.StyleRow(s.name(), s.title(), s.ready()));
        }
        return new WorldsResponse(rows, styles);
    }

    @PostMapping("/worlds")
    @Operation(summary = "Mount a new world of a ready style, grown from a seed.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<CreateWorldResponse> create(@Valid @RequestBody CreateWorldRequest body) {
        WorldStyle style;
        try {
            style = WorldStyle.valueOf(body.style().strip().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.ok(new CreateWorldResponse("BAD_STYLE", null));
        }
        WorldHub.WorldWrite w = hub.create(body.id(), style, body.seed(), body.title());
        return ResponseEntity.ok(new CreateWorldResponse(w.result(), w.world() == null ? null : row(w.world())));
    }

    @GetMapping("/world/{id}/gates")
    @Operation(summary = "This world's sky gates: in the clouds past the rainbow, reached only by air.")
    public WorldGatesResponse gates(@PathVariable String id) {
        WorldService w = hub.get(id);
        if (w == null) {
            throw ResourceNotFoundException.world(id);
        }
        List<GateRow> rows = new ArrayList<>();
        for (WorldService.GateLink g : w.gates(id)) {
            BlockCoordinate c = g.center();
            BlockCoordinate b = g.berth();
            rows.add(new GateRow(g.gate(), GateOps.slotOfGate(g.gate()), c.x(), c.y(), c.z(), b.x(), b.y(), b.z(),
                    g.toWorld(), hub.title(g.toWorld()), g.toGate()));
        }
        Mount mount = Mount.of(hub.style(id));
        return new WorldGatesResponse(id, mount.name(), mount.ready(), rows);
    }

    @PostMapping("/world/{id}/gates")
    @Operation(summary = "Open a pair of sky gates between this world and another.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<OpenGateResponse> openGate(@PathVariable String id, @Valid @RequestBody OpenGateRequest body) {
        if (hub.get(id) == null) {
            throw ResourceNotFoundException.world(id);
        }
        WorldHub.GateWrite w = hub.openGate(id, body.toWorld().strip());
        return ResponseEntity.ok(new OpenGateResponse(w.result(), w.fromGate(), body.toWorld().strip(), w.toGate()));
    }

    private WorldRow row(WorldHub.WorldEntry e) {
        WorldService w = hub.get(e.id());
        return new WorldRow(e.id(), e.style().name(), e.style().title(), e.seed(), e.title(),
                w == null ? 0 : w.islands(e.id()).size(), w == null ? 0 : w.inspect(e.id()).revision().value());
    }
}
