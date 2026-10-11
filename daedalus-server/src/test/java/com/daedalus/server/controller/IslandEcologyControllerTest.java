// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.plugin.runtime.PluginRegistry;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.server.service.WorldService;
import com.daedalus.server.web.ApiExceptionHandler;
import com.daedalus.world.ecology.Hold;
import com.daedalus.world.ecology.SpeciesCanon;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The live ecology over HTTP (ADR-023): arks launch with founders, stowaways board where an ark
 * casts off, the hold lands where it ties up, days advance on the server clock with a bounded
 * catch-up, and the whole living state survives a restart.
 */
class IslandEcologyControllerTest {

    private static final String W = "/api/v1/world/world-zero";

    @TempDir
    Path tmp;

    private final ObjectMapper json = new ObjectMapper();
    private final long[] clock = {5_000_000L};
    private Path file;
    private MockMvc mvc;
    private WorldService worlds;

    @BeforeEach
    void setUp() {
        file = tmp.resolve("world-zero.daew");
        mvc = boot(Long.MAX_VALUE / 4);
    }

    private MockMvc boot(long dayMs) {
        WorldService w = new WorldService(file, event -> { });
        w.useClock(() -> clock[0]);
        w.useDayLength(dayMs);
        this.worlds = w;
        return MockMvcBuilders.standaloneSetup(new WorldController(w, new PluginRegistry(),
                        new MazeGenerationService(new GeneratorRegistry(List.of(new RecursiveBacktrackerGenerator())),
                                event -> { }, new SimpleMeterRegistry())))
                .setControllerAdvice(new ApiExceptionHandler())
                .build();
    }

    private JsonNode body(ResultActions r) throws Exception {
        return json.readTree(r.andReturn().getResponse().getContentAsString());
    }

    private void raise(long seed) throws Exception {
        mvc.perform(post(W + "/islands").contentType(MediaType.APPLICATION_JSON).content("{\"seed\":" + seed + "}"))
                .andExpect(status().isOk());
    }

    private JsonNode ecology(int slot) throws Exception {
        return body(mvc.perform(get(W + "/islands/" + slot + "/ecology")).andExpect(status().isOk()));
    }

    private JsonNode ark(int index) throws Exception {
        return body(mvc.perform(get(W + "/arks"))).get("arks").get(index);
    }

    private static Map<String, Double> counts(JsonNode rows) {
        Map<String, Double> out = new TreeMap<>();
        for (JsonNode r : rows) {
            out.put(r.get("key").asText(), r.get("count").asDouble());
        }
        return out;
    }

    /** Sail and wait out the voyage on the test clock; returns the voyage's arrival time. */
    private long voyage(String arkId, int toSlot) throws Exception {
        JsonNode order = body(mvc.perform(post(W + "/arks/" + arkId + "/voyage")
                .contentType(MediaType.APPLICATION_JSON).content("{\"toSlot\":" + toSlot + "}")));
        assertThat(order.get("result").asText()).isEqualTo("SAILING");
        long arriveAt = order.get("ark").get("arriveAt").asLong();
        clock[0] = arriveAt;
        worlds.settleArrivals("world-zero");
        return arriveAt;
    }

    @Test
    void aNewIslandIsBareAndItsArkCarriesFounderPairs() throws Exception {
        raise(11);
        JsonNode life = ecology(0);
        assertThat(life.get("day").asLong()).isZero();
        assertThat(life.get("richness").asInt()).isZero();
        assertThat(life.get("species").size()).isZero();
        assertThat(life.get("area").asDouble()).isPositive();
        assertThat(life.get("habitat").get("MARINE").asDouble()).isZero();
        assertThat(life.get("habitat").get("MEADOW").asDouble()).isPositive();

        Map<String, Double> hold = counts(ark(0).get("hold"));
        assertThat(hold).isEqualTo(Hold.founders(11, SpeciesCanon.get()).cargo());
        for (JsonNode row : ark(0).get("hold")) {
            assertThat(row.get("name").asText()).isEqualTo(SpeciesCanon.get().byKey(row.get("key").asText()).name());
        }
    }

    @Test
    void theHoldLandsWhereTheArkTiesUp() throws Exception {
        raise(11);
        raise(42);
        Map<String, Double> founders = counts(ark(0).get("hold"));
        voyage("ark-0", 1);

        Map<String, Double> landed = counts(ecology(1).get("species"));
        Map<String, Double> stillAboard = counts(ark(0).get("hold"));
        assertThat(landed).isNotEmpty();
        // Nothing is lost or invented in the crossing: every founder is ashore or still aboard.
        Map<String, Double> accounted = new TreeMap<>(landed);
        stillAboard.forEach((k, n) -> accounted.merge(k, n, Double::sum));
        assertThat(accounted).isEqualTo(founders);
        assertThat(ecology(0).get("richness").asInt()).isZero(); // the home island is still bare
    }

    @Test
    void daysAdvanceOnTheServerClockWithABoundedCatchUp() throws Exception {
        mvc = boot(1_000);
        raise(11);
        raise(42);
        assertThat(ecology(1).get("day").asLong()).isZero(); // the first read starts the clock
        long epoch = clock[0];
        long arrived = voyage("ark-0", 1);
        long expected = (arrived - epoch) / 1_000;
        JsonNode life = ecology(1);
        assertThat(life.get("day").asLong()).isEqualTo(expected);
        assertThat(life.get("dayMs").asLong()).isEqualTo(1_000);

        clock[0] += 30_000;
        JsonNode later = ecology(1);
        assertThat(later.get("day").asLong()).isEqualTo(expected + 30);
        assertThat(later.get("total").asDouble()).isGreaterThan(life.get("total").asDouble());

        clock[0] += 1_000_000; // a thousand days dark: one read steps only MAX_CATCH_UP of them
        assertThat(ecology(1).get("day").asLong()).isEqualTo(expected + 30 + WorldService.MAX_CATCH_UP);
        assertThat(ecology(1).get("day").asLong()).isEqualTo(expected + 30 + 2L * WorldService.MAX_CATCH_UP);
    }

    @Test
    void stowawaysBoardFromTheIslandAnArkLeaves() throws Exception {
        mvc = boot(1_000);
        raise(11);
        raise(42);
        ecology(1);
        voyage("ark-0", 1);
        clock[0] += 120_000; // let the founders take hold, then drain the bounded catch-up
        while (!worlds.tickEcology("world-zero").isEmpty()) {
            assertThat(worlds.inspect("world-zero")).isNotNull();
        }
        Map<String, Double> before = counts(ecology(1).get("species"));
        Map<String, Double> holdBefore = counts(ark(1).get("hold"));

        mvc.perform(post(W + "/arks/ark-1/voyage").contentType(MediaType.APPLICATION_JSON).content("{\"toSlot\":0}"))
                .andExpect(status().isOk());
        Map<String, Double> after = counts(ecology(1).get("species"));
        Map<String, Double> holdAfter = counts(ark(1).get("hold"));

        int boarded = 0;
        for (Map.Entry<String, Double> e : holdAfter.entrySet()) {
            double gained = e.getValue() - holdBefore.getOrDefault(e.getKey(), 0.0);
            if (gained > 0) {
                boarded++;
                assertThat(gained).isCloseTo(Hold.PAIR, within(1e-9));
                assertThat(before.get(e.getKey()) - after.getOrDefault(e.getKey(), 0.0))
                        .isCloseTo(Hold.PAIR, within(1e-9));
                assertThat(before.get(e.getKey())).isGreaterThanOrEqualTo(Hold.BOARD_MIN);
            }
        }
        assertThat(boarded).as("something strong enough boarded at casting off").isPositive();
    }

    @Test
    void theLivingWorldSurvivesARestart() throws Exception {
        mvc = boot(1_000);
        raise(11);
        raise(42);
        ecology(1);
        voyage("ark-0", 1);
        clock[0] += 40_000;
        JsonNode life = ecology(1);
        JsonNode hold = ark(0).get("hold");
        assertThat(Files.readString(tmp.resolve("world-zero.daew.ecology"))).contains("isle 1 ", "hold ark-0");

        mvc = boot(1_000);
        assertThat(ecology(1)).isEqualTo(life);
        assertThat(ark(0).get("hold")).isEqualTo(hold);
    }

    @Test
    void unknownIslandsAndWorldsAre404() throws Exception {
        raise(11);
        mvc.perform(get(W + "/islands/3/ecology")).andExpect(status().isNotFound());
        mvc.perform(get("/api/v1/world/nope/islands/0/ecology")).andExpect(status().isNotFound());
        mvc.perform(get(W + "/islands/x/ecology")).andExpect(status().isBadRequest());
    }
}
