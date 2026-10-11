// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.world.WorldId;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * The harbour clock (ADR-020): a single daemon thread that ties up arks whose voyages are due, so
 * the ARRIVED frame goes out when the ark arrives rather than when someone next asks. Bounded by
 * construction — one thread, one world, a 250 ms period — and stopped with the context.
 */
@Component
public class ArkHarbor {

    private static final Logger LOG = LoggerFactory.getLogger(ArkHarbor.class);
    static final long PERIOD_MS = 250;

    private final ScheduledExecutorService clock;

    public ArkHarbor(WorldService worlds) {
        this.clock = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "ark-harbor");
            t.setDaemon(true);
            return t;
        });
        clock.scheduleWithFixedDelay(() -> {
            try {
                worlds.settleArrivals(WorldId.ZERO.value());
            } catch (RuntimeException e) {
                LOG.warn("Ark harbour tick failed: {}", e.toString());
            }
        }, PERIOD_MS, PERIOD_MS, TimeUnit.MILLISECONDS);
    }

    @PreDestroy
    public void stop() {
        clock.shutdownNow();
    }
}
