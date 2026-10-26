// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.plugin.events.WorldBlockEvent;
import com.daedalus.plugin.runtime.PluginRegistry;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.server.service.WorldHub;
import com.daedalus.server.service.WorldService;
import com.daedalus.server.web.ApiExceptionHandler;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.WorldStyle;
import com.daedalus.world.gate.GateOps;
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
import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Sky gates over HTTP (ADR-031): a pair opens between two worlds, each in the clouds past its own
 * rainbow; an ark sails to its world's gate and ties up at the cloud berth, then sails home; gates
 * survive a restart; bad requests are named.
 */
class SkyGatesTest {

    @TempDir
    Path tmp;

    private final ObjectMapper json = new ObjectMapper();
    private final List<Object> events = new ArrayList<>();
    private final long[] clock = {9_000_000L};
    private WorldHub hub;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        mvc = boot();
        hub.get("world-zero").raiseIsland("world-zero", 11, 18);
        hub.create("isle-two", WorldStyle.SKY_ISLANDS, 42, "Isle Two");
    }

    private MockMvc boot() {
        WorldService zero = new WorldService(tmp.resolve("world-zero.daew"), events::add);
        hub = new WorldHub(zero, events::add);
        hub.services().forEach(w -> w.useClock(() -> clock[0]));
        return MockMvcBuilders.standaloneSetup(new WorldsController(hub),
                        new WorldController(hub, new PluginRegistry(),
                                new MazeGenerationService(new GeneratorRegistry(List.of(new RecursiveBacktrackerGenerator())),
                                        e -> { }, new SimpleMeterRegistry())))
                .setControllerAdvice(new ApiExceptionHandler()).build();
    }

    private JsonNode body(ResultActions r) throws Exception {
        return json.readTree(r.andExpect(status().isOk()).andReturn().getResponse().getContentAsString());
    }

    private JsonNode open(String from, String to) throws Exception {
        return body(mvc.perform(post("/api/v1/world/" + from + "/gates").contentType(MediaType.APPLICATION_JSON)
                .content("{\"toWorld\":\"" + to + "\"}")));
    }

    private JsonNode sail(String world, String ark, String dest) throws Exception {
        return body(mvc.perform(post("/api/v1/world/" + world + "/arks/" + ark + "/voyage")
                .contentType(MediaType.APPLICATION_JSON).content(dest)));
    }

    @Test
    void aPairOfGatesOpensInTheCloudsOfBothWorlds() throws Exception {
        events.clear();
        JsonNode o = open("world-zero", "isle-two");
        assertThat(o.get("result").asText()).isEqualTo("OPENED");
        assertThat(o.get("gate").asInt()).isZero();
        assertThat(o.get("toGate").asInt()).isZero();

        JsonNode zero = body(mvc.perform(get("/api/v1/world/world-zero/gates")));
        assertThat(zero.get("mount").asText()).isEqualTo("ARK");
        assertThat(zero.get("mountReady").asBoolean()).isTrue();
        JsonNode g = zero.get("gates").get(0);
        assertThat(g.get("toWorld").asText()).isEqualTo("isle-two");
        assertThat(g.get("toTitle").asText()).isEqualTo("Isle Two");
        assertThat(g.get("slot").asInt()).isEqualTo(1000);
        assertThat(g.get("z").asInt()).isEqualTo(GateOps.GATE_Z);
        JsonNode two = body(mvc.perform(get("/api/v1/world/isle-two/gates")));
        assertThat(two.get("gates").get(0).get("toWorld").asText()).isEqualTo("world-zero");

        // The gate is real cubes in both worlds, announced once each.
        BlockCoordinate c = GateOps.center(0);
        for (String w : new String[] {"world-zero", "isle-two"}) {
            assertThat(body(mvc.perform(get("/api/v1/world/" + w + "/block").param("x", "" + c.x())
                    .param("y", "" + c.y()).param("z", "" + c.z()))).get("type").asText()).isEqualTo("PORTAL");
        }
        assertThat(events).filteredOn(e -> e instanceof WorldBlockEvent b && "GATE".equals(b.type())).hasSize(2);
    }

    @Test
    void anArkSailsToTheGateTiesUpInTheCloudsAndSailsHome() throws Exception {
        open("world-zero", "isle-two");
        JsonNode out = sail("world-zero", "ark-0", "{\"toGate\":0}");
        assertThat(out.get("result").asText()).isEqualTo("SAILING");
        assertThat(out.get("ark").get("toSlot").asInt()).isEqualTo(1000);
        BlockCoordinate berth = GateOps.berth(0);
        assertThat(out.get("ark").get("x").asInt()).isEqualTo(berth.x());
        assertThat(out.get("ark").get("y").asInt()).isEqualTo(berth.y());
        assertThat(out.get("ark").get("z").asInt()).isEqualTo(berth.z());

        clock[0] = out.get("ark").get("arriveAt").asLong();
        JsonNode moored = body(mvc.perform(get("/api/v1/world/world-zero/arks"))).get("arks").get(0);
        assertThat(moored.get("state").asText()).isEqualTo("MOORED");
        assertThat(moored.get("slot").asInt()).isEqualTo(1000);
        assertThat(moored.get("hold").size()).as("nothing lands in the sky").isEqualTo(6);

        JsonNode home = sail("world-zero", "ark-0", "{\"toSlot\":0}");
        assertThat(home.get("result").asText()).isEqualTo("SAILING");
        assertThat(home.get("ark").get("fromSlot").asInt()).isEqualTo(1000);
    }

    @Test
    void gatesComeBackAfterARestart() throws Exception {
        open("world-zero", "isle-two");
        mvc = boot();
        assertThat(body(mvc.perform(get("/api/v1/world/isle-two/gates"))).get("gates")).hasSize(1);
        assertThat(Files.readString(tmp.resolve("world-zero.daew.gates"))).contains("0 isle-two 0");
        assertThat(sail("world-zero", "ark-0", "{\"toGate\":0}").get("result").asText()).isEqualTo("SAILING");
    }

    @Test
    void badRequestsAreNamed() throws Exception {
        assertThat(open("world-zero", "world-zero").get("result").asText()).isEqualTo("SAME_WORLD");
        assertThat(open("world-zero", "nowhere").get("result").asText()).isEqualTo("NO_SUCH_WORLD");
        assertThat(open("world-zero", "isle-two").get("result").asText()).isEqualTo("OPENED");
        assertThat(open("world-zero", "isle-two").get("result").asText()).isEqualTo("ALREADY_LINKED");
        assertThat(open("isle-two", "world-zero").get("result").asText()).isEqualTo("ALREADY_LINKED");
        assertThat(sail("world-zero", "ark-0", "{\"toGate\":3}").get("result").asText()).isEqualTo("NO_SUCH_ISLAND");
        mvc.perform(post("/api/v1/world/world-zero/arks/ark-0/voyage").contentType(MediaType.APPLICATION_JSON)
                .content("{\"toSlot\":1,\"toGate\":0}")).andExpect(status().isBadRequest());
        mvc.perform(post("/api/v1/world/world-zero/arks/ark-0/voyage").contentType(MediaType.APPLICATION_JSON)
                .content("{}")).andExpect(status().isBadRequest());
        mvc.perform(post("/api/v1/world/world-zero/arks/ark-0/voyage").contentType(MediaType.APPLICATION_JSON)
                .content("{\"toGate\":8}")).andExpect(status().isBadRequest());
        mvc.perform(get("/api/v1/world/nowhere/gates")).andExpect(status().isNotFound());
        mvc.perform(post("/api/v1/world/nowhere/gates").contentType(MediaType.APPLICATION_JSON)
                .content("{\"toWorld\":\"isle-two\"}")).andExpect(status().isNotFound());
    }

    @Test
    void aWorldRunsOutOfSkyAfterEightGates() {
        for (int i = 0; i < 8; i++) {
            hub.create("w-" + i + "-x", WorldStyle.SKY_ISLANDS, i, "W" + i);
            assertThat(hub.openGate("world-zero", "w-" + i + "-x").result()).isEqualTo("OPENED");
        }
        assertThat(hub.openGate("world-zero", "isle-two").result()).isEqualTo("FULL");
        assertThat(hub.get("isle-two").gates("isle-two")).as("no half-built pair").isEmpty();
    }
}
