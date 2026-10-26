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
import com.daedalus.world.district.DistrictOps;
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

import java.nio.file.Path;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * A Parcels world over HTTP (ADR-033): it is born with its district; plots are claimed through the same
 * routes as islands; only an owner (or their builders) changes a plot, below the height limit, and
 * nobody builds on streets or the plaza; the helicopter flies from the pad to a sky gate and home;
 * everything holds across a restart.
 */
class ParcelsWorldTest {

    @TempDir
    Path tmp;

    private final ObjectMapper json = new ObjectMapper();
    private final long[] clock = {7_000_000L};
    private WorldHub hub;
    private MockMvc mvc;

    @BeforeEach
    void setUp() throws Exception {
        mvc = boot();
        JsonNode made = body(mvc.perform(post("/api/v1/worlds").contentType(MediaType.APPLICATION_JSON)
                .content("{\"id\":\"plaza-town\",\"style\":\"PARCELS\",\"seed\":5,\"title\":\"Plaza Town\"}")));
        assertThat(made.get("result").asText()).isEqualTo("CREATED");
        hub.get("plaza-town").useClock(() -> clock[0]); // mounted after boot: give it the test's clock too
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
        return body(mvc.perform(get("/api/v1/world/plaza-town/block").param("x", "" + x).param("y", "" + y)
                .param("z", "" + z))).get("type").asText();
    }

    private String place(String who, int x, int y, int z, String type) throws Exception {
        return body(mvc.perform(put("/api/v1/world/plaza-town/block").contentType(MediaType.APPLICATION_JSON)
                .content("{\"x\":" + x + ",\"y\":" + y + ",\"z\":" + z + ",\"type\":\"" + type + "\",\"actorId\":\"" + who + "\"}")))
                .get("result").asText();
    }

    private String claim(String verb, int n, String who) throws Exception {
        return body(mvc.perform(post("/api/v1/world/plaza-town/islands/" + n + "/" + verb)
                .contentType(MediaType.APPLICATION_JSON).content("{\"actorId\":\"" + who + "\"}"))).get("result").asText();
    }

    private JsonNode fly(String dest) throws Exception {
        return body(mvc.perform(post("/api/v1/world/plaza-town/arks/" + WorldService.HELICOPTER + "/voyage")
                .contentType(MediaType.APPLICATION_JSON).content(dest)));
    }

    @Test
    void aParcelsWorldIsBornWithItsDistrictAndListsSixtyPlots() throws Exception {
        BlockCoordinate pad = DistrictOps.padBerth();
        assertThat(type(pad.x() - 5, 0, pad.z() - 5)).isEqualTo("HELIPAD");
        assertThat(type(DistrictOps.MIN_X + 1, 0, -60)).isEqualTo("ROAD");
        assertThat(type(DistrictOps.MIN_X, -2, -60)).isEqualTo("STONE");

        JsonNode plots = body(mvc.perform(get("/api/v1/world/plaza-town/plots")));
        assertThat(plots.get("plots")).hasSize(60);
        assertThat(plots.get("height").asInt()).isEqualTo(DistrictOps.HEIGHT);
        assertThat(plots.get("padX").asInt()).isEqualTo(pad.x());
        JsonNode p0 = plots.get("plots").get(0);
        assertThat(p0.get("n").asInt()).isZero();
        assertThat(p0.get("maxX").asInt() - p0.get("minX").asInt()).isEqualTo(15);
        assertThat(p0.get("owner").asText()).isEmpty();
        assertThat(p0.get("show").asText()).isIn("LAWN", "GROVE", "PAVILION", "TOWER", "SCULPTURE", "POND");

        assertThat(body(mvc.perform(get("/api/v1/world/plaza-town/islands"))).get("islands")).isEmpty();
        assertThat(body(mvc.perform(post("/api/v1/world/plaza-town/islands").contentType(MediaType.APPLICATION_JSON)
                .content("{\"seed\":3}"))).get("result").asText()).isEqualTo("WRONG_STYLE");
        mvc.perform(get("/api/v1/world/world-zero/plots")).andExpect(status().isNotFound());
        JsonNode gates = body(mvc.perform(get("/api/v1/world/plaza-town/gates")));
        assertThat(gates.get("mount").asText()).isEqualTo("HELICOPTER");
        assertThat(gates.get("mountReady").asBoolean()).isTrue();
    }

    @Test
    void onlyAPlotsOwnerBuildsThereAndNobodyBuildsOnTheStreets() throws Exception {
        ParcelBounds b = DistrictOps.plotBounds(0);
        int x = b.minX() + 2;
        int z = b.minZ() + 2;
        assertThat(place("ana", x, 1, z, "WOOD")).as("unclaimed plot").isEqualTo("DENIED");
        assertThat(place("ana", DistrictOps.MIN_X + 1, 1, -60, "WOOD")).as("street").isEqualTo("DENIED");
        BlockCoordinate pad = DistrictOps.padBerth();
        assertThat(place("ana", pad.x(), pad.y(), pad.z(), "WOOD")).as("plaza").isEqualTo("DENIED");

        assertThat(claim("claim", 0, "ana")).isEqualTo("CLAIMED");
        assertThat(claim("claim", 0, "bo")).isEqualTo("ALREADY_CLAIMED");
        assertThat(claim("claim", 27, "bo")).as("the plaza is nobody's").isEqualTo("NO_SUCH_PLOT");
        assertThat(claim("claim", 64, "bo")).isEqualTo("NO_SUCH_PLOT");

        assertThat(place("ana", x, 1, z, "WOOD")).isEqualTo("PLACED");
        assertThat(type(x, 1, z)).isEqualTo("WOOD");
        assertThat(place("bo", x, 2, z, "WOOD")).isEqualTo("DENIED");
        assertThat(place("ana", x, DistrictOps.HEIGHT, z, "GLASS")).as("at the limit").isEqualTo("PLACED");
        assertThat(place("ana", x, DistrictOps.HEIGHT + 1, z, "GLASS")).as("above the limit").isEqualTo("DENIED");
        assertThat(place("ana", b.maxX() + 1, 1, z, "WOOD")).as("the street beside it").isEqualTo("DENIED");

        assertThat(body(mvc.perform(post("/api/v1/world/plaza-town/islands/0/builders").contentType(MediaType.APPLICATION_JSON)
                .content("{\"actorId\":\"ana\",\"builder\":\"bo\",\"allow\":true}"))).get("result").asText()).isEqualTo("GRANTED");
        assertThat(place("bo", x, 2, z, "WOOD")).isEqualTo("PLACED");
        JsonNode p0 = body(mvc.perform(get("/api/v1/world/plaza-town/plots"))).get("plots").get(0);
        assertThat(p0.get("owner").asText()).isEqualTo("ana");
        assertThat(p0.get("builders").get(0).asText()).isEqualTo("bo");

        assertThat(claim("abandon", 0, "bo")).isEqualTo("NOT_OWNER");
        assertThat(claim("abandon", 0, "ana")).isEqualTo("ABANDONED");
        assertThat(place("ana", x, 3, z, "WOOD")).as("given back: nobody builds").isEqualTo("DENIED");
        assertThat(type(x, 1, z)).as("the cubes stay").isEqualTo("WOOD");
    }

    @Test
    void theHelicopterFliesFromThePadToAGateAndHome() throws Exception {
        JsonNode arks = body(mvc.perform(get("/api/v1/world/plaza-town/arks"))).get("arks");
        assertThat(arks).hasSize(1);
        JsonNode heli = arks.get(0);
        assertThat(heli.get("id").asText()).isEqualTo("heli-0");
        assertThat(heli.get("name").asText()).isEqualTo("Helicopter");
        assertThat(heli.get("slot").asInt()).isEqualTo(DistrictOps.PAD_SLOT);
        assertThat(heli.get("x").asInt()).isEqualTo(DistrictOps.padBerth().x());
        assertThat(heli.get("hold")).isEmpty();

        assertThat(fly("{\"toGate\":0}").get("result").asText()).as("no gate yet").isEqualTo("NO_SUCH_ISLAND");
        assertThat(body(mvc.perform(post("/api/v1/world/plaza-town/gates").contentType(MediaType.APPLICATION_JSON)
                .content("{\"toWorld\":\"world-zero\"}"))).get("result").asText()).isEqualTo("OPENED");
        JsonNode up = fly("{\"toGate\":0}");
        assertThat(up.get("result").asText()).isEqualTo("SAILING");
        assertThat(up.get("ark").get("toSlot").asInt()).isEqualTo(GateOps.slotOfGate(0));
        assertThat(up.get("ark").get("z").asInt()).isEqualTo(GateOps.berth(0).z());

        clock[0] = up.get("ark").get("arriveAt").asLong();
        assertThat(body(mvc.perform(get("/api/v1/world/plaza-town/arks"))).get("arks").get(0).get("slot").asInt())
                .isEqualTo(GateOps.slotOfGate(0));
        JsonNode home = fly("{\"toHome\":true}");
        assertThat(home.get("result").asText()).isEqualTo("SAILING");
        assertThat(home.get("ark").get("toSlot").asInt()).isEqualTo(DistrictOps.PAD_SLOT);
        clock[0] = home.get("ark").get("arriveAt").asLong();
        assertThat(fly("{\"toHome\":true}").get("result").asText()).isEqualTo("ALREADY_THERE");

        mvc.perform(post("/api/v1/world/plaza-town/arks/heli-0/voyage").contentType(MediaType.APPLICATION_JSON)
                .content("{\"toHome\":true,\"toGate\":0}")).andExpect(status().isBadRequest());
        // world-zero has no helicopter; its arks still go home too.
        mvc.perform(post("/api/v1/world/world-zero/arks/heli-0/voyage").contentType(MediaType.APPLICATION_JSON)
                .content("{\"toHome\":true}")).andExpect(status().isNotFound());
    }

    @Test
    void theDistrictsRulesAndClaimsSurviveARestart() throws Exception {
        assertThat(claim("claim", 9, "ana")).isEqualTo("CLAIMED");
        ParcelBounds b = DistrictOps.plotBounds(9);
        assertThat(place("ana", b.minX(), 1, b.minZ(), "CRYSTAL")).isEqualTo("PLACED");
        mvc = boot();
        assertThat(type(b.minX(), 1, b.minZ())).isEqualTo("CRYSTAL");
        assertThat(place("bo", b.minX(), 2, b.minZ(), "WOOD")).isEqualTo("DENIED");
        assertThat(place("ana", DistrictOps.MIN_X + 1, 1, -60, "WOOD")).as("streets stay closed").isEqualTo("DENIED");
        assertThat(place("ana", b.minX(), 2, b.minZ(), "WOOD")).isEqualTo("PLACED");
        assertThat(body(mvc.perform(get("/api/v1/world/plaza-town/arks"))).get("arks").get(0).get("id").asText())
                .isEqualTo("heli-0");
    }
}
