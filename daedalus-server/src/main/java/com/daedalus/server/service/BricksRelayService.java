// SPDX-License-Identifier: MIT
package com.daedalus.server.service;

import com.daedalus.server.web.ResourceNotFoundException;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.WorldStyle;
import com.daedalus.world.bricks.BricksOps;
import com.daedalus.world.bricks.BricksRelay;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

/**
 * Bounded, process-local practice adapter. Enabled only by an explicit future host decision; no world
 * mutation, persistence, live broadcast, inventory, competitive timing or authoritative movement.
 */
@Service
@ConditionalOnProperty(name = "daedalus.bricks.relay.enabled", havingValue = "true")
public class BricksRelayService {
    public static final int MAX_RUNS = 128;
    public static final int MAX_RUNS_PER_OWNER = 4;
    public static final int MAX_RETRIES = 32;
    public static final long IDLE_MILLIS = 30 * 60 * 1000L;
    private final WorldHub hub;
    private final Map<UUID, Run> runs = new LinkedHashMap<>();

    public record View(UUID runId, String worldId, String version, long seed, BricksRelay.State state,
                       long elapsedMillis, BlockCoordinate respawn, BricksRelay.Stud nextStud,
                       List<String> heldStuds, List<String> bankedStuds, String ribbon) {
        public View {
            heldStuds = List.copyOf(heldStuds);
            bankedStuds = List.copyOf(bankedStuds);
        }
    }

    public record Admission(String result, View run, BricksRelay.Course course) { }

    public record Receipt(UUID commandId, String result, View run) { }

    private record Cached(long expectedRevision, BricksRelay.Command command, Receipt receipt) { }

    private static final class Run {
        private final UUID id;
        private final String world;
        private final String owner;
        private final BricksRelay.Course course;
        private final Map<UUID, Cached> retries = new LinkedHashMap<>();
        private BricksRelay.State state;
        private long touched;

        private Run(String world, String owner, BricksRelay.Course course, long now) {
            this.id = UUID.randomUUID();
            this.world = world;
            this.owner = owner;
            this.course = course;
            this.state = BricksRelay.start(now);
            this.touched = now;
        }
    }

    public BricksRelayService(WorldHub hub) {
        this.hub = hub;
    }

    /** Capacity refusal preserves every active run; one caller cannot evict someone else's practice. */
    public synchronized Admission open(String worldId, String owner) {
        requireOwner(owner);
        WorldHub.WorldEntry entry = bricks(worldId);
        long now = System.currentTimeMillis();
        expire(now);
        long owned = runs.values().stream().filter(run -> run.owner.equals(owner)).count();
        if (runs.size() >= MAX_RUNS || owned >= MAX_RUNS_PER_OWNER) {
            return new Admission("CAPACITY", null, null);
        }
        // Share an admitted immutable course. On a new seed, discard BricksOps' cube map immediately.
        BricksRelay.Course course = runs.values().stream().map(run -> run.course)
                .filter(existing -> existing.seed() == entry.seed()).findFirst()
                .orElseGet(() -> BricksRelay.course(entry.seed(), BricksOps.plan(entry.seed())));
        Run run = new Run(worldId, owner, course, now);
        runs.put(run.id, run);
        return new Admission("OPENED", view(run, now), course);
    }

    public synchronized View get(String worldId, UUID id, String owner) {
        long now = System.currentTimeMillis();
        Run run = run(worldId, id, owner, now);
        run.touched = now;
        return view(run, now);
    }

    /** Exact command replay returns its original receipt; changed payloads never reuse a command id. */
    public synchronized Receipt apply(String worldId, UUID id, String owner, UUID commandId,
                                      long expectedRevision, BricksRelay.Command command) {
        Objects.requireNonNull(commandId, "commandId");
        Objects.requireNonNull(command, "command");
        long now = System.currentTimeMillis();
        Run run = run(worldId, id, owner, now);
        run.touched = now;
        Cached cached = run.retries.get(commandId);
        if (cached != null) {
            return cached.expectedRevision() == expectedRevision && cached.command().equals(command)
                    ? cached.receipt() : new Receipt(commandId, "COMMAND_CONFLICT", view(run, now));
        }
        if (expectedRevision != run.state.revision()) {
            return new Receipt(commandId, "REVISION_CONFLICT", view(run, now));
        }
        BricksRelay.Transition transition = BricksRelay.apply(run.course, run.state, command, now);
        run.state = transition.state();
        Receipt receipt = new Receipt(commandId, transition.result().name(), view(run, now));
        run.retries.put(commandId, new Cached(expectedRevision, command, receipt));
        if (run.retries.size() > MAX_RETRIES) {
            Iterator<UUID> oldest = run.retries.keySet().iterator();
            oldest.next();
            oldest.remove();
        }
        return receipt;
    }

    public synchronized void close(String worldId, UUID id, String owner) {
        Run run = run(worldId, id, owner, System.currentTimeMillis());
        runs.remove(run.id);
    }

    private Run run(String worldId, UUID id, String owner, long now) {
        requireOwner(owner);
        expire(now);
        Run run = runs.get(id);
        if (run == null || !run.world.equals(worldId) || !run.owner.equals(owner)) {
            throw missing(id);
        }
        WorldHub.WorldEntry entry = bricks(worldId);
        if (entry.seed() != run.course.seed()) {
            runs.remove(id);
            throw missing(id);
        }
        return run;
    }

    private WorldHub.WorldEntry bricks(String worldId) {
        if (hub.get(worldId) == null || hub.style(worldId) != WorldStyle.BRICKS) {
            throw ResourceNotFoundException.world(worldId + "/bricks-relay");
        }
        return hub.worlds().stream().filter(entry -> entry.id().equals(worldId)).findFirst()
                .orElseThrow(() -> ResourceNotFoundException.world(worldId));
    }

    private void expire(long now) {
        runs.values().removeIf(run -> now - run.touched >= IDLE_MILLIS);
    }

    private static void requireOwner(String owner) {
        if (owner == null || owner.isBlank()) {
            throw new IllegalArgumentException("An authenticated practice owner is required");
        }
    }

    private static ResourceNotFoundException missing(UUID id) {
        return new ResourceNotFoundException("bricks relay", String.valueOf(id),
                "No Bricks practice run is available. Runs expire after thirty idle minutes or a host restart.");
    }

    private static View view(Run run, long now) {
        String ribbon = run.state.complete() ? (run.state.cleanRun() ? "CLEAN_CIRCUIT" : "BEACON_CARRIER") : "NONE";
        int pocket = run.state.collectedMask() & ~run.state.bankedMask();
        return new View(run.id, run.world, BricksRelay.VERSION, run.course.seed(), run.state,
                run.state.elapsedMillis(now), BricksRelay.respawn(run.course, run.state),
                BricksRelay.nextStud(run.course, run.state), BricksRelay.collectedStuds(run.course, pocket),
                BricksRelay.collectedStuds(run.course, run.state.bankedMask()), ribbon);
    }
}
