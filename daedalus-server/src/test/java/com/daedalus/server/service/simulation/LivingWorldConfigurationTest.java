// SPDX-License-Identifier: MIT
package com.daedalus.server.service.simulation;

import com.daedalus.server.config.LivingWorldConfiguration;
import com.daedalus.server.service.WorldHub;
import com.daedalus.world.WorldStyle;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

class LivingWorldConfigurationTest {
    @TempDir Path temp;
    @Test void optInBootAndContextRestartUseExistingWorldIdentityAndReleaseWriterLock() {
        Path file = temp.resolve("boot.simulation");
        var hub = mock(WorldHub.class);
        when(hub.worlds()).thenReturn(List.of(new WorldHub.WorldEntry("world-zero", WorldStyle.SKY_ISLANDS, 0, "World Zero")));
        var runner = new ApplicationContextRunner().withUserConfiguration(LivingWorldConfiguration.class)
                .withBean(WorldHub.class, () -> hub).withBean(MeterRegistry.class, SimpleMeterRegistry::new)
                .withPropertyValues("daedalus.simulation.file=" + file, "daedalus.simulation.steward=alice",
                        "daedalus.simulation.poll-ms=60000", "daedalus.simulation.tick-ms=60000");
        runner.run(context -> {
            assertThat(context).doesNotHaveBean(LivingWorldService.class);
            assertThat(Files.exists(file)).isFalse();
        });
        runner.withPropertyValues("daedalus.simulation.enabled=true").run(context -> {
            assertThat(context).hasNotFailed();
            context.getBean(LivingWorldService.class).supply("world-zero", "alice",
                    "00000000-0000-0000-0000-000000000001", 3);
        });
        runner.withPropertyValues("daedalus.simulation.enabled=true").run(context -> {
            assertThat(context).hasNotFailed();
            assertThat(context.getBean(LivingWorldService.class).inspect("world-zero").questCompleted()).isTrue();
        });
        runner.withPropertyValues("daedalus.simulation.enabled=true", "daedalus.simulation.world-id=missing")
                .run(context -> assertThat(context).hasFailed());
        runner.withPropertyValues("daedalus.simulation.enabled=true", "daedalus.simulation.poll-ms=0")
                .run(context -> assertThat(context).hasFailed());
        runner.withPropertyValues("daedalus.simulation.enabled=true")
                .run(context -> assertThat(context).hasNotFailed());
    }
}
