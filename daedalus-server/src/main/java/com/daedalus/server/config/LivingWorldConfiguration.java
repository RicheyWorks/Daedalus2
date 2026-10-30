// SPDX-License-Identifier: MIT
package com.daedalus.server.config;

import com.daedalus.server.service.WorldHub;
import com.daedalus.server.service.simulation.FileSimulationRepository;
import com.daedalus.server.service.simulation.LivingWorldService;
import com.daedalus.world.WorldId;
import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;

import java.io.IOException;
import java.nio.file.Path;

/** Opt-in host adapter. Existing worlds, ecology and packages are untouched. */
@Configuration
@EnableScheduling
@ConditionalOnProperty(name = "daedalus.simulation.enabled", havingValue = "true")
public class LivingWorldConfiguration {
    @Bean(destroyMethod = "close")
    public LivingWorldService livingWorldService(
            @Value("${daedalus.simulation.file}") Path file,
            @Value("${daedalus.simulation.world-id:world-zero}") String worldId,
            @Value("${daedalus.simulation.steward}") String steward,
            @Value("${daedalus.simulation.tick-ms:1000}") long tickMillis,
            @Value("${daedalus.simulation.poll-ms:1000}") long pollMillis,
            WorldHub worlds, ApplicationEventPublisher publisher, MeterRegistry metrics) throws IOException {
        if (pollMillis < 1) throw new IllegalArgumentException("Simulation polling interval must be positive");
        var world = worlds.worlds().stream().filter(w -> w.id().equals(worldId)).findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Simulation needs a mounted world"));
        return new LivingWorldService(new FileSimulationRepository(file), new WorldId(worldId), world.seed(), steward,
                tickMillis, System::currentTimeMillis, publisher::publishEvent, metrics);
    }
}
