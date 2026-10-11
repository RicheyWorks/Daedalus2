// SPDX-License-Identifier: MIT

package com.daedalus.server.health;

import com.daedalus.server.service.FingerprintService;
import org.springframework.boot.health.contributor.Health;
import org.springframework.boot.health.contributor.HealthIndicator;
import org.springframework.stereotype.Component;

/**
 * Reports whether the generator classifier has published a fit, without
 * condemning the instance.
 *
 * <p>A thrown train still answers 503 on identify until a later fit
 * publishes. That is a stuck insight, not a crash — so this indicator stays
 * {@code UP} and puts the last failure on the payload, the same contract as
 * {@link PluginSubsystemHealthIndicator}.
 */
@Component
public class FingerprintHealthIndicator implements HealthIndicator {

    private final FingerprintService fingerprints;

    public FingerprintHealthIndicator(FingerprintService fingerprints) {
        this.fingerprints = fingerprints;
    }

    @Override
    public Health health() {
        Health.Builder builder = Health.up()
                .withDetail("ready", fingerprints.ready())
                .withDetail("lastTrainFailed", fingerprints.lastTrainFailed());
        String error = fingerprints.lastTrainError();
        if (error != null) {
            builder.withDetail("lastTrainError", error);
        }
        return builder.build();
    }
}
