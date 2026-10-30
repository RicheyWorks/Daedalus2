// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.plugin.events.WorldBlockEvent;
import com.daedalus.plugin.runtime.PluginRegistry;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.server.service.WorldService;
import com.daedalus.server.web.ApiExceptionHandler;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.island.IslandOps;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.nio.file.Path;
import java.security.Principal;
import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Island ownership (ADR-026): claim, build rights, builders, abandon, and the rule that a signed-in
 * caller is who they are — a body {@code actorId} cannot speak for someone else.
 */
class IslandClaimControllerTest {

    private static final String W = "/api/v1/world/world-zero";

    @TempDir
    Path tmp;

    private final ObjectMapper json = new ObjectMapper();
    private final List<WorldBlockEvent> events = new ArrayList<>();
    private Path file;
    private MockMvc mvc;
    private BlockCoordinate isle0;
    private BlockCoordinate isle1;

    @BeforeEach
    void setUp() throws Exception {
        file = tmp.resolve("world-zero.daew");
        mvc = boot();
        for (long seed : new long[] {11, 42}) {
            mvc.perform(post(W + "/islands").contentType(MediaType.APPLICATION_JSON).content("{\"seed\":" + seed + "}"))
                    .andExpect(status().isOk());
        }
        // A cube of open sky over each island's centre, inside its claim box.
        isle0 = new BlockCoordinate(IslandOps.slot(0).x(), IslandOps.slot(0).y() + 30, IslandOps.slot(0).z());
        isle1 = new BlockCoordinate(IslandOps.slot(1).x(), IslandOps.slot(1).y() + 30, IslandOps.slot(1).z());
    }

    private MockMvc boot() {
        WorldService w = new WorldService(file, event -> {
            if (event instanceof WorldBlockEvent b) {
                events.add(b);
            }
        });
        return MockMvcBuilders.standaloneSetup(new WorldController(w, new PluginRegistry(),
                        new MazeGenerationService(new GeneratorRegistry(List.of(new RecursiveBacktrackerGenerator())),
                                event -> { }, new SimpleMeterRegistry())))
                .setControllerAdvice(new ApiExceptionHandler())
                .build();
    }

    private JsonNode body(ResultActions r) throws Exception {
        return json.readTree(r.andExpect(status().isOk()).andReturn().getResponse().getContentAsString());
    }

    private static MockHttpServletRequestBuilder as(MockHttpServletRequestBuilder b, String user) {
        Principal p = () -> user;
        return user == null ? b : b.principal(p);
    }

    private JsonNode claim(String verb, int slot, String actorId, String user, String extra) throws Exception {
        String content = "{" + (actorId == null ? "" : "\"actorId\":\"" + actorId + "\"")
                + (extra == null ? "" : (actorId == null ? "" : ",") + extra) + "}";
        return body(mvc.perform(as(post(W + "/islands/" + slot + "/" + verb), user)
                .contentType(MediaType.APPLICATION_JSON).content(content)));
    }

    private String place(BlockCoordinate at, String actorId, String user) throws Exception {
        String content = "{\"x\":" + at.x() + ",\"y\":" + at.y() + ",\"z\":" + at.z() + ",\"type\":\"CRYSTAL\""
                + (actorId == null ? "" : ",\"actorId\":\"" + actorId + "\"") + "}";
        return body(mvc.perform(as(put(W + "/block"), user).contentType(MediaType.APPLICATION_JSON).content(content)))
                .get("result").asText();
    }

    private String remove(BlockCoordinate at, String actorId, String user) throws Exception {
        var req = delete(W + "/block").param("x", "" + at.x()).param("y", "" + at.y()).param("z", "" + at.z());
        if (actorId != null) {
            req = req.param("actorId", actorId);
        }
        return body(mvc.perform(as(req, user))).get("result").asText();
    }

    private JsonNode isle(int slot) throws Exception {
        return body(mvc.perform(get(W + "/islands"))).get("islands").get(slot);
    }

    @Test
    void anOpenIslandIsEveryonesAndAClaimMakesItTheOwners() throws Exception {
        assertThat(isle(0).get("owner").asText()).isEmpty();
        assertThat(place(isle0, "bob", null)).isEqualTo("PLACED");
        assertThat(remove(isle0, "bob", null)).isEqualTo("REMOVED");

        events.clear();
        JsonNode c = claim("claim", 0, "alice", null, null);
        assertThat(c.get("result").asText()).isEqualTo("CLAIMED");
        assertThat(c.get("owner").asText()).isEqualTo("alice");
        assertThat(events).anyMatch(e -> "CLAIM".equals(e.type()));
        assertThat(isle(0).get("owner").asText()).isEqualTo("alice");

        assertThat(place(isle0, "bob", null)).isEqualTo("DENIED");
        assertThat(place(isle0, null, null)).as("an anonymous write is the system, not the owner").isEqualTo("DENIED");
        assertThat(place(isle0, "alice", null)).isEqualTo("PLACED");
        assertThat(remove(isle0, "bob", null)).isEqualTo("DENIED");
        assertThat(place(isle1, "bob", null)).as("the next island is still open").isEqualTo("PLACED");

        JsonNode again = claim("claim", 0, "bob", null, null);
        assertThat(again.get("result").asText()).isEqualTo("ALREADY_CLAIMED");
        assertThat(again.get("owner").asText()).isEqualTo("alice");
    }

    @Test
    void theOwnerNamesBuildersAndOnlyTheOwnerCan() throws Exception {
        claim("claim", 0, "alice", null, null);
        assertThat(claim("builders", 0, "bob", null, "\"builder\":\"bob\"").get("result").asText()).isEqualTo("NOT_OWNER");
        JsonNode g = claim("builders", 0, "alice", null, "\"builder\":\"bob\",\"allow\":true");
        assertThat(g.get("result").asText()).isEqualTo("GRANTED");
        assertThat(g.get("builders").get(0).asText()).isEqualTo("bob");
        assertThat(isle(0).get("builders").get(0).asText()).isEqualTo("bob");
        assertThat(place(isle0, "bob", null)).isEqualTo("PLACED");
        assertThat(place(isle0, "carol", null)).isEqualTo("DENIED");
        assertThat(claim("builders", 0, "alice", null, "\"builder\":\"bob\",\"allow\":false").get("result").asText())
                .isEqualTo("REVOKED");
        assertThat(remove(isle0, "bob", null)).isEqualTo("DENIED");
        assertThat(claim("builders", 0, "alice", null, "\"builder\":\"alice\"").get("result").asText()).isEqualTo("BAD_BUILDER");
        assertThat(claim("builders", 1, "alice", null, "\"builder\":\"bob\"").get("result").asText()).isEqualTo("NOT_CLAIMED");
    }

    @Test
    void aSignedInCallerIsWhoTheyAreWhateverTheBodySays() throws Exception {
        assertThat(claim("claim", 0, "mallory", "alice", null).get("owner").asText()).isEqualTo("alice");
        assertThat(place(isle0, "alice", "bob")).as("bob signed in, claiming to be alice").isEqualTo("DENIED");
        assertThat(remove(isle0, "alice", "bob")).isEqualTo("DENIED");
        assertThat(place(isle0, "bob", "alice")).isEqualTo("PLACED");
        assertThat(claim("abandon", 0, "alice", "bob", null).get("result").asText()).isEqualTo("NOT_OWNER");
        assertThat(claim("builders", 0, "alice", "bob", "\"builder\":\"bob\"").get("result").asText()).isEqualTo("NOT_OWNER");
    }

    @Test
    void abandoningOpensTheIslandAndItsBuildersGoWithTheClaim() throws Exception {
        claim("claim", 0, "alice", null, null);
        claim("builders", 0, "alice", null, "\"builder\":\"bob\"");
        assertThat(claim("abandon", 0, "bob", null, null).get("result").asText()).isEqualTo("NOT_OWNER");
        JsonNode a = claim("abandon", 0, "alice", null, null);
        assertThat(a.get("result").asText()).isEqualTo("ABANDONED");
        assertThat(a.get("owner").asText()).isEmpty();
        assertThat(place(isle0, "carol", null)).isEqualTo("PLACED");
        assertThat(claim("abandon", 0, "alice", null, null).get("result").asText()).isEqualTo("NOT_CLAIMED");
        claim("claim", 0, "carol", null, null);
        assertThat(isle(0).get("builders")).as("bob's grant left with alice's claim").isEmpty();
    }

    @Test
    void theGenericParcelRoutesCannotReachAClaimedIsland() throws Exception {
        claim("claim", 0, "alice", null, null);
        claim("builders", 0, "alice", null, "\"builder\":\"bob\"");
        String at = "\"x\":" + isle0.x() + ",\"y\":" + isle0.y() + ",\"z\":" + isle0.z();
        for (String verb : new String[] {"grant", "deny", "revoke", "forgive"}) {
            String who = "deny".equals(verb) ? "alice" : "revoke".equals(verb) ? "bob" : "mallory";
            JsonNode r = body(mvc.perform(post(W + "/parcels/" + verb).contentType(MediaType.APPLICATION_JSON)
                    .content("{" + at + ",\"actorId\":\"" + who + "\"}")));
            assertThat(r.get("result").asText()).as(verb).isEqualTo("NO_PARCEL");
        }
        assertThat(place(isle0, "mallory", null)).isEqualTo("DENIED");
        assertThat(place(isle0, "alice", null)).as("the owner was not denied").isEqualTo("PLACED");
        assertThat(place(isle0, "bob", null)).as("the builder was not revoked").isEqualTo("PLACED");
    }

    @Test
    void claimsAreValidatedAndSurviveARestart() throws Exception {
        for (String bad : new String[] {"system", "a b", "   "}) {
            assertThat(claim("claim", 0, bad, null, null).get("result").asText()).as(bad).isEqualTo("BAD_OWNER");
        }
        assertThat(claim("claim", 0, null, null, null).get("result").asText()).isEqualTo("BAD_OWNER");
        assertThat(claim("claim", 9, "alice", null, null).get("result").asText()).isEqualTo("NO_SUCH_ISLAND");
        claim("claim", 1, "alice", null, null);
        claim("builders", 1, "alice", null, "\"builder\":\"bob\"");

        mvc = boot();
        assertThat(isle(1).get("owner").asText()).isEqualTo("alice");
        assertThat(isle(1).get("builders").get(0).asText()).isEqualTo("bob");
        assertThat(place(isle1, "carol", null)).isEqualTo("DENIED");
        assertThat(place(isle1, "bob", null)).isEqualTo("PLACED");
        mvc.perform(post("/api/v1/world/nope/islands/0/claim").contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isNotFound());
    }
}
