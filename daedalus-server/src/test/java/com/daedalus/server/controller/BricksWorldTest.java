// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.plugin.runtime.PluginRegistry;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.server.service.WorldHub;
import com.daedalus.server.service.WorldService;
import com.daedalus.server.web.ApiExceptionHandler;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.bricks.BricksOps;
import com.daedalus.world.gate.GateOps;
import com.daedalus.world.gate.Mount;
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

import java.nio.file.Path;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * A Bricks world over HTTP (ADR-034): born with its baseplate, spawn, runway and obby; the obby endpoint
 * matches the cubes; anyone builds on the open plate, nobody on the plate itself, the obby, the runway or
 * above the limit; the plane flies from the runway to a gate and home; the rules hold after a restart.
 */
class BricksWorldTest {

    @TempDir
    Path tmp;

    private final ObjectMapper json = new ObjectMapper();
    private final long[] clock = {3_000_000L};
    private WorldHub hub;
    private MockMvc mvc;

    @BeforeEach
    void setUp() throws Exception {
        mvc = boot();
        JsonNode made = body(mvc.perform(post("/api/v1/worlds").contentType(MediaType.APPLICATION_JSON)
                .content("{\"id\":\"studs\",\"style\":\"BRICKS\",\"seed\":11,\"title\":\"Studs\"}")));
        assertThat(made.get("result").asText()).isEqualTo("CREATED");
        hub.get("studs").useClock(() -> clock[0]);
    }

    private MockMvc boot() {
        WorldService zero = new WorldService(tmp.resolve("world-zero.daew"), e -> { });
        hub = new WorldHub(zero, e -> { });
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

    private String type(int x, int y, int z) throws Exception {
        return body(mvc.perform(get("/api/v1/world/studs/block").param("x", "" + x).param("y", "" + y)
                .param("z", "" + z))).get("type").asText();
    }

    private String place(int x, int y, int z, String type) throws Exception {
        return body(mvc.perform(put("/api/v1/world/studs/block").contentType(MediaType.APPLICATION_JSON)
                .content("{\"x\":" + x + ",\"y\":" + y + ",\"z\":" + z + ",\"type\":\"" + type + "\",\"actorId\":\"kid\"}")))
                .get("result").asText();
    }

    private JsonNode fly(String dest) throws Exception {
        return body(mvc.perform(post("/api/v1/world/studs/arks/" + WorldService.PLANE + "/voyage")
                .contentType(MediaType.APPLICATION_JSON).content(dest)));
    }

    @Test
    void aBricksWorldIsBornWithItsPlaygroundAndTheObbyEndpointMatchesTheCubes() throws Exception {
        BlockCoordinate spawn = BricksOps.spawn();
        assertThat(type(spawn.x(), spawn.y() - 1, spawn.z())).isEqualTo("SPAWN");
        assertThat(type(80, 0, -100)).isEqualTo("BASEPLATE");
        JsonNode obby = body(mvc.perform(get("/api/v1/world/studs/obby")));
        assertThat(obby.get("platforms")).hasSize(BricksOps.PLATFORMS);
        assertThat(obby.get("spawnY").asInt()).isEqualTo(spawn.y());
        for (JsonNode p : obby.get("platforms")) {
            assertThat(type(p.get("minX").asInt(), p.get("y").asInt(), p.get("minZ").asInt())).isEqualTo(p.get("type").asText());
            assertThat(type(p.get("minX").asInt(), obby.get("lavaY").asInt(), p.get("minZ").asInt())).isEqualTo("LAVA");
        }
        JsonNode f = obby.get("finish");
        assertThat(type(f.get("maxX").asInt(), f.get("y").asInt(), f.get("maxZ").asInt())).isEqualTo("BRICK_YELLOW");
        assertThat(obby.get("platforms").get(5).get("checkpoint").asBoolean()).isTrue();

        mvc.perform(get("/api/v1/world/world-zero/obby")).andExpect(status().isNotFound());
        JsonNode gates = body(mvc.perform(get("/api/v1/world/studs/gates")));
        assertThat(gates.get("mount").asText()).isEqualTo("PLANE");
        assertThat(gates.get("mountReady").asBoolean()).isTrue();
        assertThat(body(mvc.perform(post("/api/v1/world/studs/islands").contentType(MediaType.APPLICATION_JSON)
                .content("{\"seed\":3}"))).get("result").asText()).isEqualTo("WRONG_STYLE");
    }

    @Test
    void theOpenPlateIsASandboxAndTheObbyIsKeptSafe() throws Exception {
        assertThat(place(80, 1, -100, "BRICK_RED")).isEqualTo("PLACED");
        assertThat(place(80, 2, -100, "BRICK_BLUE")).isEqualTo("PLACED");
        assertThat(place(80, BricksOps.HEIGHT, -100, "BRICK_GREEN")).isEqualTo("PLACED");
        assertThat(place(80, BricksOps.HEIGHT + 1, -100, "BRICK_GREEN")).as("above the limit").isEqualTo("DENIED");
        assertThat(place(80, 0, -100, "AIR")).as("the plate itself").isEqualTo("DENIED");
        assertThat(type(80, 0, -100)).isEqualTo("BASEPLATE");
        assertThat(place(20, 6, -60, "WOOD")).as("into the obby").isEqualTo("DENIED");
        assertThat(place(48, 3, -40, "WOOD")).as("onto the runway").isEqualTo("DENIED");
        assertThat(place(-20, 1, -100, "WOOD")).as("off the plate").isEqualTo("DENIED");
        BlockCoordinate spawn = BricksOps.spawn();
        assertThat(place(spawn.x(), spawn.y() - 1, spawn.z(), "AIR")).as("the spawn").isEqualTo("DENIED");
    }

    @Test
    void thePlaneFliesFromTheRunwayToAGateAndHome() throws Exception {
        JsonNode plane = body(mvc.perform(get("/api/v1/world/studs/arks"))).get("arks").get(0);
        assertThat(plane.get("id").asText()).isEqualTo("plane-0");
        assertThat(plane.get("name").asText()).isEqualTo("Plane");
        assertThat(plane.get("slot").asInt()).isEqualTo(Mount.HOME_SLOT);
        assertThat(plane.get("x").asInt()).isEqualTo(BricksOps.hangarBerth().x());
        assertThat(plane.get("z").asInt()).isEqualTo(BricksOps.hangarBerth().z());

        assertThat(body(mvc.perform(post("/api/v1/world/studs/gates").contentType(MediaType.APPLICATION_JSON)
                .content("{\"toWorld\":\"world-zero\"}"))).get("result").asText()).isEqualTo("OPENED");
        JsonNode up = fly("{\"toGate\":0}");
        assertThat(up.get("result").asText()).isEqualTo("SAILING");
        assertThat(up.get("ark").get("toSlot").asInt()).isEqualTo(GateOps.slotOfGate(0));
        clock[0] = up.get("ark").get("arriveAt").asLong();
        JsonNode home = fly("{\"toHome\":true}");
        assertThat(home.get("result").asText()).isEqualTo("SAILING");
        assertThat(home.get("ark").get("toSlot").asInt()).isEqualTo(Mount.HOME_SLOT);
    }

    @Test
    void theRulesHoldAfterARestart() throws Exception {
        assertThat(place(70, 1, -90, "BRICK_YELLOW")).isEqualTo("PLACED");
        mvc = boot();
        assertThat(type(70, 1, -90)).isEqualTo("BRICK_YELLOW");
        assertThat(place(20, 6, -60, "WOOD")).isEqualTo("DENIED");
        assertThat(body(mvc.perform(get("/api/v1/world/studs/arks"))).get("arks").get(0).get("id").asText()).isEqualTo("plane-0");
        assertThat(body(mvc.perform(get("/api/v1/world/studs/obby"))).get("platforms")).hasSize(BricksOps.PLATFORMS);
    }
}
