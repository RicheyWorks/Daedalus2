// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.equalTo;
import static org.hamcrest.Matchers.startsWith;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.daedalus.server.web.ApiExceptionHandler;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/** Unreal's round trip (ADR-060 transport): roster + events in, fenced DTO 1 out, bad input a 400. */
class TacticsControllerTest {

    private final MockMvc mvc = MockMvcBuilders.standaloneSetup(new TacticsController(
            new com.daedalus.world.tactics.TacticsHost(), "engine", "pack-1"))
            .defaultRequest(post("/").principal(identity("engine")))
            .setControllerAdvice(new ApiExceptionHandler()).build();
    private final ObjectMapper json = new ObjectMapper();

    private static java.security.Principal identity(String name) {
        return org.springframework.security.authentication.UsernamePasswordAuthenticationToken.authenticated(
                name, "unused-test-credential", java.util.List.of());
    }

    @Test
    void refusesMissingWrongAnonymousAndUnauthenticatedCallersBeforeStateChanges() throws Exception {
        var host = new com.daedalus.world.tactics.TacticsHost();
        var guarded = MockMvcBuilders.standaloneSetup(new TacticsController(host, "engine", "pack-1")).build();
        for (java.security.Principal principal : java.util.Arrays.<java.security.Principal>asList(null,
                identity("player"), () -> "engine",
                org.springframework.security.authentication.UsernamePasswordAuthenticationToken.unauthenticated("engine", "x"),
                new org.springframework.security.authentication.AnonymousAuthenticationToken("key", "engine",
                        java.util.List.of(new org.springframework.security.core.authority.SimpleGrantedAuthority("ROLE_ANONYMOUS"))))) {
            var request = post("/api/v1/tactics/decide")
                    .header("X-Host-Subject", "engine").contentType(MediaType.APPLICATION_JSON).content(body(3, ""));
            if (principal != null) request.principal(principal);
            guarded.perform(request)
                    .andExpect(status().isForbidden());
        }
        org.assertj.core.api.Assertions.assertThat(host.squads()).isZero();
    }

    @Test
    void refusesUnconfiguredControllerAndOtherSquadWithoutCreatingState() throws Exception {
        var host = new com.daedalus.world.tactics.TacticsHost();
        for (var controller : java.util.List.of(new TacticsController(), new TacticsController(host),
                new TacticsController(host, "engine", ""), new TacticsController(host, "", "pack-1"),
                new TacticsController(host, "engine", "other"))) {
            MockMvcBuilders.standaloneSetup(controller).build().perform(post("/api/v1/tactics/decide")
                    .principal(identity("engine")).contentType(MediaType.APPLICATION_JSON).content(body(3, "")))
                    .andExpect(status().isForbidden());
        }
        org.assertj.core.api.Assertions.assertThat(host.squads()).isZero();
    }

    @Test
    void rejectedCallerCannotPrimeOrReadAuthorizedHostReceipt() throws Exception {
        var host = new com.daedalus.world.tactics.TacticsHost();
        var guarded = MockMvcBuilders.standaloneSetup(new TacticsController(host, "engine", "pack-1")).build();
        String request = body(3, "DTE 1\ntick 3\nevent PLAYER player 999 0 0 100\n");
        guarded.perform(post("/api/v1/tactics/decide").principal(identity("outsider"))
                .contentType(MediaType.APPLICATION_JSON).content(request)).andExpect(status().isForbidden());
        guarded.perform(post("/api/v1/tactics/decide").principal(identity("engine"))
                .contentType(MediaType.APPLICATION_JSON).content(body(3, "")))
                .andExpect(status().isOk()).andExpect(jsonPath("$.result", equalTo("APPLY")))
                .andExpect(jsonPath("$.why", containsString("no PLAYER")));
        guarded.perform(post("/api/v1/tactics/decide").principal(identity("outsider"))
                .contentType(MediaType.APPLICATION_JSON).content(request)).andExpect(status().isForbidden());
    }

    private static String roster(long tick) {
        return "DTR 1\nsession 0123456789ab squad pack-1 tick " + tick + "\n"
                + "unit pack-1-1 SLIME 60.0 60.0 400.0 0.0 0.0 1\n"
                + "unit pack-1-2 SLIME 10.0 60.0 900.0 100.0 0.0 1\n";
    }

    private String body(long tick, String events) throws Exception {
        return json.writeValueAsString(Map.of("roster", roster(tick), "events", events));
    }

    @Test
    void decidesFencesAndRefuses() throws Exception {
        String player = "DTE 1\ntick 3\nevent PLAYER player 0.0 0.0 0.0 100.0\n";
        mvc.perform(post("/api/v1/tactics/decide").contentType(MediaType.APPLICATION_JSON).content(body(3, player)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("APPLY")))
                .andExpect(jsonPath("$.spec", startsWith("DTO 1\nsquad pack-1 tick 3\n")))
                .andExpect(jsonPath("$.spec", containsString("order pack-1-1 ATTACK")))
                .andExpect(jsonPath("$.spec", containsString("order pack-1-2 RETREAT")));
        mvc.perform(post("/api/v1/tactics/decide").contentType(MediaType.APPLICATION_JSON).content(body(3, "")))
                .andExpect(jsonPath("$.result", equalTo("REPEAT")));
        mvc.perform(post("/api/v1/tactics/decide").contentType(MediaType.APPLICATION_JSON).content(body(2, "")))
                .andExpect(jsonPath("$.result", equalTo("STALE")))
                .andExpect(jsonPath("$.spec", equalTo("")));
        mvc.perform(post("/api/v1/tactics/decide").contentType(MediaType.APPLICATION_JSON)
                        .content(json.writeValueAsString(Map.of("roster", "DTR 9\n", "events", ""))))
                .andExpect(status().isBadRequest());
        mvc.perform(post("/api/v1/tactics/decide").contentType(MediaType.APPLICATION_JSON).content("{\"events\":\"\"}"))
                .andExpect(status().isBadRequest());
    }
}
