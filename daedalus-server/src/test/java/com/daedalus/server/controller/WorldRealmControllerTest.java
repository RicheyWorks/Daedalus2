// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.plugin.events.ArkVoyageEvent;
import com.daedalus.plugin.events.WorldBlockEvent;
import com.daedalus.plugin.runtime.PluginRegistry;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.server.service.WorldService;
import com.daedalus.server.web.ApiExceptionHandler;
import com.daedalus.world.BlockType;
import com.daedalus.world.island.IslandGenerator;
import com.daedalus.world.island.IslandOps;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.equalTo;
import static org.hamcrest.Matchers.greaterThanOrEqualTo;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The realm surface (ADR-018): chunk listing and payloads for a renderer, and the island lane.
 */
class WorldRealmControllerTest {

    @TempDir
    Path tmp;

    private final ObjectMapper json = new ObjectMapper();
    private final List<WorldBlockEvent> events = new ArrayList<>();
    private final List<ArkVoyageEvent> voyages = new ArrayList<>();
    private final long[] clock = {1_000_000L};
    private Path file;
    private MockMvc mvc;
    private WorldService worlds;

    @BeforeEach
    void setUp() {
        file = tmp.resolve("world-zero.daew");
        mvc = boot();
    }

    private MockMvc boot() {
        WorldService worlds = new WorldService(file, event -> {
            if (event instanceof WorldBlockEvent b) {
                events.add(b);
            } else if (event instanceof ArkVoyageEvent v) {
                voyages.add(v);
            }
        });
        worlds.useClock(() -> clock[0]);
        this.worlds = worlds;
        return MockMvcBuilders.standaloneSetup(new WorldController(worlds, new PluginRegistry(), mazes()))
                .setControllerAdvice(new ApiExceptionHandler())
                .build();
    }

    private static MazeGenerationService mazes() {
        return new MazeGenerationService(
                new GeneratorRegistry(List.of(new RecursiveBacktrackerGenerator())),
                event -> { }, new SimpleMeterRegistry());
    }

    private JsonNode body(org.springframework.test.web.servlet.ResultActions r) throws Exception {
        return json.readTree(r.andReturn().getResponse().getContentAsString());
    }

    @Test
    void anEmptyWorldListsNoChunksAndAnEmptyChunkIsNotPresent() throws Exception {
        mvc.perform(get("/api/v1/world/world-zero/chunks"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.worldId", equalTo("world-zero")))
                .andExpect(jsonPath("$.chunkSize", equalTo(16)))
                .andExpect(jsonPath("$.chunks", hasSize(0)));
        mvc.perform(get("/api/v1/world/world-zero/chunk/blocks").param("x", "0").param("y", "0").param("z", "0"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.present", equalTo(false)))
                .andExpect(jsonPath("$.data", equalTo("")))
                .andExpect(jsonPath("$.palette[0]", equalTo("AIR")));
    }

    @Test
    void aPlacedCubeShowsUpInTheListingAndThePayload() throws Exception {
        mvc.perform(put("/api/v1/world/world-zero/block").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"x\":-14,\"y\":3,\"z\":5,\"type\":\"blossom\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.type", equalTo("BLOSSOM")));
        mvc.perform(get("/api/v1/world/world-zero/chunks"))
                .andExpect(jsonPath("$.chunks", hasSize(1)))
                .andExpect(jsonPath("$.chunks[0].x", equalTo(-1)))
                .andExpect(jsonPath("$.chunks[0].y", equalTo(0)))
                .andExpect(jsonPath("$.chunks[0].z", equalTo(0)))
                .andExpect(jsonPath("$.chunks[0].occupied", equalTo(1)));
        JsonNode chunk = body(mvc.perform(get("/api/v1/world/world-zero/chunk/blocks")
                .param("x", "-1").param("y", "0").param("z", "0")));
        assertThat(chunk.get("present").asBoolean()).isTrue();
        byte[] data = Base64.getDecoder().decode(chunk.get("data").asText());
        assertThat(data).hasSize(4096);
        // -14 is local x 2 in chunk -1; index = x + 16 * (y + 16 * z).
        int ordinal = data[2 + 16 * (3 + 16 * 5)];
        assertThat(chunk.get("palette").get(ordinal).asText()).isEqualTo("BLOSSOM");
        int occupied = 0;
        for (byte b : data) {
            occupied += b != 0 ? 1 : 0;
        }
        assertThat(occupied).isEqualTo(1);
        assertThat(chunk.get("palette").size()).isEqualTo(BlockType.values().length);
    }

    @Test
    void raisingFillsTheLaneSlotBySlotAndAnnouncesOneRevision() throws Exception {
        mvc.perform(post("/api/v1/world/world-zero/islands").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"seed\":11}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("RAISED")))
                .andExpect(jsonPath("$.island.slot", equalTo(0)))
                .andExpect(jsonPath("$.island.x", equalTo(0)))
                .andExpect(jsonPath("$.island.y", equalTo(IslandOps.SKY_Y)))
                .andExpect(jsonPath("$.island.z", equalTo(IslandOps.SKY_Z)))
                .andExpect(jsonPath("$.island.seed", equalTo(11)))
                .andExpect(jsonPath("$.island.radius", equalTo(IslandGenerator.DEFAULT_RADIUS)))
                .andExpect(jsonPath("$.island.trees", greaterThanOrEqualTo(3)));
        long islandEvents = events.stream().filter(e -> "ISLAND".equals(e.type())).count();
        assertThat(islandEvents).isEqualTo(1);
        assertThat(events).allMatch(e -> e.kind() == WorldBlockEvent.Kind.WORLD_REVISION_CHANGED);

        mvc.perform(post("/api/v1/world/world-zero/islands").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"seed\":42,\"radius\":12}"))
                .andExpect(jsonPath("$.island.slot", equalTo(1)))
                .andExpect(jsonPath("$.island.x", equalTo(IslandOps.SLOT_SPACING)))
                .andExpect(jsonPath("$.island.radius", equalTo(12)));

        mvc.perform(get("/api/v1/world/world-zero/islands"))
                .andExpect(jsonPath("$.islands", hasSize(2)))
                .andExpect(jsonPath("$.islands[0].seed", equalTo(11)))
                .andExpect(jsonPath("$.islands[1].seed", equalTo(42)));
        int expected = IslandGenerator.generate(11).blocks().size()
                + IslandGenerator.generate(42, 12).blocks().size();
        JsonNode list = body(mvc.perform(get("/api/v1/world/world-zero/chunks")));
        int cubes = 0;
        for (JsonNode row : list.get("chunks")) {
            cubes += row.get("occupied").asInt();
        }
        assertThat(cubes).isEqualTo(expected);
    }

    @Test
    void theLaneAndItsTerrainSurviveARestart() throws Exception {
        mvc.perform(post("/api/v1/world/world-zero/islands").contentType(MediaType.APPLICATION_JSON)
                .content("{\"seed\":7}")).andExpect(status().isOk());
        String chunksBefore = body(mvc.perform(get("/api/v1/world/world-zero/chunks"))).toString();
        assertThat(Files.readString(tmp.resolve("world-zero.daew.islands"))).contains("0 7 18");

        MockMvc restarted = boot();
        restarted.perform(get("/api/v1/world/world-zero/islands"))
                .andExpect(jsonPath("$.islands", hasSize(1)))
                .andExpect(jsonPath("$.islands[0].seed", equalTo(7)));
        String chunksAfter = json.readTree(restarted.perform(get("/api/v1/world/world-zero/chunks"))
                .andReturn().getResponse().getContentAsString()).toString();
        assertThat(chunksAfter).isEqualTo(chunksBefore);
    }

    @Test
    void badIslandRequestsAreProblemsNotIslands() throws Exception {
        mvc.perform(post("/api/v1/world/world-zero/islands").contentType(MediaType.APPLICATION_JSON)
                        .content("{}"))
                .andExpect(status().isBadRequest());
        mvc.perform(post("/api/v1/world/world-zero/islands").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"seed\":1,\"radius\":99}"))
                .andExpect(status().isBadRequest());
        mvc.perform(get("/api/v1/world/world-zero/islands"))
                .andExpect(jsonPath("$.islands", hasSize(0)));
        assertThat(events).isEmpty();
    }

    @Test
    void everyIslandLaunchesAnArkMooredAtItsPier() throws Exception {
        mvc.perform(get("/api/v1/world/world-zero/arks")).andExpect(jsonPath("$.arks", hasSize(0)));
        for (String body : new String[] {"{\"seed\":11}", "{\"seed\":42,\"radius\":12}"}) {
            mvc.perform(post("/api/v1/world/world-zero/islands").contentType(MediaType.APPLICATION_JSON)
                    .content(body)).andExpect(status().isOk());
        }
        JsonNode islands = body(mvc.perform(get("/api/v1/world/world-zero/islands"))).get("islands");
        JsonNode arks = body(mvc.perform(get("/api/v1/world/world-zero/arks"))).get("arks");
        assertThat(arks.size()).isEqualTo(2);
        for (int i = 0; i < 2; i++) {
            JsonNode isle = islands.get(i);
            JsonNode ark = arks.get(i);
            assertThat(ark.get("id").asText()).isEqualTo("ark-" + isle.get("slot").asInt());
            assertThat(ark.get("name").asText()).isEqualTo(
                    com.daedalus.world.ark.ArkNames.of(isle.get("seed").asLong()));
            assertThat(ark.get("state").asText()).isEqualTo("MOORED");
            // The berth is one cube above the island's pier tip.
            assertThat(ark.get("x").asInt()).isEqualTo(isle.get("dockX").asInt());
            assertThat(ark.get("y").asInt()).isEqualTo(isle.get("dockY").asInt() + 1);
            assertThat(ark.get("z").asInt()).isEqualTo(isle.get("dockZ").asInt());
            // ...and the pier tip really is a plank in the world.
            JsonNode plank = body(mvc.perform(get("/api/v1/world/world-zero/block")
                    .param("x", isle.get("dockX").asText()).param("y", isle.get("dockY").asText())
                    .param("z", isle.get("dockZ").asText())));
            assertThat(plank.get("type").asText()).isEqualTo("WOOD");
        }
    }

    private void raise(String body) throws Exception {
        mvc.perform(post("/api/v1/world/world-zero/islands").contentType(MediaType.APPLICATION_JSON)
                .content(body)).andExpect(status().isOk());
    }

    private org.springframework.test.web.servlet.ResultActions sail(String arkId, int toSlot) throws Exception {
        return mvc.perform(post("/api/v1/world/world-zero/arks/" + arkId + "/voyage")
                .contentType(MediaType.APPLICATION_JSON).content("{\"toSlot\":" + toSlot + "}"));
    }

    @Test
    void anArkSailsBetweenIslandsOnTheServerClock() throws Exception {
        raise("{\"seed\":11}");
        raise("{\"seed\":42}");
        JsonNode isles = body(mvc.perform(get("/api/v1/world/world-zero/islands"))).get("islands");
        JsonNode order = body(sail("ark-0", 1)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("SAILING")))
                .andExpect(jsonPath("$.ark.state", equalTo("SAILING")))
                .andExpect(jsonPath("$.ark.fromSlot", equalTo(0)))
                .andExpect(jsonPath("$.ark.toSlot", equalTo(1)))
                .andExpect(jsonPath("$.ark.slot", equalTo(1))));
        long departAt = order.get("ark").get("departAt").asLong();
        long arriveAt = order.get("ark").get("arriveAt").asLong();
        assertThat(departAt).isEqualTo(clock[0]);
        assertThat(arriveAt).isGreaterThan(departAt + 4_000);
        assertThat(voyages).hasSize(1);
        assertThat(voyages.get(0).kind()).isEqualTo(ArkVoyageEvent.Kind.DEPARTED);
        // The berth reported while sailing is the destination's pier tip.
        assertThat(order.get("ark").get("x").asInt()).isEqualTo(isles.get(1).get("dockX").asInt());

        // Mid-voyage: underway is a named refusal, the list still says SAILING.
        clock[0] = (departAt + arriveAt) / 2;
        sail("ark-0", 0).andExpect(jsonPath("$.result", equalTo("UNDERWAY")));
        mvc.perform(get("/api/v1/world/world-zero/arks"))
                .andExpect(jsonPath("$.now").value(clock[0]))
                .andExpect(jsonPath("$.arks[0].state", equalTo("SAILING")));
        assertThat(worlds.settleArrivals("world-zero")).isEmpty();

        // Arrival: the harbour tick ties it up and announces it exactly once.
        clock[0] = arriveAt;
        assertThat(worlds.settleArrivals("world-zero")).hasSize(1);
        assertThat(worlds.settleArrivals("world-zero")).isEmpty();
        assertThat(voyages).hasSize(2);
        assertThat(voyages.get(1).kind()).isEqualTo(ArkVoyageEvent.Kind.ARRIVED);
        assertThat(voyages.get(1).toSlot()).isEqualTo(1);
        mvc.perform(get("/api/v1/world/world-zero/arks"))
                .andExpect(jsonPath("$.arks[0].state", equalTo("MOORED")))
                .andExpect(jsonPath("$.arks[0].slot", equalTo(1)))
                .andExpect(jsonPath("$.arks[0].homeSlot", equalTo(0)))
                .andExpect(jsonPath("$.arks[1].slot", equalTo(1)));
        sail("ark-0", 1).andExpect(jsonPath("$.result", equalTo("ALREADY_THERE")));
    }

    @Test
    void aVoyageSurvivesARestartAndArrivesAfterIt() throws Exception {
        raise("{\"seed\":11}");
        raise("{\"seed\":42}");
        long arriveAt = body(sail("ark-1", 0)).get("ark").get("arriveAt").asLong();
        assertThat(Files.readString(tmp.resolve("world-zero.daew.arks"))).contains("ark-1 0 1 0");
        MockMvc restarted = boot();
        restarted.perform(get("/api/v1/world/world-zero/arks"))
                .andExpect(jsonPath("$.arks[1].state", equalTo("SAILING")))
                .andExpect(jsonPath("$.arks[1].arriveAt").value(arriveAt));
        clock[0] = arriveAt + 1;
        restarted.perform(get("/api/v1/world/world-zero/arks"))
                .andExpect(jsonPath("$.arks[1].state", equalTo("MOORED")))
                .andExpect(jsonPath("$.arks[1].slot", equalTo(0)));
    }

    @Test
    void badVoyageOrdersAreNamedOrRefused() throws Exception {
        raise("{\"seed\":11}");
        sail("ark-0", 5).andExpect(status().isOk()).andExpect(jsonPath("$.result", equalTo("NO_SUCH_ISLAND")));
        sail("ark-9", 0).andExpect(status().isNotFound());
        sail("ark-0", 64).andExpect(status().isBadRequest());
        mvc.perform(post("/api/v1/world/world-zero/arks/ark-0/voyage").contentType(MediaType.APPLICATION_JSON)
                .content("{}")).andExpect(status().isBadRequest());
        assertThat(voyages).isEmpty();
    }

    @Test
    void unknownWorldsAre404OnEveryRealmRoute() throws Exception {
        mvc.perform(get("/api/v1/world/nope/chunks")).andExpect(status().isNotFound());
        mvc.perform(get("/api/v1/world/nope/chunk/blocks").param("x", "0").param("y", "0").param("z", "0"))
                .andExpect(status().isNotFound());
        mvc.perform(get("/api/v1/world/nope/islands")).andExpect(status().isNotFound());
        mvc.perform(get("/api/v1/world/nope/arks")).andExpect(status().isNotFound());
        mvc.perform(post("/api/v1/world/nope/arks/ark-0/voyage").contentType(MediaType.APPLICATION_JSON)
                .content("{\"toSlot\":1}")).andExpect(status().isNotFound());
        mvc.perform(post("/api/v1/world/nope/islands").contentType(MediaType.APPLICATION_JSON)
                .content("{\"seed\":1}")).andExpect(status().isNotFound());
    }

    @Test
    void anUnknownBlockTypeNamesEveryKnownOne() throws Exception {
        mvc.perform(put("/api/v1/world/world-zero/block").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"x\":0,\"y\":9,\"z\":0,\"type\":\"plasma\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detail", equalTo(
                        "Unknown block type 'plasma'. Use one of " + BlockType.names() + ".")));
        mvc.perform(get("/api/v1/world/world-zero/islands")).andExpect(jsonPath("$.islands", hasSize(0)));
    }
}
