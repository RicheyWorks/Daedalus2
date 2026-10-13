// SPDX-License-Identifier: MIT
package com.daedalus.server.config;

import com.daedalus.server.controller.TacticsController;
import com.daedalus.server.service.tactics.FileTacticalCheckpoints;
import com.daedalus.world.tactics.TacticsHost;
import java.nio.file.Path;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class TacticsConfigurationTest {
    @TempDir Path temp;
    private final ApplicationContextRunner runner = new ApplicationContextRunner()
            .withUserConfiguration(TacticsConfiguration.class, TacticsController.class);
    private static String roster(String squad) {
        return "DTR 1\nsession session squad " + squad + " tick 1\nunit a SLIME 100 100 0 0 0 1\n";
    }
    private static final String EVENTS = "DTE 1\ntick 1\nevent PLAYER player 1000 0 0 100\n";
    private ApplicationContextRunner enabled() {
        return runner.withPropertyValues("daedalus.tactics.adaptive.enabled=true",
                "daedalus.tactics.host.subject=engine", "daedalus.tactics.host.squad=pack-1",
                "daedalus.tactics.adaptive.directory=" + temp);
    }

    @Test void defaultUsesBaselineWithoutCreatingStore() {
        runner.run(c -> {
            assertThat(c).hasNotFailed().hasSingleBean(TacticsHost.class).doesNotHaveBean(FileTacticalCheckpoints.class);
            assertThat(c.getBean(TacticsHost.class).decide(roster("any"), EVENTS).result()).isEqualTo(TacticsHost.Result.APPLY);
        });
    }

    @Test void enabledHttpResponseSurvivesContextAndDiskRestart() {
        var first = new AtomicReference<String>();
        for (int i = 0; i < 2; i++) {
            enabled().run(c -> {
                assertThat(c).hasNotFailed().hasSingleBean(FileTacticalCheckpoints.class);
                var mvc = MockMvcBuilders.standaloneSetup(c.getBean(TacticsController.class)).build();
                var body = new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(
                        java.util.Map.of("roster", roster("pack-1"), "events", EVENTS));
                String response = mvc.perform(post("/api/v1/tactics/decide")
                        .principal(org.springframework.security.authentication.UsernamePasswordAuthenticationToken.authenticated(
                                "engine", "unused-test-credential", java.util.List.of()))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body)).andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
                if (first.get() == null) first.set(response); else assertThat(response).isEqualTo(first.get());
                assertThatThrownBy(() -> c.getBean(TacticsHost.class).decide(roster("unconfigured"), EVENTS))
                        .isInstanceOf(IllegalArgumentException.class);
            });
        }
    }

    @Test void badCoordinatesFailStartupAndReleaseWriter() {
        enabled().withPropertyValues("daedalus.tactics.adaptive.objective-x=NaN").run(c -> assertThat(c).hasFailed());
        enabled().run(c -> assertThat(c).hasNotFailed());
    }

    @Test void enabledRequiresExplicitDirectory() {
        runner.withPropertyValues("daedalus.tactics.adaptive.enabled=true").run(c -> assertThat(c).hasFailed());
    }

    @Test void invalidHostConfigurationFailsStartupAndReleasesWriter() {
        for (String property : java.util.List.of("daedalus.tactics.host.subject=",
                "daedalus.tactics.host.squad=", "daedalus.tactics.host.squad=other")) {
            enabled().withPropertyValues(property).run(c -> assertThat(c).hasFailed()
                    .getFailure().hasRootCauseMessage(
                            "Adaptive tactics requires a host subject and matching host/adaptive squads"));
            enabled().run(c -> assertThat(c).hasNotFailed());
        }
    }
}
