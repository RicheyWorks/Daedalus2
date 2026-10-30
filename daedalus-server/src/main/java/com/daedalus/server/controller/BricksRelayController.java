// SPDX-License-Identifier: MIT
package com.daedalus.server.controller;

import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.server.service.BricksRelayService;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.bricks.BricksRelay;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import java.util.UUID;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

/** New, default-off extension; existing obby, auth posture, world and client contracts stay intact. */
@RestController
@RequestMapping("/api/v1/world/{worldId}/bricks-relay/v1")
@ConditionalOnProperty(name = "daedalus.bricks.relay.enabled", havingValue = "true")
@Tag(name = "Bricks practice", description = "Optional Stud Relay; reported landings, no authoritative score or movement.")
public class BricksRelayController {
    private final BricksRelayService relay;

    public record CommandRequest(@NotNull UUID commandId, @NotNull @Min(0) Long expectedRevision,
                                 @NotNull BricksRelay.Action action, Integer platform,
                                 Integer x, Integer y, Integer z) { }

    public BricksRelayController(BricksRelayService relay) {
        this.relay = relay;
    }

    @PostMapping("/runs")
    @PerKeyRateLimit("sessionOpen")
    @Operation(summary = "Open a private practice run on this world's existing seeded obby.")
    public ResponseEntity<BricksRelayService.Admission> open(@PathVariable String worldId, Authentication authentication) {
        BricksRelayService.Admission admission = relay.open(worldId, owner(authentication));
        return ResponseEntity.status("CAPACITY".equals(admission.result()) ? HttpStatus.TOO_MANY_REQUESTS : HttpStatus.CREATED)
                .body(admission);
    }

    @GetMapping("/runs/{runId}")
    @PerKeyRateLimit("sessionMove")
    @Operation(summary = "Read your practice checkpoint, next pickup, and local run feedback.")
    public BricksRelayService.View get(@PathVariable String worldId, @PathVariable UUID runId, Authentication authentication) {
        return relay.get(worldId, runId, owner(authentication));
    }

    @PostMapping("/runs/{runId}/commands")
    @PerKeyRateLimit("sessionMove")
    @Operation(summary = "Report a landing, fall, finish or restart with a revision and retry-safe command id.")
    public ResponseEntity<BricksRelayService.Receipt> command(@PathVariable String worldId, @PathVariable UUID runId,
            @Valid @RequestBody CommandRequest request, Authentication authentication) {
        String owner = owner(authentication);
        boolean landing = request.action() == BricksRelay.Action.LAND || request.action() == BricksRelay.Action.FINISH;
        if (landing && (request.x() == null || request.y() == null || request.z() == null)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "LAND and FINISH require integer feet coordinates");
        }
        if (request.action() == BricksRelay.Action.LAND && request.platform() == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "LAND requires the zero-based obby platform index");
        }
        BlockCoordinate at = landing ? new BlockCoordinate(request.x(), request.y(), request.z()) : null;
        BricksRelay.Command command = new BricksRelay.Command(request.action(),
                request.action() == BricksRelay.Action.LAND ? request.platform() : -1, at);
        BricksRelayService.Receipt receipt = relay.apply(worldId, runId, owner, request.commandId(), request.expectedRevision(), command);
        HttpStatus status = "REVISION_CONFLICT".equals(receipt.result()) || "COMMAND_CONFLICT".equals(receipt.result())
                ? HttpStatus.CONFLICT : HttpStatus.OK;
        return ResponseEntity.status(status).body(receipt);
    }

    @DeleteMapping("/runs/{runId}")
    @PerKeyRateLimit("sessionMove")
    @Operation(summary = "Close your practice run and release its bounded slot.")
    public ResponseEntity<Void> close(@PathVariable String worldId, @PathVariable UUID runId, Authentication authentication) {
        relay.close(worldId, runId, owner(authentication));
        return ResponseEntity.noContent().build();
    }

    private static String owner(Authentication authentication) {
        String owner = SessionController.ownerOf(authentication);
        if (owner == null || owner.isBlank()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Authenticated principal required for private practice");
        }
        return owner;
    }
}
