// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.server.service.HeroService;
import com.daedalus.server.web.ApiExceptionHandler;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Heroes over HTTP (ADR-037): the server keeps the score. Beating a foe adds its EXP from the server's table;
 * a level is a choice that resets EXP; a fall costs unspent EXP; foes falling faster than a sword swings are
 * refused; the rules every client plays by are served; heroes survive a restart.
 */
class HeroControllerTest {

    @TempDir
    Path tmp;

    private final ObjectMapper json = new ObjectMapper();
    private final long[] clock = {1_000_000L};
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        mvc = boot();
    }

    private MockMvc boot() {
        HeroService heroes = new HeroService(tmp.resolve("heroes.daeh"));
        heroes.useClock(() -> clock[0]);
        return MockMvcBuilders.standaloneSetup(new HeroController(heroes)).setControllerAdvice(new ApiExceptionHandler()).build();
    }

    private JsonNode body(ResultActions r) throws Exception {
        return json.readTree(r.andExpect(status().isOk()).andReturn().getResponse().getContentAsString());
    }

    private JsonNode send(String path, String content) throws Exception {
        return body(mvc.perform(post("/api/v1/hero/" + path).contentType(MediaType.APPLICATION_JSON).content(content)));
    }

    private JsonNode beat(String foe) throws Exception {
        clock[0] += 1000;
        return send("defeat", "{\"foe\":\"" + foe + "\",\"actorId\":\"link\"}");
    }

    @Test
    void aFreshHeroAndTheRules() throws Exception {
        JsonNode h = body(mvc.perform(get("/api/v1/hero").param("actorId", "link")));
        assertThat(h.get("exp").asInt()).isZero();
        assertThat(h.get("attack").asInt()).isEqualTo(1);
        assertThat(h.get("maxLife").asInt()).as("three hearts").isEqualTo(6);
        assertThat(h.get("nextLife").asInt()).isEqualTo(50);
        assertThat(h.get("canRaise")).isEmpty();
        JsonNode rules = body(mvc.perform(get("/api/v1/hero/rules")));
        assertThat(rules.get("foes")).hasSize(4);
        assertThat(rules.get("foes").get(1).get("guard").asText()).isEqualTo("HIGH");
        assertThat(rules.get("foes").get(3).get("shifting").asBoolean()).isTrue();
        assertThat(rules.get("lifeCosts").get(0).asInt()).isEqualTo(50);
        assertThat(rules.get("attackCosts").get(6).asInt()).isEqualTo(8000);
        mvc.perform(get("/api/v1/hero").param("actorId", "no spaces")).andExpect(status().isBadRequest());
    }

    @Test
    void beatingAKnightThenChoosingLife() throws Exception {
        assertThat(beat("BLIGHT_SLIME").get("exp").asInt()).isEqualTo(2);
        JsonNode h = beat("STONE_KNIGHT");
        assertThat(h.get("result").asText()).isEqualTo("BEAT");
        assertThat(h.get("exp").asInt()).isEqualTo(52);
        assertThat(h.get("beaten").asInt()).isEqualTo(2);
        assertThat(h.get("canRaise").toString()).isEqualTo("[\"LIFE\"]");
        assertThat(send("raise", "{\"stat\":\"MAGIC\",\"actorId\":\"link\"}").get("result").asText()).isEqualTo("NOT_ENOUGH");
        JsonNode up = send("raise", "{\"stat\":\"LIFE\",\"actorId\":\"link\"}");
        assertThat(up.get("result").asText()).isEqualTo("RAISED");
        assertThat(up.get("life").asInt()).isEqualTo(2);
        assertThat(up.get("exp").asInt()).as("Zelda II: back to zero").isZero();
        assertThat(up.get("maxLife").asInt()).isEqualTo(8);
        assertThat(up.get("nextLife").asInt()).isEqualTo(150);
    }

    @Test
    void aFallCostsUnspentExpAndFoesCannotFallFasterThanASword() throws Exception {
        beat("SHARDBACK");
        beat("SHARDBACK");
        JsonNode quick = send("defeat", "{\"foe\":\"SHARDBACK\",\"actorId\":\"link\"}");
        assertThat(quick.get("result").asText()).isEqualTo("TOO_FAST");
        assertThat(quick.get("exp").asInt()).isEqualTo(10);
        JsonNode fell = send("fall", "{\"actorId\":\"link\"}");
        assertThat(fell.get("result").asText()).isEqualTo("FELL");
        assertThat(fell.get("exp").asInt()).isZero();
        assertThat(fell.get("beaten").asInt()).isEqualTo(2);
        mvc.perform(post("/api/v1/hero/defeat").contentType(MediaType.APPLICATION_JSON)
                .content("{\"foe\":\"DRAGON\",\"actorId\":\"link\"}")).andExpect(status().isBadRequest());
        mvc.perform(post("/api/v1/hero/raise").contentType(MediaType.APPLICATION_JSON)
                .content("{\"stat\":\"LUCK\",\"actorId\":\"link\"}")).andExpect(status().isBadRequest());
    }

    @Test
    void heroesSurviveARestart() throws Exception {
        beat("STONE_KNIGHT");
        send("raise", "{\"stat\":\"LIFE\",\"actorId\":\"link\"}");
        beat("DUST_WISP");
        mvc = boot();
        JsonNode h = body(mvc.perform(get("/api/v1/hero").param("actorId", "link")));
        assertThat(h.get("life").asInt()).isEqualTo(2);
        assertThat(h.get("exp").asInt()).isEqualTo(3);
        assertThat(h.get("beaten").asInt()).isEqualTo(2);
        assertThat(Files.readString(tmp.resolve("heroes.daeh"))).contains("link 3 1 1 2 2");
    }
}
