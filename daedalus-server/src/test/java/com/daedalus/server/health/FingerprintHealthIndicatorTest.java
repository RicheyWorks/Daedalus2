// SPDX-License-Identifier: MIT

package com.daedalus.server.health;

import com.daedalus.server.service.FingerprintService;
import org.junit.jupiter.api.Test;
import org.springframework.boot.health.contributor.Health;
import org.springframework.boot.health.contributor.Status;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * A thrown classifier fit is a detail, never a DOWN. Same contract as
 * {@link PluginSubsystemHealthIndicator}: an insight miss must not take the
 * instance out of rotation.
 */
class FingerprintHealthIndicatorTest {

    @Test
    void aCleanClassifierReportsNoErrorNoise() {
        FingerprintService fingerprints = mock(FingerprintService.class);
        when(fingerprints.ready()).thenReturn(true);
        when(fingerprints.lastTrainFailed()).thenReturn(false);
        when(fingerprints.lastTrainError()).thenReturn(null);

        Health health = new FingerprintHealthIndicator(fingerprints).health();
        assertThat(health.getStatus()).isEqualTo(Status.UP);
        assertThat(health.getDetails()).containsEntry("ready", true);
        assertThat(health.getDetails()).containsEntry("lastTrainFailed", false);
        assertThat(health.getDetails()).doesNotContainKey("lastTrainError");
    }

    @Test
    void aFailedFitIsDescribedWithoutChangingTheStatus() {
        FingerprintService fingerprints = mock(FingerprintService.class);
        when(fingerprints.ready()).thenReturn(false);
        when(fingerprints.lastTrainFailed()).thenReturn(true);
        when(fingerprints.lastTrainError()).thenReturn("fit boom");

        Health health = new FingerprintHealthIndicator(fingerprints).health();
        assertThat(health.getStatus())
                .as("a stuck insight must not pull the instance out of rotation")
                .isEqualTo(Status.UP);
        assertThat(health.getDetails()).containsEntry("ready", false);
        assertThat(health.getDetails()).containsEntry("lastTrainFailed", true);
        assertThat(health.getDetails()).containsEntry("lastTrainError", "fit boom");
    }
}
