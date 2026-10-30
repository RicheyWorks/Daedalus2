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
import com.daedalus.world.ParcelBounds;
import com.daedalus.world.art.MazeArt;
import com.daedalus.world.gallery.GalleryOps;
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

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Gallery City over HTTP (ADR-035): born with streets, parcels and galleries full of maze art; parcels are
 * claimed like plots and built only by their holders; a holder hangs art on their own wall and nobody else
 * can, nor on air, nor over another frame; frames survive a restart and vanish with their wall; the
 * drone flies from the Origin; the art itself is served by seed.
 */
class GalleryCityTest {

    @TempDir
    Path tmp;

    private final ObjectMapper json = new ObjectMapper();
    private final long[] clock = {4_000_000L};
    private WorldHub hub;
    private MockMvc mvc;

    @BeforeEach
    void setUp() throws Exception {
        mvc = boot();
        JsonNode made = body(mvc.perform(post("/api/v1/worlds").contentType(MediaType.APPLICATION_JSON)
                .content("{\"id\":\"origin\",\"style\":\"GALLERY\",\"seed\":3,\"title\":\"Origin City\"}")));
        assertThat(made.get("result").asText()).isEqualTo("CREATED");
        hub.get("origin").useClock(() -> clock[0]);
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

    private String place(String who, int x, int y, int z, String type) throws Exception {
        return body(mvc.perform(put("/api/v1/world/origin/block").contentType(MediaType.APPLICATION_JSON)
                .content("{\"x\":" + x + ",\"y\":" + y + ",\"z\":" + z + ",\"type\":\"" + type + "\",\"actorId\":\"" + who + "\"}")))
                .get("result").asText();
    }

    private JsonNode hang(String who, int x, int y, int z, String facing, int w, int h, long seed) throws Exception {
        return body(mvc.perform(post("/api/v1/world/origin/art").contentType(MediaType.APPLICATION_JSON)
                .content("{\"x\":" + x + ",\"y\":" + y + ",\"z\":" + z + ",\"facing\":\"" + facing + "\",\"w\":" + w
                        + ",\"h\":" + h + ",\"seed\":" + seed + ",\"title\":\"Night Maze\",\"actorId\":\"" + who + "\"}")));
    }

    /** An open parcel (no gallery), and a 4-wide, 3-high white wall built on it by its new owner. */
    private int wallOnOwnParcel(String who) throws Exception {
        JsonNode parcels = body(mvc.perform(get("/api/v1/world/origin/gallery"))).get("parcels");
        JsonNode open = null;
        for (JsonNode p : parcels) {
            if (!p.get("gallery").asBoolean()) {
                open = p;
                break;
            }
        }
        int n = open.get("n").asInt();
        assertThat(body(mvc.perform(post("/api/v1/world/origin/islands/" + n + "/claim").contentType(MediaType.APPLICATION_JSON)
                .content("{\"actorId\":\"" + who + "\"}"))).get("result").asText()).isEqualTo("CLAIMED");
        ParcelBounds b = GalleryOps.parcelBounds(n);
        for (int x = b.minX() + 2; x < b.minX() + 6; x++) {
            for (int y = 1; y <= 3; y++) {
                assertThat(place(who, x, y, b.minZ() + 2, "BRICK_WHITE")).isEqualTo("PLACED");
            }
        }
        return n;
    }

    @Test
    void aGalleryCityIsBornWithStreetsParcelsAndArtOnTheWalls() throws Exception {
        JsonNode g = body(mvc.perform(get("/api/v1/world/origin/gallery")));
        assertThat(g.get("parcels")).hasSize(GalleryOps.parcelCount());
        assertThat(g.get("streets")).hasSize(12);
        assertThat(g.get("padX").asInt()).isEqualTo(GalleryOps.padBerth().x());
        assertThat(g.get("parcels").get(0).get("address").asText()).matches("1 .+");
        JsonNode art = body(mvc.perform(get("/api/v1/world/origin/art"))).get("art");
        assertThat(art.size()).isGreaterThan(20);
        JsonNode first = art.get(0);
        assertThat(first.get("id").asText()).startsWith("show-");
        assertThat(first.get("owner").asText()).isEmpty();
        assertThat(first.get("title").asText()).isEqualTo(MazeArt.of(first.get("seed").asLong()).title());
        assertThat(first.get("image").asText()).isEqualTo("/api/v1/art/maze/" + first.get("seed").asLong() + ".png");
        byte[] png = mvc.perform(get(first.get("image").asText()))
                .andExpect(status().isOk()).andExpect(header().string("Content-Type", "image/png"))
                .andReturn().getResponse().getContentAsByteArray();
        assertThat(png).isEqualTo(MazeArt.of(first.get("seed").asLong()).png());

        JsonNode gates = body(mvc.perform(get("/api/v1/world/origin/gates")));
        assertThat(gates.get("mount").asText()).isEqualTo("DRONE");
        JsonNode drone = body(mvc.perform(get("/api/v1/world/origin/arks"))).get("arks").get(0);
        assertThat(drone.get("id").asText()).isEqualTo("drone-0");
        assertThat(drone.get("name").asText()).isEqualTo("Drone");
        assertThat(drone.get("slot").asInt()).isEqualTo(Mount.HOME_SLOT);
        mvc.perform(get("/api/v1/world/world-zero/gallery")).andExpect(status().isNotFound());
        assertThat(body(mvc.perform(get("/api/v1/world/world-zero/art"))).get("art")).isEmpty();
    }

    @Test
    void parcelsAreBuiltOnlyByTheirHoldersAndUnderTheirHeight() throws Exception {
        GalleryOps.Parcel p = GalleryOps.parcels().get(0);
        ParcelBounds b = p.bounds();
        assertThat(place("ana", b.minX(), 1, b.minZ(), "WOOD")).as("unclaimed").isEqualTo("DENIED");
        assertThat(body(mvc.perform(post("/api/v1/world/origin/islands/0/claim").contentType(MediaType.APPLICATION_JSON)
                .content("{\"actorId\":\"ana\"}"))).get("result").asText()).isEqualTo("CLAIMED");
        assertThat(place("ana", b.minX(), 1, b.minZ(), "WOOD")).isEqualTo("PLACED");
        assertThat(place("bo", b.minX(), 2, b.minZ(), "WOOD")).isEqualTo("DENIED");
        assertThat(place("ana", b.minX(), b.maxY() + 1, b.minZ(), "WOOD")).as("over the height").isEqualTo("DENIED");
        BlockCoordinate pad = GalleryOps.padBerth();
        assertThat(place("ana", pad.x(), 1, pad.z(), "WOOD")).as("the Origin").isEqualTo("DENIED");
        assertThat(body(mvc.perform(post("/api/v1/world/origin/islands/999/claim").contentType(MediaType.APPLICATION_JSON)
                .content("{\"actorId\":\"ana\"}"))).get("result").asText()).isEqualTo("NO_SUCH_PARCEL");
    }

    @Test
    void aHolderHangsArtOnTheirOwnWallAndNobodyElseCan() throws Exception {
        int n = wallOnOwnParcel("ana");
        ParcelBounds b = GalleryOps.parcelBounds(n);
        int x = b.minX() + 2;
        int z = b.minZ() + 2;
        assertThat(hang("bo", x, 1, z, "SOUTH", 3, 2, 77).get("result").asText()).isEqualTo("NOT_YOURS");
        assertThat(hang("ana", x, 1, z, "SOUTH", 5, 2, 77).get("result").asText()).as("past the wall's end").isEqualTo("NO_WALL");
        assertThat(hang("ana", x, 1, z + 1, "SOUTH", 2, 2, 77).get("result").asText()).as("on air").isEqualTo("NO_WALL");
        JsonNode hung = hang("ana", x, 1, z, "SOUTH", 3, 2, 77);
        assertThat(hung.get("result").asText()).isEqualTo("HUNG");
        assertThat(hung.get("art").get("owner").asText()).isEqualTo("ana");
        assertThat(hung.get("art").get("address").asText()).isEqualTo(GalleryOps.parcels().get(n).address());
        assertThat(hang("ana", x + 2, 2, z, "SOUTH", 1, 1, 78).get("result").asText()).isEqualTo("OVERLAP");
        assertThat(hang("ana", x, 1, z, "NORTH", 2, 2, 79).get("result").asText()).as("the other face is free").isEqualTo("HUNG");
        String id = hung.get("art").get("id").asText();
        assertThat(body(mvc.perform(get("/api/v1/world/origin/art"))).get("art").toString()).contains(id);
        assertThat(Files.readString(tmp.resolve("origin.daew.art"))).contains(id + " " + x + " 1 " + z + " SOUTH 3 2 77 ana Night Maze");

        assertThat(body(mvc.perform(delete("/api/v1/world/origin/art/" + id).param("actorId", "bo"))).get("result").asText())
                .isEqualTo("NOT_YOURS");
        assertThat(body(mvc.perform(delete("/api/v1/world/origin/art/show-0").param("actorId", "ana"))).get("result").asText())
                .as("the galleries' own art stays").isEqualTo("NOT_YOURS");
        assertThat(body(mvc.perform(delete("/api/v1/world/origin/art/" + id).param("actorId", "ana"))).get("result").asText())
                .isEqualTo("TAKEN_DOWN");
        assertThat(body(mvc.perform(delete("/api/v1/world/origin/art/" + id).param("actorId", "ana"))).get("result").asText())
                .isEqualTo("NO_SUCH_ART");
        mvc.perform(post("/api/v1/world/origin/art").contentType(MediaType.APPLICATION_JSON)
                .content("{\"x\":0,\"y\":1,\"z\":0,\"facing\":\"UP\",\"w\":1,\"h\":1,\"seed\":1}")).andExpect(status().isBadRequest());
    }

    @Test
    void artSurvivesARestartAndGoesWithItsWall() throws Exception {
        int n = wallOnOwnParcel("cy");
        ParcelBounds b = GalleryOps.parcelBounds(n);
        String id = hang("cy", b.minX() + 2, 1, b.minZ() + 2, "SOUTH", 2, 2, 5).get("art").get("id").asText();
        mvc = boot();
        assertThat(body(mvc.perform(get("/api/v1/world/origin/art"))).get("art").toString()).contains(id);
        assertThat(place("cy", b.minX() + 2, 1, b.minZ() + 2, "AIR")).isEqualTo("PLACED");
        assertThat(body(mvc.perform(get("/api/v1/world/origin/art"))).get("art").toString())
                .as("a frame whose wall is gone is not shown").doesNotContain(id);
        assertThat(place("cy", b.minX() + 2, 1, b.minZ() + 2, "BRICK_WHITE")).isEqualTo("PLACED");
        assertThat(body(mvc.perform(get("/api/v1/world/origin/art"))).get("art").toString()).contains(id);
    }
}
