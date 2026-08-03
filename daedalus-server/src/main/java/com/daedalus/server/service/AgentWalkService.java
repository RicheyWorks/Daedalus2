// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Direction;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.AgentSteppedEvent;
import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import com.github.benmanes.caffeine.cache.Ticker;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * Fog-of-war agent walks (ADR-006 idea #7): the maze as a benchmark for <em>blind</em>
 * solvers. An agent opened on a maze sees only three things: where it stands, where the
 * goal is (a compass, not a map), and which of the four directions are open <em>from its
 * current cell</em>. No tiles, no topology, ever — the whole point is that the caller must
 * explore. Anything that speaks HTTP can compete: a shell script, an RL policy, a student's
 * first wall-follower.
 *
 * <p><b>The maze can change under the agent's feet.</b> Visibility is recomputed from the
 * cache's <em>current</em> grid on every step and view — never from a snapshot taken at
 * open time — so a living maze (ADR-006 v1) erodes mid-walk and yesterday's wall is
 * today's shortcut. This is the composition the ADR predicted: fog-of-war is dramatically
 * better once mazes already mutate, and it costs nothing extra here.
 *
 * <p><b>Bounded everywhere</b> (house rule): the agent store is a Caffeine cache
 * ({@code daedalus.agent.max-agents} / {@code idle-ttl}) and every walk carries a step
 * budget — defaulting to {@code 4·rows·cols} (generous for any systematic exploration;
 * Trémaux needs at most 2 traversals per passage) and capped by
 * {@code daedalus.agent.max-steps}. An exhausted walk stays queryable until it idles out,
 * but takes no more steps.
 *
 * <p>Illegal moves (walking into a wall) are rejected <em>without consuming budget</em>:
 * the view already told the caller which directions are open, so a wall-bump is a caller
 * bug (answered 400), not a legitimate exploration cost.
 */
@Service
public class AgentWalkService {

    /**
     * Everything an agent is allowed to know.
     *
     * @param open           directions open from the current cell, in enum order — the fog:
     *                       this is the entire visible world
     * @param stepsRemaining budget left; 0 with {@code arrived=false} means the walk failed
     * @param arrived        the agent stands on the goal
     * @param expired        budget exhausted before arrival
     */
    public record AgentView(UUID agentId, UUID mazeId, Point position, Point goal,
                            List<Direction> open, int stepsUsed, int stepsRemaining,
                            boolean arrived, boolean expired) {}

    private record Walk(UUID id, UUID mazeId, Point position, int stepsUsed, int budget,
                        boolean arrived) {}

    private final MazeGenerationService gen;
    private final ApplicationEventPublisher events;
    private final int maxSteps;
    private final Cache<UUID, Walk> walks;

    @Autowired
    public AgentWalkService(MazeGenerationService gen,
            ApplicationEventPublisher events,
            @Value("${daedalus.agent.max-agents:10000}") long maxAgents,
            @Value("${daedalus.agent.idle-ttl:1h}") Duration idleTtl,
            @Value("${daedalus.agent.max-steps:100000}") int maxSteps) {
        this(gen, events, maxAgents, idleTtl, maxSteps, Ticker.systemTicker());
    }

    /**
     * Ticker seam — the third in this package, and the third time the same gap was found the
     * same way. {@code BoundedStoresTest} pins that every Caffeine cache in the server declares
     * a {@code maximumSize}, and a declaration is not an expiry: deleting
     * {@code expireAfterAccess} from this builder left the suite green, exactly as it did for
     * {@code GameSessionService} on 08-01 and {@code MazeGenerationService} on 08-02. An agent
     * store bounded only by size holds every walk anyone ever opened until 10,000 more arrive.
     */
    AgentWalkService(MazeGenerationService gen,
            ApplicationEventPublisher events,
            long maxAgents,
            Duration idleTtl,
            int maxSteps,
            Ticker ticker) {
        this.gen = gen;
        this.events = events;
        this.maxSteps = maxSteps;
        this.walks = Caffeine.newBuilder()
                .maximumSize(maxAgents)
                .expireAfterAccess(idleTtl)
                .ticker(ticker)
                .build();
    }

    /**
     * Open a blind walk at the maze's start cell.
     *
     * @param requestedBudget step budget, or {@code null} for the {@code 4·rows·cols}
     *                        default; clamped to {@code [1, daedalus.agent.max-steps]}
     * @return the opening view, or {@code null} if the maze is unknown (caller answers 404)
     */
    public AgentView open(UUID mazeId, Integer requestedBudget) {
        var cached = gen.find(mazeId);
        if (cached == null) {
            return null;
        }
        MazeGrid grid = cached.grid();
        int defaultBudget = 4 * grid.rows() * grid.cols();
        int budget = requestedBudget == null ? Math.min(defaultBudget, maxSteps)
                : Math.max(1, Math.min(requestedBudget, maxSteps));
        Walk walk = new Walk(UUID.randomUUID(), mazeId, grid.start(), 0,
                budget, grid.start().equals(grid.goal()));
        walks.put(walk.id(), walk);
        return view(walk, grid);
    }

    /**
     * Take one step. Atomic per agent (concurrent steps on the same walk serialize on the
     * store's compute), and validated against the maze's <em>live</em> grid.
     *
     * @return the post-step view, or {@code null} if the agent or its maze is gone (404)
     * @throws IllegalArgumentException for caller errors — walking into a wall, stepping
     *                                  after arrival, or stepping with no budget left (400)
     */
    public AgentView step(UUID agentId, Direction direction) {
        var holder = new Object() { MazeGrid grid; };
        Walk after = walks.asMap().computeIfPresent(agentId, (id, walk) -> {
            var cached = gen.find(walk.mazeId());
            if (cached == null) {
                return null; // maze evicted — the walk dies with it
            }
            MazeGrid grid = cached.grid();
            if (walk.arrived()) {
                throw new IllegalArgumentException("agent already arrived — open a new agent");
            }
            if (walk.stepsUsed() >= walk.budget()) {
                throw new IllegalArgumentException("step budget exhausted (" + walk.budget() + ")");
            }
            Point to = walk.position().step(direction);
            if (!grid.inBounds(to) || !grid.cell(walk.position()).isOpen(direction)) {
                throw new IllegalArgumentException("no opening to the " + direction + " from ("
                        + walk.position().row() + "," + walk.position().col() + ")");
            }
            holder.grid = grid;
            return new Walk(walk.id(), walk.mazeId(), to, walk.stepsUsed() + 1,
                    walk.budget(), to.equals(grid.goal()));
        });
        if (after == null) {
            return null;
        }
        // Outside the store's compute (no listener work under the map lock). Traffic
        // simulation counts this exactly like a player move — occupancy is occupancy.
        events.publishEvent(new AgentSteppedEvent(this, after.mazeId(), after.id(),
                after.position().step(direction.opposite()), after.position()));
        return view(after, holder.grid);
    }

    /**
     * Re-poll the walk without spending a step — the honest move for agents on living
     * mazes, whose openings can change between steps.
     *
     * @return current view, or {@code null} if the agent or its maze is gone (404)
     */
    public AgentView view(UUID agentId) {
        Walk walk = walks.getIfPresent(agentId);
        if (walk == null) {
            return null;
        }
        var cached = gen.find(walk.mazeId());
        if (cached == null) {
            return null;
        }
        return view(walk, cached.grid());
    }

    private static AgentView view(Walk walk, MazeGrid grid) {
        List<Direction> open = new ArrayList<>(4);
        for (Direction d : Direction.values()) {
            if (grid.cell(walk.position()).isOpen(d) && grid.inBounds(walk.position().step(d))) {
                open.add(d);
            }
        }
        return new AgentView(walk.id(), walk.mazeId(), walk.position(), grid.goal(),
                List.copyOf(open), walk.stepsUsed(),
                Math.max(0, walk.budget() - walk.stepsUsed()), walk.arrived(),
                !walk.arrived() && walk.stepsUsed() >= walk.budget());
    }
}
