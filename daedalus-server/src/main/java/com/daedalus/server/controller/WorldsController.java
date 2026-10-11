// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.CreateWorldRequest;
import com.daedalus.api.dto.CreateWorldResponse;
import com.daedalus.api.dto.WorldRow;
import com.daedalus.api.dto.WorldsResponse;
import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.server.service.WorldHub;
import com.daedalus.server.service.WorldService;
import com.daedalus.world.WorldStyle;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
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

    private WorldRow row(WorldHub.WorldEntry e) {
        WorldService w = hub.get(e.id());
        return new WorldRow(e.id(), e.style().name(), e.style().title(), e.seed(), e.title(),
                w == null ? 0 : w.islands(e.id()).size(), w == null ? 0 : w.inspect(e.id()).revision().value());
    }
}
