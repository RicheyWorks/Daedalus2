// SPDX-License-Identifier: MIT

package com.daedalus.server.health;

import com.daedalus.plugin.events.PluginFailedEvent;
import com.daedalus.plugin.runtime.PluginManager;
import org.junit.jupiter.api.Test;
import org.springframework.boot.health.contributor.Health;
import org.springframework.boot.health.contributor.Status;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * The plugin health component reports, but never condemns.
 *
 * <p>Boot folds component statuses into the top-level status, and that is what a load balancer
 * or Kubernetes readiness probe acts on. An indicator that went DOWN for a broken optional
 * plugin would therefore pull a serving instance out of rotation — the exact failure the stock
 * Redis indicator caused earlier the same day, when a disabled Redis dragged
 * {@code /actuator/health} to 503 on an application that was working fine.
 *
 * <p>So the assertion that matters most here is the negative one: no sequence of plugin
 * failures may change the status.
 */
class PluginSubsystemHealthIndicatorTest {

    private static PluginManager managerWith(int loaded) {
        PluginManager manager = mock(PluginManager.class);
        when(manager.loadedCount()).thenReturn(loaded);
        return manager;
    }

    private static PluginFailedEvent failure(String id, PluginFailedEvent.Phase phase) {
        return new PluginFailedEvent(new Object(), id, "1.0.0", phase,
                new IllegalStateException("boom"));
    }

    @Test
    void aHealthyDeploymentReportsLoadedCountAndNoFailureNoise() {
        Health health = new PluginSubsystemHealthIndicator(managerWith(3)).health();

        assertThat(health.getStatus()).isEqualTo(Status.UP);
        assertThat(health.getDetails()).containsEntry("loadedPlugins", 3);
        assertThat(health.getDetails()).containsEntry("failedPlugins", 0);
        assertThat(health.getDetails())
                .as("a clean deployment's payload should carry no null-valued lastFailure")
                .doesNotContainKey("lastFailure");
    }

    @Test
    void failuresAreCountedAndDescribedWithoutChangingTheStatus() {
        PluginSubsystemHealthIndicator subject = new PluginSubsystemHealthIndicator(managerWith(2));

        subject.onPluginFailed(failure("broken-generator", PluginFailedEvent.Phase.INIT));
        subject.onPluginFailed(failure("worse-solver", PluginFailedEvent.Phase.START));

        Health health = subject.health();
        assertThat(health.getStatus())
                .as("a broken optional plugin must not take the instance out of rotation")
                .isEqualTo(Status.UP);
        assertThat(health.getDetails()).containsEntry("failedPlugins", 2);
        assertThat(health.getDetails().get("lastFailure").toString())
                .as("the most recent failure should be identifiable from the payload")
                .contains("worse-solver")
                .contains("START");
    }

    @Test
    void noNumberOfFailuresEverProducesADownStatus() {
        // The property this component exists to guarantee, checked to excess rather than
        // assumed from reading the implementation.
        PluginSubsystemHealthIndicator subject = new PluginSubsystemHealthIndicator(managerWith(0));

        for (int i = 0; i < 50; i++) {
            for (PluginFailedEvent.Phase phase : PluginFailedEvent.Phase.values()) {
                subject.onPluginFailed(failure("plugin-" + i, phase));
                assertThat(subject.health().getStatus()).isEqualTo(Status.UP);
            }
        }
        assertThat(subject.health().getDetails())
                .containsEntry("failedPlugins", 50 * PluginFailedEvent.Phase.values().length);
    }

    @Test
    void loadedCountIsReadLiveRatherThanCachedAtConstruction() {
        // Plugins boot after the context is built, so a count captured in the constructor would
        // always report zero.
        PluginManager manager = mock(PluginManager.class);
        when(manager.loadedCount()).thenReturn(0, 4);

        PluginSubsystemHealthIndicator subject = new PluginSubsystemHealthIndicator(manager);
        assertThat(subject.health().getDetails()).containsEntry("loadedPlugins", 0);
        assertThat(subject.health().getDetails()).containsEntry("loadedPlugins", 4);
    }
}
