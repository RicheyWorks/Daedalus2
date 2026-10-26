// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.plugin.runtime.PluginRegistry;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.server.service.WorldService;
import com.daedalus.server.web.ApiExceptionHandler;
import com.daedalus.world.ark.ArkNames;
import com.daedalus.world.island.IslandGenerator;
import com.daedalus.world.island.IslandPortrait;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.nio.file.Path;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Island deeds (ADR-027): token metadata in the shape a marketplace reads, whose image is the
 * seed's portrait byte for byte.
 */
class IslandTokenControllerTest {

    private static final String W = "/api/v1/world/world-zero";

    @TempDir
    Path tmp;

    private final ObjectMapper json = new ObjectMapper();
    private MockMvc mvc;

    @BeforeEach
    void setUp() throws Exception {
        WorldService w = new WorldService(tmp.resolve("world-zero.daew"), event -> { });
        mvc = MockMvcBuilders.standaloneSetup(new WorldController(w, new PluginRegistry(),
                        new MazeGenerationService(new GeneratorRegistry(List.of(new RecursiveBacktrackerGenerator())),
                                event -> { }, new SimpleMeterRegistry())))
                .setControllerAdvice(new ApiExceptionHandler())
                .build();
        for (String body : new String[] {"{\"seed\":11}", "{\"seed\":42,\"radius\":12}"}) {
            mvc.perform(post(W + "/islands").contentType(MediaType.APPLICATION_JSON).content(body))
                    .andExpect(status().isOk());
        }
    }

    @Test
    void metadataIsTheErc721ShapeAndNamesTheIsland() throws Exception {
        JsonNode meta = json.readTree(mvc.perform(get(W + "/tokens/1")).andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString());
        assertThat(meta.get("name").asText()).isEqualTo("Isle 1 · " + ArkNames.of(42));
        assertThat(meta.get("description").asText()).contains("seed 42");
        assertThat(meta.get("image").asText()).isEqualTo("http://localhost" + W + "/islands/1/portrait.png");
        assertThat(meta.get("external_url").asText()).isEqualTo("http://localhost/realm.html#isle=1");
        Map<String, JsonNode> traits = new HashMap<>();
        for (JsonNode a : meta.get("attributes")) {
            traits.put(a.get("trait_type").asText(), a);
        }
        assertThat(traits.get("Seed").get("value").asText()).isEqualTo("42");
        assertThat(traits.get("Seed").has("display_type")).isFalse();
        assertThat(traits.get("Radius").get("value").asInt()).isEqualTo(12);
        assertThat(traits.get("Radius").get("display_type").asText()).isEqualTo("number");
        assertThat(traits.get("Trees").get("value").asInt()).isEqualTo(IslandGenerator.generate(42, 12).traits().trees());
        assertThat(traits.get("Ark").get("value").asText()).isEqualTo(ArkNames.of(42));
        assertThat(traits).containsKeys("Crystals", "Waterfall", "Pond", "Kinds living", "Ground columns");
    }

    @Test
    void theImageIsTheSeedsPortraitByteForByte() throws Exception {
        MockHttpServletResponse r = mvc.perform(get(W + "/islands/0/portrait.png")).andExpect(status().isOk())
                .andReturn().getResponse();
        assertThat(r.getContentType()).isEqualTo("image/png");
        assertThat(r.getHeader("Cache-Control")).contains("max-age=86400").contains("public");
        assertThat(r.getHeader("ETag")).isEqualTo("\"11-18\"");
        assertThat(r.getContentAsByteArray()).isEqualTo(IslandPortrait.of(IslandGenerator.generate(11)).png());
    }

    @Test
    void unknownTokensAndIslandsAre404() throws Exception {
        mvc.perform(get(W + "/tokens/7")).andExpect(status().isNotFound());
        mvc.perform(get(W + "/islands/7/portrait.png")).andExpect(status().isNotFound());
        mvc.perform(get("/api/v1/world/nope/tokens/0")).andExpect(status().isNotFound());
    }
}
