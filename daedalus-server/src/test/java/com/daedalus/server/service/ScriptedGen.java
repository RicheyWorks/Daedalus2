// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.generators.GeneratorRegistry;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.springframework.context.ApplicationEventPublisher;

import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * A real {@link MazeGenerationService} whose commit can be made to fail on demand.
 *
 * <p>Both tickers ({@link TrafficService}, {@link LivingMazeService}) end a run when their
 * snapshot swap does not go through, and they distinguish two ways it can fail. {@code replace}
 * answering <em>false</em> means the entry is gone — evicted by the idle TTL or the size bound —
 * and is the documented stop signal: a run must retire rather than re-insert, because
 * re-inserting would resurrect a maze the cache deliberately dropped. A {@code replace} that
 * <em>throws</em> is the unexpected case, caught so one broken maze cannot kill the shared ticker
 * thread or spin forever logging.
 *
 * <p>{@code find} can also be made to forget an id, which is the third unreachable path:
 * {@link CampaignService} replans a campaign whose stage mazes have been evicted, and waiting for
 * a real Caffeine eviction means a size bound, a clock, and a test that measures patience.
 *
 * <p>None of these paths can be reached by ordinary use — that is what makes them worth faking. Waiting
 * for a genuine eviction means a Caffeine bound and a clock; a genuine exception means corrupting
 * something. Two flags reach both in one line, and the rest of the service stays real, so what is
 * under test is still the tick's response to a failed commit rather than a mock's idea of one.
 */
class ScriptedGen extends MazeGenerationService {

    /** When true, {@code replace} throws — the tick's {@code catch} path. */
    volatile boolean explode;

    /** When true, {@code replace} answers false without swapping — the eviction path. */
    volatile boolean refuseReplace;

    /** Ids {@code find} pretends never to have heard of — eviction, without a clock or a bound. */
    final Set<UUID> hidden = ConcurrentHashMap.newKeySet();

    ScriptedGen(GeneratorRegistry registry, ApplicationEventPublisher events) {
        super(registry, events, new SimpleMeterRegistry());
    }

    @Override
    public Cached find(UUID id) {
        return hidden.contains(id) ? null : super.find(id);
    }

    @Override
    public boolean replace(UUID id, Cached updated) {
        if (explode) {
            throw new IllegalStateException("cache swap failed");
        }
        if (refuseReplace) {
            return false;
        }
        return super.replace(id, updated);
    }
}
