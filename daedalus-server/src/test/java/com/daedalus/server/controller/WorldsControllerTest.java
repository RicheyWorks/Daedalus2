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
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Many worlds on one server (ADR-030): a new world is mounted from a seed, grows its first island,
 * keeps its own cubes, lane, claims and sidecars apart from World Zero, publishes its own frames,
 * and comes back after a restart. Styles not yet built are named, not faked.
 */
class WorldsControllerTest {

    @TempDir
    Path tmp;

    private final ObjectMapper json = new ObjectMapper();
    private final List<Object> events = new ArrayList<>();
    private WorldHub hub;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        mvc = boot();
    }

    private MockMvc boot() {
        WorldService zero = new WorldService(tmp.resolve("world-zero.daew"), events::add);
        hub = new WorldHub(zero, events::add);
        return MockMvcBuilders.standaloneSetup(new WorldsController(hub),
                        new WorldController(hub, new PluginRegistry(),
                                new MazeGenerationService(new GeneratorRegistry(List.of(new RecursiveBacktrackerGenerator())),
                                        e -> { }, new SimpleMeterRegistry())))
                .setControllerAdvice(new ApiExceptionHandler()).build();
    }

    private JsonNode body(ResultActions r) throws Exception {
        return json.readTree(r.andExpect(status().isOk()).andReturn().getResponse().getContentAsString());
    }

    private JsonNode create(String id, String style, long seed, String title) throws Exception {
        return body(mvc.perform(post("/api/v1/worlds").contentType(MediaType.APPLICATION_JSON)
                .content("{\"id\":\"" + id + "\",\"style\":\"" + style + "\",\"seed\":" + seed + ",\"title\":\"" + title + "\"}")));
    }

    @Test
    void worldZeroIsAlwaysFirstAndEveryStyleIsListed() throws Exception {
        JsonNode r = body(mvc.perform(get("/api/v1/worlds")));
        assertThat(r.get("worlds")).hasSize(1);
        assertThat(r.get("worlds").get(0).get("id").asText()).isEqualTo("world-zero");
        assertThat(r.get("worlds").get(0).get("style").asText()).isEqualTo("SKY_ISLANDS");
        List<String> styles = new ArrayList<>();
        r.get("styles").forEach(s -> styles.add(s.get("style").asText() + ":" + s.get("ready").asBoolean()));
        assertThat(styles).containsExactly("SKY_ISLANDS:true", "PARCELS:true", "BRICKS:true", "GALLERY:true",
                "LABYRINTH:false");
    }

    @Test
    void ramIsReportedPerWorldAndPalettesBeatDenseChunks() throws Exception {
        create("gal", "gallery", 5, "Gal");
        JsonNode r = body(mvc.perform(get("/api/v1/worlds/ram")));
        assertThat(r.get("worlds")).hasSize(2);
        JsonNode gal = r.get("worlds").get(1);
        assertThat(gal.get("id").asText()).isEqualTo("gal");
        int chunks = gal.get("chunks").asInt();
        assertThat(chunks).isGreaterThan(50);
        assertThat(gal.get("uniform").asInt() + gal.get("nibble").asInt() + gal.get("dense").asInt()).isEqualTo(chunks);
        assertThat(gal.get("bytes").asLong()).isPositive().isLessThan(gal.get("denseBytes").asLong());
        assertThat(r.get("chunkBytes").asLong()).isEqualTo(
                r.get("worlds").get(0).get("bytes").asLong() + gal.get("bytes").asLong());
        assertThat(r.get("heapMax").asLong()).isGreaterThan(r.get("heapUsed").asLong()).isPositive();
    }

    @Test
    void aNewWorldIsBornWithAnIslandAndKeepsToItself() throws Exception {
        JsonNode c = create("isle-two", "sky_islands", 42, "Isle Two");
        assertThat(c.get("result").asText()).isEqualTo("CREATED");
        assertThat(c.get("world").get("islands").asInt()).isEqualTo(1);
        assertThat(c.get("world").get("title").asText()).isEqualTo("Isle Two");

        JsonNode isles = body(mvc.perform(get("/api/v1/world/isle-two/islands")));
        assertThat(isles.get("islands")).hasSize(1);
        assertThat(isles.get("islands").get(0).get("seed").asLong()).isEqualTo(42);
        assertThat(body(mvc.perform(get("/api/v1/world/world-zero/islands"))).get("islands")).isEmpty();
        assertThat(body(mvc.perform(get("/api/v1/world/isle-two/arks"))).get("arks")).hasSize(1);

        // A cube placed in one world is not in the other.
        events.clear();
        mvc.perform(put("/api/v1/world/isle-two/block").contentType(MediaType.APPLICATION_JSON)
                .content("{\"x\":5,\"y\":90,\"z\":5,\"type\":\"CRYSTAL\"}")).andExpect(status().isOk());
        assertThat(body(mvc.perform(get("/api/v1/world/isle-two/block").param("x", "5").param("y", "90").param("z", "5")))
                .get("type").asText()).isEqualTo("CRYSTAL");
        assertThat(body(mvc.perform(get("/api/v1/world/world-zero/block").param("x", "5").param("y", "90").param("z", "5")))
                .get("type").asText()).isEqualTo("AIR");
        assertThat(events).filteredOn(e -> e instanceof WorldBlockEvent)
                .allMatch(e -> ((WorldBlockEvent) e).worldId().equals("isle-two"));
        // Its files are its own.
        assertThat(Files.exists(tmp.resolve("isle-two.daew"))).isTrue();
        assertThat(Files.exists(tmp.resolve("isle-two.daew.islands"))).isTrue();
        // Claims are per world.
        assertThat(hub.get("isle-two").claimIsland("isle-two", 0, "alice").result()).isEqualTo("CLAIMED");
        assertThat(body(mvc.perform(get("/api/v1/world/isle-two/islands"))).get("islands").get(0).get("owner").asText())
                .isEqualTo("alice");
    }

    @Test
    void worldsComeBackAfterARestart() throws Exception {
        create("isle-two", "SKY_ISLANDS", 42, "Isle Two");
        mvc.perform(put("/api/v1/world/isle-two/block").contentType(MediaType.APPLICATION_JSON)
                .content("{\"x\":5,\"y\":90,\"z\":5,\"type\":\"CRYSTAL\"}")).andExpect(status().isOk());
        mvc = boot();
        JsonNode r = body(mvc.perform(get("/api/v1/worlds")));
        assertThat(r.get("worlds")).hasSize(2);
        assertThat(r.get("worlds").get(1).get("id").asText()).isEqualTo("isle-two");
        assertThat(r.get("worlds").get(1).get("islands").asInt()).as("not raised a second time").isEqualTo(1);
        assertThat(body(mvc.perform(get("/api/v1/world/isle-two/block").param("x", "5").param("y", "90").param("z", "5")))
                .get("type").asText()).isEqualTo("CRYSTAL");
        assertThat(Files.readString(tmp.resolve("worlds.registry"))).contains("isle-two SKY_ISLANDS 42 Isle Two");
    }

    @Test
    void badRequestsAreNamed() throws Exception {
        assertThat(create("isle-two", "SKY_ISLANDS", 1, "One").get("result").asText()).isEqualTo("CREATED");
        assertThat(create("isle-two", "SKY_ISLANDS", 2, "Two").get("result").asText()).isEqualTo("EXISTS");
        assertThat(create("world-zero", "SKY_ISLANDS", 2, "Zero").get("result").asText()).isEqualTo("EXISTS");
        assertThat(create("No Caps", "SKY_ISLANDS", 2, "x").get("result").asText()).isEqualTo("BAD_ID");
        assertThat(create("ab", "SKY_ISLANDS", 2, "x").get("result").asText()).isEqualTo("BAD_ID");
        assertThat(create("-dash", "SKY_ISLANDS", 2, "x").get("result").asText()).isEqualTo("BAD_ID");
        assertThat(create("maze-world", "LABYRINTH", 2, "Mazes").get("result").asText()).isEqualTo("STYLE_NOT_READY");
        assertThat(create("nowhere", "HYPERSPACE", 2, "x").get("result").asText()).isEqualTo("BAD_STYLE");
        assertThat(create("too-long-name", "SKY_ISLANDS", 2, "x".repeat(49)).get("result").asText()).isEqualTo("BAD_TITLE");
        for (int i = 0; i < WorldHub.MAX_WORLDS - 2; i++) {
            assertThat(create("w-" + i + "-x", "SKY_ISLANDS", i, "W" + i).get("result").asText()).isEqualTo("CREATED");
        }
        assertThat(create("one-more", "SKY_ISLANDS", 9, "Over").get("result").asText()).isEqualTo("FULL");
        mvc.perform(post("/api/v1/worlds").contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isBadRequest());
        mvc.perform(get("/api/v1/world/never-made/islands")).andExpect(status().isNotFound());
    }

    @Test
    void everyWorldKeepsItsOwnClock() {
        hub.create("isle-two", com.daedalus.world.WorldStyle.SKY_ISLANDS, 42, "Isle Two");
        WorldService two = hub.get("isle-two");
        assertThat(two.id().value()).isEqualTo("isle-two");
        assertThat(hub.services()).hasSize(2);
        assertThat(two.islands("world-zero")).as("a world answers only for its own id").isNull();
        assertThat(two.inspect("isle-two").get(new BlockCoordinate(0, 0, 0)).name()).isEqualTo("AIR");
    }
}
