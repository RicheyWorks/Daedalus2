// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.api.dto.Hotspot;
import com.daedalus.engine.Braider;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.Sealer;
import com.daedalus.engine.WeightedMazeGrid;
import com.daedalus.plugin.events.MazeMutatedEvent;
import io.micrometer.core.instrument.MeterRegistry;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;

/**
 * Living mazes (ADR-006 / ADR-008): scheduled mutation ticks that mutate a cached maze
 * in place. Each tick copies the current snapshot ({@link MazeGrid#copy()}), opens a
 * fraction of its dead-end walls ({@link Braider}), optionally closes a fraction of
 * extra passages ({@link Sealer} — ADR-008, off unless the caller asked), drifts hotspot
 * costs on weighted grids, and commits via {@link MazeGenerationService#replace} — an
 * atomic snapshot swap, so concurrent readers are never shown a half-mutated grid and
 * no locking is needed anywhere.
 *
 * <p><b>Safe by construction.</b> Erosion only ever opens walls, so reachability can only
 * grow. Hardening only ever closes passages that are not in a spanning forest of the
 * habitable graph, so reachability cannot shrink either: a mid-run player can never be
 * walled in. ADR-006 left closing out of v1 pending that proof; the trigger (fog-of-war
 * and traffic both shipped) fired, and ADR-008 is the proof.
 *
 * <p><b>Deterministic.</b> Tick {@code n} of a run seeded {@code s} braids with seed
 * {@code s + n}, so the same maze brought to life with the same seed erodes identically —
 * the same property every generator in the project already honors.
 *
 * <p><b>Bounded everywhere</b> (house rule since the 2026-07-29 bounded-stores audit):
 * concurrent runs are capped ({@code daedalus.living.max-concurrent}), ticks per run are
 * capped ({@code daedalus.living.max-ticks}), and every run self-terminates — ticks
 * exhausted, nothing left to erode ("settled"), or the maze evicted from the cache
 * ({@code replace} answering false is the stop signal, never a resurrection).
 */
@Service
public class LivingMazeService {

    private static final Logger log = LoggerFactory.getLogger(LivingMazeService.class);

    /** Costs drift multiplicatively within this band per tick, then clamp to the API domain. */
    private static final double DRIFT_MIN = 0.75;
    private static final double DRIFT_SPAN = 0.5;
    private static final double COST_MIN = 1.0;
    private static final double COST_MAX = 1000.0;
    /** Weight changes below this are no change at all — never compare costs with {@code ==}. */
    private static final double WEIGHT_EPSILON = 1e-9;

    /** Thrown when {@code max-concurrent} living runs already exist — answered 409. */
    public static class CapacityExceededException extends RuntimeException {
        CapacityExceededException(int cap) {
            super("already animating " + cap + " mazes — retry after one settles");
        }
    }

    /**
     * A run's externally visible state.
     *
     * @param mazeId         the living maze
     * @param ticksRequested total ticks scheduled for this run
     * @param ticksDone      ticks completed so far
     * @param tickMillis     interval between ticks — lets STOMP-less clients poll honestly
     * @param active         true while the run is scheduled
     * @param settled        true once a tick found nothing to change
     */
    public record LiveStatus(UUID mazeId, int ticksRequested, int ticksDone,
                             long tickMillis, boolean active, boolean settled) {}

    private final MazeGenerationService gen;
    private final ApplicationEventPublisher events;
    private final MeterRegistry meters;
    private final Duration tickInterval;
    private final int maxTicks;
    private final int maxConcurrent;
    private final double erosionFactor;
    private final double sealFactor;

    private final ScheduledExecutorService ticker;

    private static ScheduledExecutorService daemonTicker() {
        return Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "living-maze-ticker");
            t.setDaemon(true);
            return t;
        });
    }
    private final ConcurrentHashMap<UUID, Run> runs = new ConcurrentHashMap<>();
    /**
     * Serialises first-insert against the cap. {@code compute} locks one key, so two first
     * starts on different mazes both used to see {@code size() < cap} and both insert.
     */
    private final Object admission = new Object();

    private final class Run {
        final UUID mazeId;
        final int ticks;
        final long seed;
        final double sealFactor;
        // Incremented only by the single ticker thread but read by request threads
        // (status, events). AtomicInteger rather than a volatile int: `done++` on a
        // volatile field is a read-modify-write, so it is not atomic even with one
        // writer, and SpotBugs (VO_VOLATILE_INCREMENT) is right to flag it.
        final java.util.concurrent.atomic.AtomicInteger done =
                new java.util.concurrent.atomic.AtomicInteger();
        volatile boolean settled;
        volatile ScheduledFuture<?> future; // set immediately after construction

        Run(UUID mazeId, int ticks, long seed, double sealFactor) {
            this.mazeId = mazeId;
            this.ticks = ticks;
            this.seed = seed;
            this.sealFactor = sealFactor;
        }
    }

    /**
     * @param tickInterval  wall-clock spacing between mutation ticks
     * @param maxTicks      hard per-run cap (requests asking for more are clamped)
     * @param maxConcurrent simultaneous living mazes — each run costs one scheduled task
     *                      and one grid copy per tick, so the bound is what keeps a burst
     *                      of {@code /live} calls from turning the ticker into a firehose
     * @param erosionFactor fraction of current dead ends each tick erodes; whenever any
     *                      dead end remains at least one wall opens, so runs always make
     *                      progress until the maze genuinely settles
     */
    @Autowired // two constructors now: the seam below is invisible to Spring without this
    public LivingMazeService(MazeGenerationService gen,
                             ApplicationEventPublisher events,
                             MeterRegistry meters,
                             @Value("${daedalus.living.tick-interval:2s}") Duration tickInterval,
                             @Value("${daedalus.living.max-ticks:240}") int maxTicks,
                             @Value("${daedalus.living.max-concurrent:8}") int maxConcurrent,
                             @Value("${daedalus.living.erosion-factor:0.08}") double erosionFactor,
                             @Value("${daedalus.living.seal-factor:0.0}") double sealFactor) {
        this(gen, events, meters, tickInterval, maxTicks, maxConcurrent, erosionFactor,
                sealFactor, daemonTicker());
    }

    /**
     * Test seam: real daemon ticker, hardening off. {@link LivingMazeServiceTest} uses
     * this so its clock-bound assertions stay on v1 erosion.
     */
    LivingMazeService(MazeGenerationService gen,
                      ApplicationEventPublisher events,
                      MeterRegistry meters,
                      Duration tickInterval,
                      int maxTicks,
                      int maxConcurrent,
                      double erosionFactor) {
        this(gen, events, meters, tickInterval, maxTicks, maxConcurrent, erosionFactor,
                0.0, daemonTicker());
    }

    /**
     * Scheduler seam, the same one {@link TrafficService} carries and for the same reasons.
     * This class's promises about <em>scheduling</em> — one ticker per maze however many times
     * {@code /live} is called, nothing left running when a run ends, a run that cannot commit
     * retiring instead of spinning — are not visible to a test that can only watch a clock. A
     * duplicated ticker does not fail; it erodes the maze twice as fast and outlives the run it
     * belongs to. Handing the executor in lets a test run ticks synchronously and count what is
     * still scheduled. Production behaviour is unchanged: the public constructor passes the same
     * daemon single-thread executor the field used to build inline.
     */
    LivingMazeService(MazeGenerationService gen,
                      ApplicationEventPublisher events,
                      MeterRegistry meters,
                      Duration tickInterval,
                      int maxTicks,
                      int maxConcurrent,
                      double erosionFactor,
                      ScheduledExecutorService ticker) {
        this(gen, events, meters, tickInterval, maxTicks, maxConcurrent, erosionFactor,
                0.0, ticker);
    }

    LivingMazeService(MazeGenerationService gen,
                      ApplicationEventPublisher events,
                      MeterRegistry meters,
                      Duration tickInterval,
                      int maxTicks,
                      int maxConcurrent,
                      double erosionFactor,
                      double sealFactor,
                      ScheduledExecutorService ticker) {
        this.ticker = ticker;
        this.gen = gen;
        this.events = events;
        this.meters = meters;
        this.tickInterval = tickInterval;
        this.maxTicks = maxTicks;
        this.maxConcurrent = maxConcurrent;
        this.erosionFactor = erosionFactor;
        this.sealFactor = clampUnit(sealFactor);
    }

    /**
     * Bring a maze to life. Idempotent while alive: a second call for a maze that is
     * already ticking returns the existing run's status instead of stacking a second
     * scheduler on the same grid.
     *
     * @param mazeId maze to animate; caller has verified it exists
     * @param ticks  requested tick count, clamped to {@code daedalus.living.max-ticks}
     * @param seed   erosion seed — same maze + same seed erodes identically
     * @return the run's status (freshly started, or the already-running one)
     * @throws CapacityExceededException when {@code max-concurrent} runs are live
     */
    public LiveStatus start(UUID mazeId, int ticks, long seed) {
        return start(mazeId, ticks, seed, this.sealFactor);
    }

    /**
     * Bring a maze to life, overriding the process-wide {@code seal-factor} for this run.
     * {@code 0} is v1 erosion; a positive factor hardens extra passages each tick (ADR-008).
     */
    public LiveStatus start(UUID mazeId, int ticks, long seed, double sealFactor) {
        int bounded = Math.min(Math.max(1, ticks), maxTicks);
        double seal = clampUnit(sealFactor);
        Run run;
        synchronized (admission) {
            Run existing = runs.get(mazeId);
            if (existing != null) {
                run = existing;
            } else if (runs.size() >= maxConcurrent) {
                throw new CapacityExceededException(maxConcurrent);
            } else {
                run = new Run(mazeId, bounded, seed, seal);
                runs.put(mazeId, run);
            }
        }
        // Schedule outside compute (no long work under the map's lock). The benign race —
        // two first-callers both reach here — is settled by `run.future == null` being
        // assigned only once: compute returned the same Run instance to both, and only the
        // creator sees it unscheduled. synchronized keeps that check-then-act atomic.
        synchronized (run) {
            if (run.future == null) {
                run.future = ticker.scheduleAtFixedRate(() -> tick(run),
                        tickInterval.toMillis(), tickInterval.toMillis(), TimeUnit.MILLISECONDS);
                log.info("maze {} is alive: {} ticks every {}", mazeId, run.ticks, tickInterval);
            }
        }
        return status(run);
    }

    /** Status of the given maze's run, or an inactive status if it is not living. */
    public LiveStatus status(UUID mazeId) {
        Run run = runs.get(mazeId);
        if (run == null) {
            return new LiveStatus(mazeId, 0, 0, tickInterval.toMillis(), false, false);
        }
        return status(run);
    }

    private LiveStatus status(Run run) {
        return new LiveStatus(run.mazeId, run.ticks, run.done.get(),
                tickInterval.toMillis(), runs.containsKey(run.mazeId), run.settled);
    }

    /** Number of currently living mazes — exposed for tests and metrics. */
    public int liveCount() {
        return runs.size();
    }

    /* ------------------------------------------------------------------ */
    /* The tick                                                            */
    /* ------------------------------------------------------------------ */

    private void tick(Run run) {
        try {
            MazeGenerationService.Cached current = gen.find(run.mazeId);
            if (current == null) {
                // Evicted (idle TTL / size bound) — stop quietly rather than resurrect.
                stop(run, false);
                return;
            }

            long tickSeed = run.seed + run.done.get() + 1;
            MazeGrid next = current.grid().copy();

            // Erode: open a fraction of the dead ends — at least one whenever the
            // caller asked to erode and any remain, so small mazes don't stall at
            // round(factor * few) == 0. A zero factor stays a no-op (harden-only).
            int deadEnds = Braider.deadEnds(next).size();
            double factor = 0.0;
            if (erosionFactor > 0.0 && deadEnds > 0) {
                factor = Math.max(erosionFactor, 1.0 / deadEnds);
            }
            Braider.BraidResult erosion = Braider.braid(next, factor, tickSeed);

            // Harden: close a fraction of extra (non-forest) passages — at least one
            // whenever the caller asked to harden and any extra remains. A zero factor
            // stays a no-op even if extras exist, so v1 /live is unchanged.
            Sealer.SealResult sealing = new Sealer.SealResult(0, 0, 0);
            if (run.sealFactor > 0.0) {
                int closable = Sealer.closablePassages(next).size();
                double sealF = closable == 0 ? 0.0 : Math.max(run.sealFactor, 1.0 / closable);
                sealing = Sealer.seal(next, sealF, tickSeed ^ 0x9E3779B97F4A7C15L);
            }

            // Breathe: drift hotspot costs on weighted grids, clamped to the API's domain.
            boolean weightsDrifted = false;
            List<Hotspot> hotspots = current.hotspots();
            if (next instanceof WeightedMazeGrid weighted && hotspots != null) {
                weightsDrifted = drift(weighted, tickSeed);
                hotspots = hotspotsOf(weighted);
            }

            boolean changed = erosion.wallsOpened() > 0 || sealing.wallsClosed() > 0
                    || weightsDrifted;
            boolean lastTick = run.done.get() + 1 >= run.ticks;

            if (!changed) {
                // Fully eroded, fully hardened, nothing breathing: the maze has settled.
                run.settled = true;
                events.publishEvent(new MazeMutatedEvent(this, run.mazeId, run.done.get() + 1,
                        0, 0, erosion.deadEndsAfter(), true, current.grid()));
                stop(run, true);
                return;
            }

            MazeGenerationService.Cached updated = new MazeGenerationService.Cached(
                    current.metadata(), next, current.stats(), hotspots, current.braid());
            if (!gen.replace(run.mazeId, updated)) {
                stop(run, false); // lost the race with eviction — never resurrect
                return;
            }

            int ticksDone = run.done.incrementAndGet();
            meters.counter("daedalus.living.walls-opened").increment(erosion.wallsOpened());
            if (sealing.wallsClosed() > 0) {
                meters.counter("daedalus.living.walls-closed").increment(sealing.wallsClosed());
            }
            events.publishEvent(new MazeMutatedEvent(this, run.mazeId, ticksDone,
                    erosion.wallsOpened(), sealing.wallsClosed(),
                    erosion.deadEndsAfter(), lastTick, next));
            if (lastTick) {
                stop(run, true);
            }
        } catch (RuntimeException e) {
            // A tick must never kill the shared ticker thread's schedule silently — log,
            // stop this run, let the others live.
            log.warn("living maze {} tick failed — ending its run", run.mazeId, e);
            stop(run, false);
        }
    }

    private void stop(Run run, boolean graceful) {
        runs.remove(run.mazeId);
        ScheduledFuture<?> f = run.future;
        if (f != null) {
            f.cancel(false);
        }
        if (graceful) {
            log.info("maze {} finished living after {} ticks{}", run.mazeId, run.done.get(),
                    run.settled ? " (settled)" : "");
        }
    }

    /** @return true if any weight actually changed */
    private static boolean drift(WeightedMazeGrid grid, long tickSeed) {
        Random rng = new Random(tickSeed * 0x9E3779B97F4A7C15L + 1);
        boolean changed = false;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                double w = grid.weightOf(r, c);
                if (Math.abs(w - 1.0) <= WEIGHT_EPSILON) {
                    continue; // only existing hotspots breathe; erosion never mints new ones
                }
                double drifted = Math.min(COST_MAX,
                        Math.max(COST_MIN, w * (DRIFT_MIN + DRIFT_SPAN * rng.nextDouble())));
                if (Math.abs(drifted - w) > WEIGHT_EPSILON) {
                    grid.setWeight(new com.daedalus.model.Point(r, c), drifted);
                    changed = true;
                }
            }
        }
        return changed;
    }

    private static double clampUnit(double value) {
        return Math.max(0.0, Math.min(1.0, value));
    }

    /** Rebuild the response-facing hotspot list from the grid's live weights. */
    private static List<Hotspot> hotspotsOf(WeightedMazeGrid grid) {
        List<Hotspot> out = new ArrayList<>();
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                double w = grid.weightOf(r, c);
                if (Math.abs(w - 1.0) > WEIGHT_EPSILON) {
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
