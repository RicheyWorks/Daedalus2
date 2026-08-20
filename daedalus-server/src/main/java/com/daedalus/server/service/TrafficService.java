// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.api.dto.Hotspot;
import com.daedalus.engine.WeightedMazeGrid;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.AgentSteppedEvent;
import com.daedalus.plugin.events.PlayerMovedEvent;
import com.daedalus.plugin.events.TrafficPulseEvent;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;

/**
 * Traffic simulation (ADR-006 idea #3): occupancy feeds cost, cost feeds routing. Once a
 * maze's traffic is enabled, every cell a player or agent enters accumulates a pending
 * bump; a scheduled tick applies the bumps to the grid's weights (clamped at
 * {@code max-cost}) and decays every raised weight back toward the uniform {@code 1.0}.
 * Weight-aware solvers (Dijkstra, A*, Dial) consulted between pulses route around the
 * crowd — and as the crowd disperses, the shortcut reopens. Play changes routing; routing
 * (via the drawn path players tend to follow) changes play.
 *
 * <p><b>Single-writer copy-on-write</b>, the living-maze pattern: moves and steps never
 * touch the grid — they only increment pending counters — and the tick thread alone
 * copies the current snapshot ({@link WeightedMazeGrid#copy()} keeps weights), applies
 * bumps + decay, and commits via {@link MazeGenerationService#replace}. Readers keep
 * immutable snapshots; no torn weights, no locks.
 *
 * <p><b>Composition note.</b> A maze can be living <em>and</em> congested: both tickers
 * copy-and-swap the same cache entry, so a rare interleaving can cost one tick's delta
 * (both copied the same parent; the second swap wins). That is eventual-consistency by
 * design — snapshots are never corrupt, and the loser's effect simply re-derives next
 * tick (pending bumps drain only on a successful swap-side effect: bumps drained into a
 * losing snapshot are lost for one tick, at heuristic-cost stakes). Recorded rather than
 * locked away because the fix (a shared mutation ticker) costs more than the race.
 *
 * <p><b>Bounded everywhere</b>: concurrent tracked mazes ({@code max-concurrent}, 409 at
 * capacity), per-cell cost ({@code max-cost}), pending map (at most rows·cols keys), and
 * self-termination — a tracker whose maze went quiet (fully decayed, no bumps for
 * {@code quiet-ticks}) retires itself and announces {@code settled}.
 */
@Service
public class TrafficService {

    private static final Logger log = LoggerFactory.getLogger(TrafficService.class);
    private static final double UNIFORM = 1.0;
    /** Below this, a decaying weight snaps to uniform — asymptotes never finish. */
    private static final double SNAP = 1.05;
    /** Cost changes smaller than this are no change at all (weights are game-visible costs). */
    private static final double EPSILON = 1e-9;

    /** Thrown when {@code max-concurrent} tracked mazes exist — answered 409. */
    public static class CapacityExceededException extends RuntimeException {
        CapacityExceededException(int cap) {
            super("already tracking traffic on " + cap + " mazes — retry after one settles");
        }
    }

    /** @param tickMillis interval between pulses — lets STOMP-less clients poll honestly */
    public record TrafficStatus(UUID mazeId, boolean active, long tickMillis) {}

    private final MazeGenerationService gen;
    private final GameSessionService sessions;
    private final ApplicationEventPublisher events;
    private final double bump;
    private final double decayFactor;
    private final double maxCost;
    private final Duration tickInterval;
    private final int maxConcurrent;
    private final int quietTicksToStop;

    private final ScheduledExecutorService ticker;
    private final ConcurrentHashMap<UUID, Tracker> trackers = new ConcurrentHashMap<>();
    /**
     * Serialises first-insert against the cap. {@code compute} locks one key, so two first
     * enables on different mazes both used to see {@code size() < cap} and both insert.
     */
    private final Object admission = new Object();

    private static ScheduledExecutorService daemonTicker() {
        return Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "traffic-ticker");
            t.setDaemon(true);
            return t;
        });
    }

    private final class Tracker {
        final UUID mazeId;
        final ConcurrentHashMap<Point, Integer> pending = new ConcurrentHashMap<>();
        // Read and written only by the single-threaded ticker (see `ticker`), so it needs no
        // synchronisation and is deliberately NOT volatile. It used to be, which was worse
        // than useless: `++tracker.quietTicks` is a read-modify-write, so volatile bought no
        // atomicity while advertising cross-thread sharing that does not exist — exactly the
        // confusion SpotBugs flags as VO_VOLATILE_INCREMENT on LivingMazeService's tick
        // counter. That counter genuinely is shared and became an AtomicInteger; this one is
        // confined to one thread, so the honest fix is the opposite direction. Publication to
        // the ticker thread happens-before via the executor submission in enable().
        int quietTicks;
        volatile ScheduledFuture<?> future;

        Tracker(UUID mazeId) {
            this.mazeId = mazeId;
        }
    }

    /**
     * @param bump        cost added per occupancy event on the entered cell
     * @param decayFactor per-tick multiplier on the excess over uniform ({@code 0.8} halves
     *                    congestion roughly every three ticks)
     * @param maxCost     congestion ceiling per cell, kept inside the weighted-maze API's
     *                    {@code [1, 1000]} domain
     */
    @Autowired // two constructors now: the seam below is invisible to Spring without this
    public TrafficService(MazeGenerationService gen,
                          GameSessionService sessions,
                          ApplicationEventPublisher events,
                          @Value("${daedalus.traffic.bump:4.0}") double bump,
                          @Value("${daedalus.traffic.decay-factor:0.80}") double decayFactor,
                          @Value("${daedalus.traffic.max-cost:200.0}") double maxCost,
                          @Value("${daedalus.traffic.tick-interval:2s}") Duration tickInterval,
                          @Value("${daedalus.traffic.max-concurrent:8}") int maxConcurrent,
                          @Value("${daedalus.traffic.quiet-ticks:5}") int quietTicksToStop) {
        this(gen, sessions, events, bump, decayFactor, maxCost, tickInterval,
                maxConcurrent, quietTicksToStop, daemonTicker());
    }

    /**
     * Scheduler seam — the same shape as {@code GameSessionService}'s {@code Ticker}
     * constructor, and for the same reason. Every guarantee this class makes about
     * <em>scheduling</em> (one ticker per maze however many times {@code enable} is called; a
     * retired tracker leaves nothing running; a throwing tick retires rather than spins) is
     * invisible to a test that can only watch a real clock: the difference between one
     * scheduled task and two is a leak, not a failure, and the wall-clock test for it is a
     * sleep long enough to be slow and short enough to be flaky. Handing the executor in lets
     * a test run ticks synchronously and count what is still scheduled, so those become
     * assertions instead of hopes. Production behaviour is unchanged — the public constructor
     * passes the same daemon single-thread executor the field used to build inline.
     */
    TrafficService(MazeGenerationService gen,
                   GameSessionService sessions,
                   ApplicationEventPublisher events,
                   double bump,
                   double decayFactor,
                   double maxCost,
                   Duration tickInterval,
                   int maxConcurrent,
                   int quietTicksToStop,
                   ScheduledExecutorService ticker) {
        this.ticker = ticker;
        this.gen = gen;
        this.sessions = sessions;
        this.events = events;
        this.bump = bump;
        this.decayFactor = Math.max(0.0, Math.min(0.99, decayFactor));
        this.maxCost = Math.min(1000.0, maxCost);
        this.tickInterval = tickInterval;
        this.maxConcurrent = maxConcurrent;
        this.quietTicksToStop = quietTicksToStop;
    }

    /**
     * Start tracking traffic on a maze. If its grid is uniform-cost, it is wrapped into a
     * {@link WeightedMazeGrid} (topology copy, weights 1.0) and swapped into the cache so
     * the weight-aware solvers see congestion from the first pulse. Idempotent while
     * tracked.
     *
     * @return status, or {@code null} if the maze is unknown (controller answers 404)
     * @throws CapacityExceededException when {@code max-concurrent} mazes are tracked
     */
    public TrafficStatus enable(UUID mazeId) {
        var cached = gen.find(mazeId);
        if (cached == null) {
            return null;
        }
        if (!(cached.grid() instanceof WeightedMazeGrid)) {
            // Wrap-on-enable: copy topology into a weighted grid so setWeight has a home.
            WeightedMazeGrid weighted = new WeightedMazeGrid(cached.grid());
            gen.replace(mazeId, new MazeGenerationService.Cached(
                    cached.metadata(), weighted, cached.stats(), cached.hotspots(),
                    cached.braid()));
        }
        Tracker tracker;
        synchronized (admission) {
            Tracker existing = trackers.get(mazeId);
            if (existing != null) {
                tracker = existing;
            } else if (trackers.size() >= maxConcurrent) {
                throw new CapacityExceededException(maxConcurrent);
            } else {
                tracker = new Tracker(mazeId);
                trackers.put(mazeId, tracker);
            }
        }
        synchronized (tracker) {
            if (tracker.future == null) {
                tracker.future = ticker.scheduleAtFixedRate(() -> tick(tracker),
                        tickInterval.toMillis(), tickInterval.toMillis(), TimeUnit.MILLISECONDS);
                log.info("traffic tracking on maze {}: bump {}, decay {}", mazeId, bump, decayFactor);
            }
        }
        return status(mazeId);
    }

    public TrafficStatus status(UUID mazeId) {
        return new TrafficStatus(mazeId, trackers.containsKey(mazeId), tickInterval.toMillis());
    }

    /** Tracked-maze count — for tests and metrics. */
    public int trackedCount() {
        return trackers.size();
    }

    /* ------------------------------------------------------------------ */
    /* Occupancy intake — cheap counters only; the grid is never touched   */
    /* here. Both sources count identically: occupancy is occupancy.       */
    /* ------------------------------------------------------------------ */

    @EventListener
    public void onPlayerMoved(PlayerMovedEvent e) {
        var session = sessions.find(e.sessionId());
        if (session == null) {
            return;
        }
        bump(session.mazeId(), e.to());
    }

    @EventListener
    public void onAgentStepped(AgentSteppedEvent e) {
        bump(e.mazeId(), e.to());
    }

    private void bump(UUID mazeId, Point cell) {
        Tracker tracker = trackers.get(mazeId);
        if (tracker != null) {
            tracker.pending.merge(cell, 1, Integer::sum);
        }
    }

    /* ------------------------------------------------------------------ */
    /* The pulse — single writer                                           */
    /* ------------------------------------------------------------------ */

    private void tick(Tracker tracker) {
        try {
            var cached = gen.find(tracker.mazeId);
            if (cached == null || !(cached.grid() instanceof WeightedMazeGrid current)) {
                stop(tracker, false); // evicted, or someone swapped in a non-weighted grid
                return;
            }

            // Drain pending occupancy atomically per key — a bump landing mid-drain either
            // rides this tick or the next, never vanishes.
            var drained = new java.util.HashMap<Point, Integer>();
            for (Point p : tracker.pending.keySet()) {
                Integer v = tracker.pending.remove(p);
                if (v != null) {
                    drained.put(p, v);
                }
            }

            WeightedMazeGrid next = current.copy();
            boolean changed = false;

            for (var entry : drained.entrySet()) {
                Point p = entry.getKey();
                if (!next.inBounds(p)) {
                    continue;
                }
                double raised = Math.min(maxCost, next.weightOf(p.row(), p.col())
                        + bump * entry.getValue());
                next.setWeight(p, raised);
                changed = true;
            }

            int congested = 0;
            double peak = UNIFORM;
            for (int r = 0; r < next.rows(); r++) {
                for (int c = 0; c < next.cols(); c++) {
                    double w = next.weightOf(r, c);
                    if (isUniform(w)) {
                        continue; // untouched cell: nothing to decay
                    }
                    double decayed = UNIFORM + (w - UNIFORM) * decayFactor;
                    if (decayed < SNAP) {
                        decayed = UNIFORM;
                    }
                    // Compare with a tolerance, not ==. The old exact test happened to work
                    // (SNAP forces exactly UNIFORM), but it made the loop's "did anything
                    // move?" answer depend on bit-level equality of a computed double — one
                    // decay-factor change away from spinning on deltas no player could see.
                    if (Math.abs(decayed - w) > EPSILON) {
                        next.setWeight(new Point(r, c), decayed);
                        changed = true;
                    }
                    if (decayed > UNIFORM) {
                        congested++;
                        peak = Math.max(peak, decayed);
                    }
                }
            }

            if (!changed && drained.isEmpty()) {
                if (++tracker.quietTicks >= quietTicksToStop) {
                    events.publishEvent(new TrafficPulseEvent(this, tracker.mazeId,
                            congested, peak, true, current));
                    stop(tracker, true);
                }
                return;
            }
            tracker.quietTicks = 0;

            List<Hotspot> hotspots = hotspotsOf(next);
            if (!gen.replace(tracker.mazeId, new MazeGenerationService.Cached(
                    cached.metadata(), next, cached.stats(), hotspots, cached.braid()))) {
                stop(tracker, false);
                return;
            }
            events.publishEvent(new TrafficPulseEvent(this, tracker.mazeId,
                    congested, peak, false, next));
        } catch (RuntimeException e) {
            log.warn("traffic tick on maze {} failed — retiring its tracker", tracker.mazeId, e);
            stop(tracker, false);
        }
    }

    private void stop(Tracker tracker, boolean graceful) {
        trackers.remove(tracker.mazeId);
        ScheduledFuture<?> f = tracker.future;
        if (f != null) {
            f.cancel(false);
        }
        if (graceful) {
            log.info("traffic on maze {} settled — tracker retired", tracker.mazeId);
        }
    }

    /** Uniform-cost test with tolerance — see EPSILON. */
    private static boolean isUniform(double weight) {
        return Math.abs(weight - UNIFORM) <= EPSILON;
    }

    /** Response-facing hotspot list mirrors the live weights — congestion IS a hotspot. */
    private static List<Hotspot> hotspotsOf(WeightedMazeGrid grid) {
        List<Hotspot> out = new ArrayList<>();
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                double w = grid.weightOf(r, c);
                if (!isUniform(w)) {
                    out.add(new Hotspot(r, c, w));
                }
            }
        }
        return out.isEmpty() ? null : List.copyOf(out);
    }

    @PreDestroy
    void shutdown() {
        ticker.shutdownNow();
    }
}
