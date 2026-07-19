// SPDX-License-Identifier: MIT

package com.daedalus.server.health;

import com.daedalus.plugin.events.PluginFailedEvent;
import com.daedalus.plugin.runtime.PluginManager;
import org.springframework.boot.health.contributor.Health;
import org.springframework.boot.health.contributor.HealthIndicator;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Reports the plugin subsystem's state as an {@code /actuator/health} component.
 *
 * <h3>Why this reports UP even when plugins have failed</h3>
 *
 * <p>This indicator is <b>deliberately never DOWN</b>. Boot aggregates component statuses into
 * the top-level status, and the top-level status is what a load balancer or Kubernetes readiness
 * probe acts on — so an indicator that reported DOWN for a broken plugin would pull a serving
 * instance out of rotation over an optional extension. The engine, the REST API and the solver
 * registry all keep working when a plugin fails to boot; that is the whole point of loading them
 * in isolation.
 *
 * <p>This is not a hypothetical concern. Earlier the same day, Boot's stock Redis indicator did
 * exactly that: it reported DOWN whenever Redis was disabled, dragging the aggregate to
 * {@code 503} on an application that was working perfectly on its in-memory backend. The fix
 * there was to stop the indicator contributing; the lesson here is to not contribute a failure
 * status in the first place.
 *
 * <p>So failures are surfaced as <em>details</em> — {@code failedPlugins}, {@code lastFailure} —
 * for a human or a dashboard to act on, while the status stays UP. If a future deployment
 * genuinely cannot serve without a particular plugin, that is a readiness concern specific to
 * that deployment and belongs in its own indicator with its own contract.
 */
@Component
public class PluginSubsystemHealthIndicator implements HealthIndicator {

    private final PluginManager pluginManager;

    /** Failures observed since startup. Plugin boot is one-shot, so this only grows. */
    private final AtomicInteger failureCount = new AtomicInteger();

    private final AtomicReference<String> lastFailure = new AtomicReference<>();

    public PluginSubsystemHealthIndicator(PluginManager pluginManager) {
        this.pluginManager = pluginManager;
    }

    /**
     * Records a plugin failure for reporting. Deliberately does not change the reported status.
     */
    @EventListener
    public void onPluginFailed(PluginFailedEvent event) {
        failureCount.incrementAndGet();
        lastFailure.set("%s@%s failed during %s at %s"
                .formatted(event.pluginId(), event.pluginVersion(), event.phase(), Instant.now()));
    }

    @Override
    public Health health() {
        Health.Builder builder = Health.up()
                .withDetail("loadedPlugins", pluginManager.loadedCount())
                .withDetail("failedPlugins", failureCount.get());

        String failure = lastFailure.get();
        if (failure != null) {
            // Present only when something actually went wrong, so a clean deployment's health
            // payload stays free of null-valued noise.
            builder.withDetail("lastFailure", failure);
        }
        return builder.build();
    }
}
