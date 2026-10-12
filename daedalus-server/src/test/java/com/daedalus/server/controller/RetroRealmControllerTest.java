// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.world.retro.RetroCodec;
import com.daedalus.world.retro.RetroRealmGenerator;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import static org.hamcrest.Matchers.equalTo;
import static org.hamcrest.Matchers.startsWith;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class RetroRealmControllerTest {

    private final MockMvc mvc = MockMvcBuilders.standaloneSetup(new RetroRealmController()).build();

    @Test
    void servesTheSpecTheGeneratorWrites() throws Exception {
        String want = RetroCodec.write(RetroRealmGenerator.generate(7));
        for (int i = 0; i < 2; i++) {   // the second read comes from the kept realms, and must be the same
            mvc.perform(get("/api/v1/retro/7"))
                    .andExpect(status().isOk())
                    .andExpect(content().contentTypeCompatibleWith("text/plain"))
                    .andExpect(content().string(startsWith("DRR 1\nseed 7\n")))
                    .andExpect(content().string(equalTo(want)));
        }
        for (long s = 100; s < 120; s++) {   // more than it keeps: the oldest drop out, nothing breaks
            mvc.perform(get("/api/v1/retro/" + s)).andExpect(status().isOk());
        }
    }

    @Test
    void checksARealmCanBeFinished() throws Exception {
        mvc.perform(get("/api/v1/retro/7/check"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.finishable", equalTo(true)))
                .andExpect(jsonPath("$.doors", equalTo(4)))
                .andExpect(jsonPath("$.bossesBeaten", equalTo(1)))
                .andExpect(jsonPath("$.problems.length()", equalTo(0)));
    }

    @Test
    void aSeedMustBeANumber() throws Exception {
        mvc.perform(get("/api/v1/retro/moon")).andExpect(status().isBadRequest());
    }
}
