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

    private final MockMvc mvc = MockMvcBuilders.standaloneSetup(new TacticsController())
            .setControllerAdvice(new ApiExceptionHandler()).build();
    private final ObjectMapper json = new ObjectMapper();

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
