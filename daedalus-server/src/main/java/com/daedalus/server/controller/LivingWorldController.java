// SPDX-License-Identifier: MIT
package com.daedalus.server.controller;

import com.daedalus.server.service.simulation.LivingWorldService;
import com.daedalus.server.ratelimit.PerKeyRateLimit;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.event.EventListener;
import org.springframework.http.HttpStatus;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.security.Principal;

/** Additive JSON surface on the existing transport. Actor identity is never a request body field. */
@RestController
@RequestMapping("/api/v1/world/{id}/simulation/v1")
@ConditionalOnProperty(name = "daedalus.simulation.enabled", havingValue = "true")
public class LivingWorldController {
    private final LivingWorldService service;
    private final SimpMessagingTemplate stomp;
    public record Supply(@NotBlank @Size(min = 36, max = 36) String requestId, @Min(1) @Max(3) int water) { }

    public LivingWorldController(LivingWorldService service, SimpMessagingTemplate stomp) {
        this.service = service;
        this.stomp = stomp;
    }
    @GetMapping
    public LivingWorldService.View inspect(@PathVariable String id) { return service.inspect(id); }

    @PostMapping("/actions/supply")
    @PerKeyRateLimit("mazeGenerate")
    public LivingWorldService.ActionResult supply(@PathVariable String id, @Valid @RequestBody Supply body,
                                                Principal principal) throws IOException {
        if (principal == null) throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Authenticated principal required");
        try { return service.supply(id, principal.getName(), body.requestId(), body.water()); }
        catch (SecurityException denied) { throw new ResponseStatusException(HttpStatus.FORBIDDEN, denied.getMessage()); }
        catch (IllegalStateException capacity) { throw new ResponseStatusException(HttpStatus.CONFLICT, capacity.getMessage()); }
    }
    @EventListener
    public void updated(LivingWorldService.Update update) {
        stomp.convertAndSend("/topic/world/" + update.state().worldId() + "/simulation/v1", update);
    }
}
