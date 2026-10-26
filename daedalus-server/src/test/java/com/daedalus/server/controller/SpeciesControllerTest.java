// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import static org.hamcrest.Matchers.equalTo;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class SpeciesControllerTest {

    private final MockMvc mvc = MockMvcBuilders.standaloneSetup(new SpeciesController()).build();

    @Test
    void theCanonIsServedWhole() throws Exception {
        mvc.perform(get("/api/v1/species"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.count", equalTo(221)))
                .andExpect(jsonPath("$.species", hasSize(221)))
                .andExpect(jsonPath("$.species[0].key", equalTo("red_panda")))
                .andExpect(jsonPath("$.species[0].guild", equalTo("CANOPY")))
                .andExpect(jsonPath("$.guilds.MEADOW", equalTo(76)))
                .andExpect(jsonPath("$.guilds.POND", equalTo(43)))
                .andExpect(jsonPath("$.guilds.CANOPY", equalTo(31)))
                .andExpect(jsonPath("$.guilds.DECOMPOSER", equalTo(18)))
                .andExpect(jsonPath("$.guilds.STARBORN", equalTo(22)))
                .andExpect(jsonPath("$.guilds.MARINE", equalTo(31)));
    }
}
