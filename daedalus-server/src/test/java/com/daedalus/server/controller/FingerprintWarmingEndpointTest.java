// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.server.service.FingerprintService;
import com.daedalus.server.web.ApiExceptionHandler;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.UUID;

import static org.hamcrest.Matchers.equalTo;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * First Identify is 503 with Retry-After, not a silent hang. Standalone MockMvc so the
 * advice is the thing under test — a full Boot start would pay the real 40s fit.
 */
class FingerprintWarmingEndpointTest {

    @Test
    void warmingAnswers503WithRetryAfter() throws Exception {
        FingerprintService fingerprints = mock(FingerprintService.class);
        when(fingerprints.identify(any()))
                .thenThrow(new FingerprintService.ClassifierWarmingException());
        var mvc = MockMvcBuilders.standaloneSetup(new InsightController(
                        mock(com.daedalus.server.service.MazeGenerationService.class),
                        mock(com.daedalus.server.service.GameSessionService.class),
                        mock(com.daedalus.server.service.GhostService.class),
                        mock(com.daedalus.server.service.WaypointService.class),
                        mock(com.daedalus.server.service.ComplexityLabService.class),
                        fingerprints,
                        mock(com.daedalus.server.service.HardestRouteService.class),
                        mock(com.daedalus.server.service.TopographyService.class),
                        mock(com.daedalus.server.service.TournamentService.class),
                        mock(com.daedalus.server.service.HeuristicLensService.class)))
                .setControllerAdvice(new ApiExceptionHandler())
                .build();

        mvc.perform(get("/api/v1/maze/" + UUID.randomUUID() + "/fingerprint"))
                .andExpect(status().isServiceUnavailable())
                .andExpect(header().string("Retry-After", "5"))
                .andExpect(jsonPath("$.title", equalTo("Classifier warming")))
                .andExpect(jsonPath("$.kind", equalTo("classifier-warming")));
    }
}
