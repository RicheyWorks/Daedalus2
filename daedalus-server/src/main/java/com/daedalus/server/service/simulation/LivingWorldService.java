// SPDX-License-Identifier: MIT
package com.daedalus.server.service.simulation;

import com.daedalus.world.WorldId;
import com.daedalus.world.simulation.LivingWorld;
import com.daedalus.world.simulation.SimulationCodec;
import com.daedalus.world.simulation.SimulationTimeline;
import io.micrometer.core.instrument.MeterRegistry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;

import java.io.IOException;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;
import java.util.function.LongSupplier;

/** Single-region host. State is committed to disk before becoming visible or being published. */
public final class LivingWorldService implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(LivingWorldService.class);
    private final SimulationRepository repository;
    private final LongSupplier clock;
    private final Consumer<Update> publisher;
    private final MeterRegistry metrics;
    private SimulationCodec.Stored stored;
    private long lastRead;
    private long lastWake;
    private boolean unavailable;

    public record View(int schemaVersion, String worldId, long tick, long revision, String stateHash,
                       int cisternWater, int keeperWater, String npcId, LivingWorld.Task task, String reason,
                       boolean questCompleted, String rememberedActor, boolean drySpell, boolean active,
                       long eventSequence, List<LivingWorld.Event> events) {
        public View { events = List.copyOf(events); }
    }
    public record Update(View state, List<LivingWorld.Event> events) {
        public Update { events = List.copyOf(events); }
    }
    public record ActionResult(LivingWorld.Receipt receipt, boolean duplicate, View state) { }

    public LivingWorldService(SimulationRepository repository, WorldId world, long seed, String steward,
                              long tickMillis, LongSupplier clock, Consumer<Update> publisher,
                              MeterRegistry metrics) throws IOException {
        this.repository = Objects.requireNonNull(repository);
        this.clock = Objects.requireNonNull(clock);
        this.publisher = Objects.requireNonNull(publisher);
        this.metrics = Objects.requireNonNull(metrics);
        try {
            stored = repository.load();
            if (stored == null) {
                stored = new SimulationCodec.Stored(clock.getAsLong(), tickMillis, steward,
                        SimulationTimeline.start(LivingWorld.initial(world, seed)));
                repository.save(stored);
            } else if (!stored.timeline().state().worldId().equals(world) || stored.timeline().state().seed() != seed
                    || !stored.steward().equals(steward) || stored.tickMillis() != tickMillis) {
                throw new IOException("Configured simulation identity/rate differs from saved state");
            }
            lastRead = clock.getAsLong();
            lastWake = lastRead;
        } catch (IOException | RuntimeException e) {
            try { repository.close(); } catch (IOException closeFailure) { e.addSuppressed(closeFailure); }
            throw e;
        }
    }

    public synchronized View inspect(String world) {
        requireWorld(world);
        lastRead = clock.getAsLong();
        return view();
    }
    public synchronized ActionResult supply(String world, String authenticatedActor, String requestId, int amount) throws IOException {
        requireWorld(world);
        if (!stored.steward().equals(authenticatedActor)) throw new SecurityException("Only the authenticated settlement steward may supply water");
        var transition = commit(LivingWorld.Input.supply(requestId, authenticatedActor, amount));
        return new ActionResult(transition.receipt(), transition.duplicate(), view());
    }
    /** Host-driven tick: inactive regions wake at 10x the active interval, with identical transition rules. */
    public synchronized void advance() throws IOException {
        requireAvailable();
        long begin = System.nanoTime();
        try {
            long now = clock.getAsLong();
            if (now < stored.epochMillis()) return;
            boolean active = now - lastRead <= 30_000;
            long interval = active ? stored.tickMillis() : Math.multiplyExact(stored.tickMillis(), 10);
            if (now - lastWake < interval) return;
            commit(LivingWorld.Input.activity(active));
            var transition = commit(LivingWorld.Input.advance((now - stored.epochMillis()) / stored.tickMillis()));
            lastWake = now;
            metrics.counter("daedalus.simulation.events").increment(transition.emitted().size());
        } finally {
            metrics.timer("daedalus.simulation.tick").record(System.nanoTime() - begin, TimeUnit.NANOSECONDS);
        }
    }
    @Scheduled(fixedDelayString = "${daedalus.simulation.poll-ms:1000}")
    public void scheduledAdvance() {
        try { advance(); }
        catch (IOException | RuntimeException e) {
            metrics.counter("daedalus.simulation.failures").increment();
            LOG.error("Living world tick failed; committed state retained", e);
        }
    }
    private LivingWorld.Transition commit(LivingWorld.Input input) throws IOException {
        SimulationTimeline.Commit commit = stored.timeline().append(input);
        if (commit.timeline() == stored.timeline()) return commit.transition();
        var next = new SimulationCodec.Stored(stored.epochMillis(), stored.tickMillis(), stored.steward(), commit.timeline());
        try { repository.save(next); }
        catch (IOException failure) {
            // A transport/filesystem error can lose an acknowledgment after the atomic replacement.
            // Reconcile while still holding the writer lock before allowing a retry to overwrite it.
            try {
                var recovered = repository.load();
                byte[] bytes = recovered == null ? new byte[0] : SimulationCodec.encode(recovered);
                if (java.util.Arrays.equals(bytes, SimulationCodec.encode(next))) stored = recovered;
                else if (!java.util.Arrays.equals(bytes, SimulationCodec.encode(stored))) unavailable = true;
            } catch (IOException | RuntimeException reconciliationFailure) {
                unavailable = true;
                failure.addSuppressed(reconciliationFailure);
            }
            throw failure;
        }
        stored = next;
        try { publisher.accept(new Update(view(), commit.transition().emitted())); }
        catch (RuntimeException e) {
            metrics.counter("daedalus.simulation.publish.failures").increment();
            LOG.warn("Simulation committed but publication failed; clients must reconcile by snapshot", e);
        }
        return commit.transition();
    }
    private View view() {
        var s = stored.timeline().state();
        return new View(s.version(), s.worldId().value(), s.tick(), s.revision(), SimulationCodec.hash(s),
                s.water(), s.keeperWater(), s.npcId(), s.task(), s.reason(), s.questCompleted(), s.rememberedActor(),
                s.drySpell(), s.active(), s.eventSequence(), s.events());
    }
    private void requireWorld(String world) {
        requireAvailable();
        if (!stored.timeline().state().worldId().value().equals(world)) throw new IllegalArgumentException("Unknown simulation world");
    }
    private void requireAvailable() {
        if (unavailable) throw new IllegalStateException("Simulation writer unavailable; recover before continuing");
    }
    @Override public synchronized void close() throws IOException { unavailable = true; repository.close(); }
}
