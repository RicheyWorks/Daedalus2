// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.model.Direction;
import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.server.web.ResourceNotFoundException;
import com.daedalus.server.service.AgentWalkService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.UUID;

/**
 * Fog-of-war agent walks (ADR-006 idea #7) — the maze as a benchmark anything that speaks
 * HTTP can compete on. The agent sees only its position, the goal's coordinates, and which
 * of the four directions are open from where it stands; the grid is never in any response.
 *
 * <p>Endpoints:
 * <ul>
 *   <li>{@code POST /api/v1/maze/{id}/agent?steps=...} — open a blind walk at the start cell</li>
 *   <li>{@code POST /api/v1/agent/{id}/step?direction=NORTH} — take one step</li>
 *   <li>{@code GET  /api/v1/agent/{id}} — re-poll visibility without spending a step
 *       (essential on living mazes, whose openings change mid-walk)</li>
 * </ul>
 *
 * <p>Whole walk from a terminal:
 * <pre>
 * A=$(curl -sX POST localhost:8080/api/v1/maze/$MAZE/agent | jq -r .agentId)
 * curl -sX POST "localhost:8080/api/v1/agent/$A/step?direction=SOUTH" | jq '{position,open,arrived}'
 * </pre>
 */
@RestController
@RequestMapping("/api/v1")
@Tag(name = "Agents", description = "Blind (fog-of-war) maze walks over REST.")
@Validated
public class AgentController {

    private final AgentWalkService agents;

    public AgentController(AgentWalkService agents) {
        this.agents = agents;
    }

    @PostMapping("/maze/{id}/agent")
    @Operation(summary = "Open a fog-of-war walk on a maze: the agent sees only its own cell's openings.",
            description = "steps bounds the walk (default 4·rows·cols, capped by "
                    + "daedalus.agent.max-steps). The response never contains the grid — "
                    + "exploration is the game. Rate-limited against the 'sessionOpen' budget.")
    @PerKeyRateLimit("sessionOpen")
    public ResponseEntity<AgentWalkService.AgentView> open(
            @PathVariable UUID id,
            @RequestParam(required = false)
            @Min(value = 1, message = "steps must be at least 1")
            @Max(value = 1_000_000, message = "steps must be at most 1000000")
            Integer steps) {
        var view = agents.open(id, steps);
        if (view == null) throw ResourceNotFoundException.maze(id);
        return ResponseEntity.ok(view);
    }

    @PostMapping("/agent/{id}/step")
    @Operation(summary = "Take one step in a named direction.",
            description = "Walking into a wall answers 400 without consuming budget (the "
                    + "view already told you the openings); stepping after arrival or past "
                    + "the budget also answers 400. Validated against the maze's LIVE grid, "
                    + "so a living maze can open new routes mid-walk. Rate-limited against "
                    + "the 'agentStep' budget.")
    @PerKeyRateLimit("agentStep")
    public ResponseEntity<AgentWalkService.AgentView> step(
            @PathVariable UUID id,
            @RequestParam Direction direction) {
        var view = agents.step(id, direction);
        if (view == null) throw ResourceNotFoundException.agent(id);
        return ResponseEntity.ok(view);
    }

    @GetMapping("/agent/{id}")
    @Operation(summary = "Re-poll the agent's view without spending a step.",
            description = "On living mazes the openings at your feet can change between "
                    + "steps — polling is free and honest.")
    public ResponseEntity<AgentWalkService.AgentView> view(@PathVariable UUID id) {
        var view = agents.view(id);
        if (view == null) throw ResourceNotFoundException.agent(id);
        return ResponseEntity.ok(view);
    }
}
