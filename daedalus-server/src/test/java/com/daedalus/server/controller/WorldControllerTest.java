// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.plugin.MazePlugin;
import com.daedalus.plugin.PluginManifest;
import com.daedalus.plugin.runtime.PluginRegistry;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.server.service.WorldService;
import com.daedalus.server.web.ApiExceptionHandler;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.nio.file.Path;
import java.util.List;
import java.util.UUID;

import static org.hamcrest.Matchers.equalTo;
import static org.hamcrest.Matchers.nullValue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class WorldControllerTest {

    @TempDir
    Path tmp;

    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        WorldService worlds = new WorldService(tmp.resolve("world-zero.daew"));
        mvc = MockMvcBuilders.standaloneSetup(new WorldController(worlds, new PluginRegistry(), mazes()))
                .setControllerAdvice(new ApiExceptionHandler())
                .build();
    }

    private static MazeGenerationService mazes() {
        return new MazeGenerationService(
                new GeneratorRegistry(List.of(new RecursiveBacktrackerGenerator())),
                event -> { }, new SimpleMeterRegistry());
    }

    @Test
    void inspectPlaceRemoveAndUnknownWorld() throws Exception {
        mvc.perform(get("/api/v1/world/world-zero"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id", equalTo("world-zero")))
                .andExpect(jsonPath("$.revision", equalTo(0)))
                .andExpect(jsonPath("$.chunkCount", equalTo(0)))
                .andExpect(jsonPath("$.plots", equalTo(0)))
                .andExpect(jsonPath("$.street", equalTo("")))
                .andExpect(jsonPath("$.lot", equalTo("")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("")))
                .andExpect(jsonPath("$.place", equalTo("")))
                .andExpect(jsonPath("$.occupants", equalTo("door · trap · portal · npc")))
                .andExpect(jsonPath("$.stands",
                        equalTo("door 0,1,0 · trap 1,1,0 · portal 2,1,0 · npc 3,1,0")))
                .andExpect(jsonPath("$.acl", equalTo("")))
                .andExpect(jsonPath("$.drive", equalTo("")))
                .andExpect(jsonPath("$.driveActor", equalTo("")))
                .andExpect(jsonPath("$.driveAt", equalTo("")));

        mvc.perform(get("/api/v1/world/world-zero/parcels"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.worldId", equalTo("world-zero")))
                .andExpect(jsonPath("$.parcels.length()", equalTo(0)));

        mvc.perform(get("/api/v1/world/world-zero/capabilities"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.worldId", equalTo("world-zero")))
                .andExpect(jsonPath("$.capabilities", org.hamcrest.Matchers.hasItems(
                        "world.inspect", "block.place", "door.open", "door.close",
                        "trap.arm", "trap.disarm", "portal.open", "portal.seal",
                        "npc.talk", "npc.hush", "parcel.lease", "parcel.release",
                        "parcel.grant",
                        "parcel.deny", "parcel.revoke", "parcel.forgive", "stamp.apply")));

        mvc.perform(get("/api/v1/world/world-zero/observe")
                        .param("x", "1").param("y", "2").param("z", "3"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.blockType", equalTo("AIR")))
                .andExpect(jsonPath("$.doorState", equalTo("CLOSED")))
                .andExpect(jsonPath("$.place", equalTo("")))
                .andExpect(jsonPath("$.lot", equalTo("")))
                .andExpect(jsonPath("$.occupant", equalTo("")))
                .andExpect(jsonPath("$.acl", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.drive", equalTo("")))
                .andExpect(jsonPath("$.driveActor", equalTo("")))
                .andExpect(jsonPath("$.driveAt", equalTo("")))
                .andExpect(jsonPath("$.revision", equalTo(0)));

        mvc.perform(get("/api/v1/world/world-zero/observe")
                        .param("x", "0").param("y", "1").param("z", "0"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.occupant", equalTo("door")));

        mvc.perform(get("/api/v1/world/world-zero/trace"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.steps.length()", equalTo(0)));

        mvc.perform(put("/api/v1/world/world-zero/block")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"x\":1,\"y\":2,\"z\":3,\"type\":\"STONE\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.previous", equalTo("AIR")))
                .andExpect(jsonPath("$.type", equalTo("STONE")))
                .andExpect(jsonPath("$.result", equalTo("PLACED")))
                .andExpect(jsonPath("$.revision", equalTo(1)));

        mvc.perform(get("/api/v1/world/world-zero/block").param("x", "1").param("y", "2").param("z", "3"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.type", equalTo("STONE")))
                .andExpect(jsonPath("$.present", equalTo(true)))
                .andExpect(jsonPath("$.place", equalTo("")))
                .andExpect(jsonPath("$.lot", equalTo("")))
                .andExpect(jsonPath("$.acl", equalTo("")))
                .andExpect(jsonPath("$.drive", equalTo("block.place AIR")))
                .andExpect(jsonPath("$.driveActor", equalTo("system")))
                .andExpect(jsonPath("$.driveAt", equalTo("1,2,3")));

        mvc.perform(get("/api/v1/world/world-zero/block").param("x", "0").param("y", "0").param("z", "0"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.drive", equalTo("")))
                .andExpect(jsonPath("$.driveActor", equalTo("")))
                .andExpect(jsonPath("$.driveAt", equalTo("")));

        mvc.perform(get("/api/v1/world/world-zero/chunk").param("x", "0").param("y", "0").param("z", "0"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.present", equalTo(true)))
                .andExpect(jsonPath("$.occupied", equalTo(1)))
                .andExpect(jsonPath("$.street", equalTo("")))
                .andExpect(jsonPath("$.lot", equalTo("")))
                .andExpect(jsonPath("$.plots", equalTo(0)))
                .andExpect(jsonPath("$.occupants", equalTo("door · trap · portal · npc")))
                .andExpect(jsonPath("$.stands",
                        equalTo("door 0,1,0 · trap 1,1,0 · portal 2,1,0 · npc 3,1,0")))
                .andExpect(jsonPath("$.drive", equalTo("block.place AIR")))
                .andExpect(jsonPath("$.driveActor", equalTo("system")))
                .andExpect(jsonPath("$.driveAt", equalTo("1,2,3")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("")))
                .andExpect(jsonPath("$.acl", equalTo("")));

        mvc.perform(get("/api/v1/world/world-zero/chunk").param("x", "4").param("y", "0").param("z", "0"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.present", equalTo(false)))
                .andExpect(jsonPath("$.revision", nullValue()))
                .andExpect(jsonPath("$.street", equalTo("")))
                .andExpect(jsonPath("$.occupants", equalTo("")))
                .andExpect(jsonPath("$.stands", equalTo("")))
                .andExpect(jsonPath("$.drive", equalTo("")))
                .andExpect(jsonPath("$.driveActor", equalTo("")))
                .andExpect(jsonPath("$.driveAt", equalTo("")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("")))
                .andExpect(jsonPath("$.acl", equalTo("")));

        mvc.perform(delete("/api/v1/world/world-zero/block")
                        .param("x", "1").param("y", "2").param("z", "3"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.previous", equalTo("STONE")))
                .andExpect(jsonPath("$.type", equalTo("AIR")))
                .andExpect(jsonPath("$.result", equalTo("REMOVED")));

        mvc.perform(get("/api/v1/world/other"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.kind", equalTo("world")));

        mvc.perform(put("/api/v1/world/world-zero/block")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"x\":0,\"y\":0,\"z\":0,\"type\":\"obsidian\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detail").value(org.hamcrest.Matchers.containsString("Unknown block type")));

        mvc.perform(get("/api/v1/world/world-zero/door"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id", equalTo("door-zero")))
                .andExpect(jsonPath("$.state", equalTo("CLOSED")))
                .andExpect(jsonPath("$.place", equalTo("")))
                .andExpect(jsonPath("$.lot", equalTo("")))
                .andExpect(jsonPath("$.box", equalTo("")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("")))
                .andExpect(jsonPath("$.acl", equalTo("")))
                .andExpect(jsonPath("$.drive", equalTo("")))
                .andExpect(jsonPath("$.driveActor", equalTo("")))
                .andExpect(jsonPath("$.driveAt", equalTo("")));

        mvc.perform(post("/api/v1/world/world-zero/door/open"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("OPENED")))
                .andExpect(jsonPath("$.state", equalTo("OPEN")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("")))
                .andExpect(jsonPath("$.place", equalTo("")))
                .andExpect(jsonPath("$.lot", equalTo("")))
                .andExpect(jsonPath("$.box", equalTo("")));

        mvc.perform(post("/api/v1/world/world-zero/door/open"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("ALREADY_OPEN")));

        mvc.perform(get("/api/v1/world/world-zero/observe")
                        .param("x", "1").param("y", "2").param("z", "3"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.blockType", equalTo("AIR")))
                .andExpect(jsonPath("$.doorState", equalTo("OPEN")));

        mvc.perform(get("/api/v1/world/world-zero/trace"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.steps.length()", equalTo(4)))
                .andExpect(jsonPath("$.steps[0].capability", equalTo("block.place")))
                .andExpect(jsonPath("$.steps[0].actor", equalTo("system")))
                .andExpect(jsonPath("$.steps[0].at", equalTo("1,2,3")))
                .andExpect(jsonPath("$.steps[1].capability", equalTo("block.remove")))
                .andExpect(jsonPath("$.steps[2].capability", equalTo("door.open")))
                .andExpect(jsonPath("$.steps[3].capability", equalTo("door.open")))
                .andExpect(jsonPath("$.steps[3].actor", equalTo("system")));

        mvc.perform(get("/api/v1/world/world-zero/trap"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id", equalTo("trap-zero")))
                .andExpect(jsonPath("$.state", equalTo("DISARMED")))
                .andExpect(jsonPath("$.box", equalTo("")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("")))
                .andExpect(jsonPath("$.acl", equalTo("")))
                .andExpect(jsonPath("$.drive", equalTo("")))
                .andExpect(jsonPath("$.driveActor", equalTo("")))
                .andExpect(jsonPath("$.driveAt", equalTo("")));

        mvc.perform(post("/api/v1/world/world-zero/trap/arm"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("ARMED")))
                .andExpect(jsonPath("$.state", equalTo("ARMED")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("")))
                .andExpect(jsonPath("$.place", equalTo("")))
                .andExpect(jsonPath("$.lot", equalTo("")))
                .andExpect(jsonPath("$.box", equalTo("")));

        mvc.perform(post("/api/v1/world/world-zero/trap/arm"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("ALREADY_ARMED")));

        mvc.perform(get("/api/v1/world/world-zero/portal"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id", equalTo("portal-zero")))
                .andExpect(jsonPath("$.state", equalTo("SEALED")))
                .andExpect(jsonPath("$.box", equalTo("")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("")))
                .andExpect(jsonPath("$.acl", equalTo("")))
                .andExpect(jsonPath("$.drive", equalTo("")))
                .andExpect(jsonPath("$.driveActor", equalTo("")))
                .andExpect(jsonPath("$.driveAt", equalTo("")));

        mvc.perform(post("/api/v1/world/world-zero/portal/open"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("OPENED")))
                .andExpect(jsonPath("$.state", equalTo("OPEN")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("")))
                .andExpect(jsonPath("$.place", equalTo("")))
                .andExpect(jsonPath("$.lot", equalTo("")));

        mvc.perform(post("/api/v1/world/world-zero/portal/open"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("ALREADY_OPEN")));

        mvc.perform(get("/api/v1/world/world-zero/npc"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id", equalTo("npc-zero")))
                .andExpect(jsonPath("$.state", equalTo("IDLE")))
                .andExpect(jsonPath("$.box", equalTo("")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("")))
                .andExpect(jsonPath("$.acl", equalTo("")))
                .andExpect(jsonPath("$.drive", equalTo("")))
                .andExpect(jsonPath("$.driveActor", equalTo("")))
                .andExpect(jsonPath("$.driveAt", equalTo("")));

        mvc.perform(post("/api/v1/world/world-zero/npc/talk"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("SPOKE")))
                .andExpect(jsonPath("$.state", equalTo("SPEAKING")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("")))
                .andExpect(jsonPath("$.place", equalTo("")))
                .andExpect(jsonPath("$.lot", equalTo("")));

        mvc.perform(post("/api/v1/world/world-zero/npc/talk"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("ALREADY_SPEAKING")));

        mvc.perform(post("/api/v1/world/world-zero/parcels/lease"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("NO_PARCEL")))
                .andExpect(jsonPath("$.leaseId", equalTo("")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.place", equalTo("")))
                .andExpect(jsonPath("$.lot", equalTo("")))
                .andExpect(jsonPath("$.box", equalTo("")));

        mvc.perform(post("/api/v1/world/world-zero/parcels/release"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("NO_PARCEL")))
                .andExpect(jsonPath("$.leaseId", equalTo("")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.place", equalTo("")))
                .andExpect(jsonPath("$.lot", equalTo("")))
                .andExpect(jsonPath("$.box", equalTo("")));

        mvc.perform(post("/api/v1/world/world-zero/stamp")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"x\":0,\"y\":0,\"z\":0}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.ok", equalTo(true)))
                .andExpect(jsonPath("$.result", equalTo("APPLIED")))
                .andExpect(jsonPath("$.parcelId", equalTo("parcel-1")))
                .andExpect(jsonPath("$.maxX", equalTo(2)))
                .andExpect(jsonPath("$.maxZ", equalTo(2)))
                .andExpect(jsonPath("$.box", equalTo("0,0,0-2,1,2")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("0,0")));

        mvc.perform(get("/api/v1/world/world-zero/door"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.box", equalTo("0,0,0-2,1,2")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("")));

        mvc.perform(get("/api/v1/world/world-zero/trap"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.box", equalTo("0,0,0-2,1,2")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("")));

        mvc.perform(get("/api/v1/world/world-zero/portal"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.box", equalTo("0,0,0-2,1,2")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("")));

        mvc.perform(get("/api/v1/world/world-zero/npc"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.box", equalTo("")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("")));

        mvc.perform(get("/api/v1/world/world-zero"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.drive", equalTo("stamp.apply APPLIED")))
                .andExpect(jsonPath("$.driveActor", equalTo("system")))
                .andExpect(jsonPath("$.driveAt", equalTo("0,0,0")));

        mvc.perform(post("/api/v1/world/world-zero/stamp")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"x\":0,\"y\":0,\"z\":0,\"actorId\":\"carol\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.ok", equalTo(false)))
                .andExpect(jsonPath("$.result", equalTo("DENIED")))
                .andExpect(jsonPath("$.box", equalTo("")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.place", equalTo("")))
                .andExpect(jsonPath("$.lot", equalTo("")));

        mvc.perform(get("/api/v1/world/world-zero"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.drive", equalTo("stamp.apply DENIED")))
                .andExpect(jsonPath("$.driveActor", equalTo("carol")))
                .andExpect(jsonPath("$.driveAt", equalTo("0,0,0")));

        mvc.perform(get("/api/v1/world/world-zero/trace"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.steps[-1].capability", equalTo("stamp.apply")))
                .andExpect(jsonPath("$.steps[-1].result", equalTo("DENIED")))
                .andExpect(jsonPath("$.steps[-1].actor", equalTo("carol")))
                .andExpect(jsonPath("$.steps[-1].at", equalTo("0,0,0")));

        mvc.perform(get("/api/v1/world/world-zero/block").param("x", "0").param("y", "0").param("z", "0"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.drive", equalTo("stamp.apply DENIED")))
                .andExpect(jsonPath("$.driveActor", equalTo("carol")))
                .andExpect(jsonPath("$.driveAt", equalTo("0,0,0")));

        mvc.perform(get("/api/v1/world/world-zero/observe")
                        .param("x", "0").param("y", "0").param("z", "0"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.drive", equalTo("stamp.apply DENIED")))
                .andExpect(jsonPath("$.driveActor", equalTo("carol")))
                .andExpect(jsonPath("$.driveAt", equalTo("0,0,0")))
                .andExpect(jsonPath("$.lease", equalTo("")))
                .andExpect(jsonPath("$.maze", equalTo("")));

        mvc.perform(post("/api/v1/world/world-zero/stamp")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"x\":0,\"y\":0,\"z\":0}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.ok", equalTo(false)))
                .andExpect(jsonPath("$.result", equalTo("PARCEL_OVERLAP")));

        mvc.perform(post("/api/v1/world/world-zero/parcels/lease"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("LEASED")))
                .andExpect(jsonPath("$.leaseId", equalTo("tenant-zero")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("0,0")))
                .andExpect(jsonPath("$.box", equalTo("0,0,0-2,1,2")));

        mvc.perform(get("/api/v1/world/world-zero/observe")
                        .param("x", "0").param("y", "0").param("z", "0"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.lease", equalTo("tenant-zero")))
                .andExpect(jsonPath("$.maze", equalTo("")));

        mvc.perform(post("/api/v1/world/world-zero/door/close"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("CLOSED")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("tenant-zero")))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("0,0")))
                .andExpect(jsonPath("$.box", equalTo("0,0,0-2,1,2")));

        mvc.perform(post("/api/v1/world/world-zero/door/open").param("actorId", "carol"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("DENIED")))
                .andExpect(jsonPath("$.state", equalTo("CLOSED")));

        mvc.perform(get("/api/v1/world/world-zero/door"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.drive", equalTo("door.open DENIED")))
                .andExpect(jsonPath("$.driveActor", equalTo("carol")))
                .andExpect(jsonPath("$.driveAt", equalTo("0,1,0")))
                .andExpect(jsonPath("$.lease", equalTo("tenant-zero")));

        mvc.perform(get("/api/v1/world/world-zero/trap"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.lease", equalTo("tenant-zero")));

        mvc.perform(get("/api/v1/world/world-zero/portal"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.lease", equalTo("tenant-zero")));

        mvc.perform(get("/api/v1/world/world-zero/npc"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.lease", equalTo("")));

        mvc.perform(post("/api/v1/world/world-zero/door/open"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("OPENED")))
                .andExpect(jsonPath("$.state", equalTo("OPEN")));

        mvc.perform(post("/api/v1/world/world-zero/door/close").param("actorId", "carol"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("DENIED")))
                .andExpect(jsonPath("$.state", equalTo("OPEN")));

        mvc.perform(post("/api/v1/world/world-zero/parcels/grant")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"actorId\":\"bob\",\"x\":0,\"y\":0,\"z\":0}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("GRANTED")))
                .andExpect(jsonPath("$.acl", equalTo("bob block.place")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("tenant-zero")))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("0,0")))
                .andExpect(jsonPath("$.box", equalTo("0,0,0-2,1,2")));

        mvc.perform(get("/api/v1/world/world-zero/chunk").param("x", "0").param("y", "0").param("z", "0"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.acl", equalTo("bob block.place")));
        mvc.perform(get("/api/v1/world/world-zero/chunk").param("x", "4").param("y", "0").param("z", "0"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.acl", equalTo("")));
        mvc.perform(get("/api/v1/world/world-zero/parcels"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.parcels[0].acl", equalTo("bob block.place")));

        mvc.perform(post("/api/v1/world/world-zero/parcels/grant")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"actorId\":\"bob\",\"x\":0,\"y\":0,\"z\":0}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("ALREADY_GRANTED")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("tenant-zero")))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("0,0")))
                .andExpect(jsonPath("$.box", equalTo("0,0,0-2,1,2")));

        mvc.perform(post("/api/v1/world/world-zero/parcels/grant")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"actorId\":\"bob\",\"x\":0,\"y\":0,\"z\":0,\"verb\":\"door.open\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("GRANTED")))
                .andExpect(jsonPath("$.acl", equalTo("bob block.place · bob door.open")));

        mvc.perform(post("/api/v1/world/world-zero/parcels/grant")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"actorId\":\"bob\",\"x\":0,\"y\":0,\"z\":0,\"verb\":\"shop.open\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("UNKNOWN_VERB")));

        mvc.perform(post("/api/v1/world/world-zero/door/close"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("CLOSED")));

        mvc.perform(post("/api/v1/world/world-zero/door/open").param("actorId", "bob"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("OPENED")))
                .andExpect(jsonPath("$.state", equalTo("OPEN")));

        mvc.perform(put("/api/v1/world/world-zero/block")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"x\":0,\"y\":0,\"z\":0,\"type\":\"STONE\",\"actorId\":\"carol\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("DENIED")));

        mvc.perform(put("/api/v1/world/world-zero/block")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"x\":0,\"y\":0,\"z\":0,\"type\":\"STONE\",\"actorId\":\"bob\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("PLACED")))
                .andExpect(jsonPath("$.type", equalTo("STONE")));

        mvc.perform(delete("/api/v1/world/world-zero/block")
                        .param("x", "0").param("y", "0").param("z", "0")
                        .param("actorId", "carol"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("DENIED")))
                .andExpect(jsonPath("$.type", equalTo("STONE")));

        mvc.perform(post("/api/v1/world/world-zero/parcels/deny")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"actorId\":\"bob\",\"x\":0,\"y\":0,\"z\":0}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("DENIED")))
                .andExpect(jsonPath("$.acl",
                        equalTo("bob block.place · bob door.open · !bob block.place")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("tenant-zero")))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("0,0")))
                .andExpect(jsonPath("$.box", equalTo("0,0,0-2,1,2")));

        mvc.perform(post("/api/v1/world/world-zero/parcels/deny")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"actorId\":\"bob\",\"x\":0,\"y\":0,\"z\":0}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("ALREADY_DENIED")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("tenant-zero")))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("0,0")))
                .andExpect(jsonPath("$.box", equalTo("0,0,0-2,1,2")));

        mvc.perform(post("/api/v1/world/world-zero/trap/arm").param("actorId", "carol"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("DENIED")))
                .andExpect(jsonPath("$.state", equalTo("ARMED")))
                .andExpect(jsonPath("$.lease", equalTo("tenant-zero")))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("0,0")))
                .andExpect(jsonPath("$.box", equalTo("0,0,0-2,1,2")));

        mvc.perform(get("/api/v1/world/world-zero/trap"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.drive", equalTo("trap.arm DENIED")))
                .andExpect(jsonPath("$.driveActor", equalTo("carol")))
                .andExpect(jsonPath("$.driveAt", equalTo("1,1,0")));

        mvc.perform(post("/api/v1/world/world-zero/trap/disarm").param("actorId", "carol"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("DENIED")))
                .andExpect(jsonPath("$.state", equalTo("ARMED")));

        mvc.perform(post("/api/v1/world/world-zero/parcels/grant")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"actorId\":\"bob\",\"x\":0,\"y\":0,\"z\":0,\"verb\":\"trap.arm\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("GRANTED")));

        mvc.perform(post("/api/v1/world/world-zero/trap/disarm").param("actorId", "bob"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("DISARMED")))
                .andExpect(jsonPath("$.state", equalTo("DISARMED")));

        mvc.perform(post("/api/v1/world/world-zero/portal/open").param("actorId", "carol"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("DENIED")))
                .andExpect(jsonPath("$.state", equalTo("OPEN")))
                .andExpect(jsonPath("$.lease", equalTo("tenant-zero")))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("0,0")));

        mvc.perform(get("/api/v1/world/world-zero/portal"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.drive", equalTo("portal.open DENIED")))
                .andExpect(jsonPath("$.driveActor", equalTo("carol")))
                .andExpect(jsonPath("$.driveAt", equalTo("2,1,0")));

        mvc.perform(get("/api/v1/world/world-zero/chunk").param("x", "0").param("y", "0").param("z", "0"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.drive", equalTo("portal.open DENIED")))
                .andExpect(jsonPath("$.driveActor", equalTo("carol")))
                .andExpect(jsonPath("$.driveAt", equalTo("2,1,0")));

        mvc.perform(get("/api/v1/world/world-zero/chunk").param("x", "4").param("y", "0").param("z", "0"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.drive", equalTo("")))
                .andExpect(jsonPath("$.driveActor", equalTo("")))
                .andExpect(jsonPath("$.driveAt", equalTo("")));

        mvc.perform(post("/api/v1/world/world-zero/portal/seal").param("actorId", "carol"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("DENIED")))
                .andExpect(jsonPath("$.state", equalTo("OPEN")));

        mvc.perform(post("/api/v1/world/world-zero/parcels/grant")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"actorId\":\"bob\",\"x\":0,\"y\":0,\"z\":0,\"verb\":\"portal.open\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("GRANTED")));

        mvc.perform(post("/api/v1/world/world-zero/portal/seal").param("actorId", "bob"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("SEALED")))
                .andExpect(jsonPath("$.state", equalTo("SEALED")));

        mvc.perform(post("/api/v1/world/world-zero/stamp")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"x\":3,\"y\":0,\"z\":0}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.ok", equalTo(true)));

        mvc.perform(post("/api/v1/world/world-zero/npc/talk").param("actorId", "carol"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("DENIED")))
                .andExpect(jsonPath("$.state", equalTo("SPEAKING")));

        mvc.perform(get("/api/v1/world/world-zero/npc"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.drive", equalTo("npc.talk DENIED")))
                .andExpect(jsonPath("$.driveActor", equalTo("carol")))
                .andExpect(jsonPath("$.driveAt", equalTo("3,1,0")));

        mvc.perform(post("/api/v1/world/world-zero/npc/hush").param("actorId", "carol"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("DENIED")))
                .andExpect(jsonPath("$.state", equalTo("SPEAKING")));

        mvc.perform(post("/api/v1/world/world-zero/parcels/grant")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"actorId\":\"bob\",\"x\":3,\"y\":1,\"z\":0,\"verb\":\"npc.talk\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("GRANTED")));

        mvc.perform(post("/api/v1/world/world-zero/npc/hush").param("actorId", "bob"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("HUSHED")))
                .andExpect(jsonPath("$.state", equalTo("IDLE")));

        mvc.perform(post("/api/v1/world/world-zero/parcels/revoke")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"actorId\":\"bob\",\"x\":0,\"y\":0,\"z\":0}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("REVOKED")))
                .andExpect(jsonPath("$.acl", equalTo(
                        "bob door.open · bob trap.arm · bob portal.open · !bob block.place"
                                + " · bob npc.talk")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("tenant-zero")))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("0,0")))
                .andExpect(jsonPath("$.box", equalTo("0,0,0-2,1,2")));

        mvc.perform(post("/api/v1/world/world-zero/parcels/revoke")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"actorId\":\"bob\",\"x\":0,\"y\":0,\"z\":0}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("NOT_GRANTED")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("tenant-zero")))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("0,0")))
                .andExpect(jsonPath("$.box", equalTo("0,0,0-2,1,2")));

        mvc.perform(post("/api/v1/world/world-zero/parcels/revoke")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"actorId\":\"bob\",\"x\":0,\"y\":0,\"z\":0,\"verb\":\"shop.open\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("UNKNOWN_VERB")));

        mvc.perform(post("/api/v1/world/world-zero/parcels/forgive")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"actorId\":\"bob\",\"x\":0,\"y\":0,\"z\":0}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("FORGIVEN")))
                .andExpect(jsonPath("$.acl", equalTo(
                        "bob door.open · bob trap.arm · bob portal.open · bob npc.talk")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("tenant-zero")))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("0,0")))
                .andExpect(jsonPath("$.box", equalTo("0,0,0-2,1,2")));

        mvc.perform(post("/api/v1/world/world-zero/parcels/forgive")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"actorId\":\"bob\",\"x\":0,\"y\":0,\"z\":0}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("NOT_DENIED")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("tenant-zero")))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("0,0")))
                .andExpect(jsonPath("$.box", equalTo("0,0,0-2,1,2")));

        mvc.perform(post("/api/v1/world/world-zero/parcels/forgive")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"actorId\":\"bob\",\"x\":0,\"y\":0,\"z\":0,\"verb\":\"shop.open\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("UNKNOWN_VERB")));

        mvc.perform(post("/api/v1/world/world-zero/parcels/release"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("RELEASED")))
                .andExpect(jsonPath("$.leaseId", equalTo("")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.place", equalTo("")))
                .andExpect(jsonPath("$.lot", equalTo("")))
                .andExpect(jsonPath("$.box", equalTo("")));

        mvc.perform(post("/api/v1/world/world-zero/parcels/release"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("NOT_LEASED")))
                .andExpect(jsonPath("$.leaseId", equalTo("")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.place", equalTo("")))
                .andExpect(jsonPath("$.lot", equalTo("")))
                .andExpect(jsonPath("$.box", equalTo("")));
    }

    @Test
    void pluginAdvertisedCapabilitiesAppearOnDiscover() throws Exception {
        WorldService worlds = new WorldService(tmp.resolve("world-zero.daew"));
        PluginRegistry plugins = new PluginRegistry();
        plugins.put(new MazePlugin() {
            @Override
            public PluginManifest manifest() {
                return new PluginManifest("trap", "Trap", "1.0", null, null);
            }

            @Override
            public java.util.List<String> worldCapabilities() {
                return java.util.List.of("trap.arm");
            }
        });
        MockMvc extra = MockMvcBuilders.standaloneSetup(new WorldController(worlds, plugins, mazes()))
                .setControllerAdvice(new ApiExceptionHandler())
                .build();
        extra.perform(get("/api/v1/world/world-zero/capabilities"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.capabilities", org.hamcrest.Matchers.hasItems(
                        "door.open", "trap.arm")));
    }

    @Test
    void aGeneratedMazeStampsALargerSlabThanTheOneByOneDefault() throws Exception {
        MazeGenerationService gen = mazes();
        MazeGenerationService.Cached cached = gen.generate("recursive-backtracker", 3, 3, 7L);
        WorldService worlds = new WorldService(tmp.resolve("lab-stamp.daew"));
        MockMvc extra = MockMvcBuilders.standaloneSetup(
                        new WorldController(worlds, new PluginRegistry(), gen))
                .setControllerAdvice(new ApiExceptionHandler())
                .build();
        extra.perform(post("/api/v1/world/world-zero/stamp")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"x\":0,\"y\":0,\"z\":0,\"mazeId\":\""
                                + UUID.randomUUID() + "\"}"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.kind", equalTo("maze")));
        extra.perform(post("/api/v1/world/world-zero/stamp")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"x\":0,\"y\":0,\"z\":0,\"mazeId\":\""
                                + cached.metadata().id() + "\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.ok", equalTo(true)))
                .andExpect(jsonPath("$.result", equalTo("APPLIED")))
                .andExpect(jsonPath("$.maxX", equalTo(6)))
                .andExpect(jsonPath("$.maxZ", equalTo(6)))
                .andExpect(jsonPath("$.box", equalTo("0,0,0-6,1,6")))
                .andExpect(jsonPath("$.maze", equalTo(cached.metadata().id().toString())))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("0,0")));
        extra.perform(get("/api/v1/world/world-zero/parcels"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.parcels[0].mazeRef", equalTo(cached.metadata().id().toString())))
                .andExpect(jsonPath("$.parcels[0].box", equalTo("0,0,0-6,1,6")))
                .andExpect(jsonPath("$.parcels[0].acl", equalTo("")));
        extra.perform(post("/api/v1/world/world-zero/parcels/grant")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"actorId\":\"bob\",\"x\":0,\"y\":0,\"z\":0}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("GRANTED")))
                .andExpect(jsonPath("$.maze", equalTo(cached.metadata().id().toString())))
                .andExpect(jsonPath("$.lease", equalTo("")))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("0,0")))
                .andExpect(jsonPath("$.box", equalTo("0,0,0-6,1,6")));
        extra.perform(get("/api/v1/world/world-zero/observe")
                        .param("x", "0").param("y", "0").param("z", "0"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.maze", equalTo(cached.metadata().id().toString())));
        extra.perform(get("/api/v1/world/world-zero/chunk")
                        .param("x", "0").param("y", "0").param("z", "0"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.maze", equalTo(cached.metadata().id().toString())))
                .andExpect(jsonPath("$.lease", equalTo("")))
                .andExpect(jsonPath("$.acl", equalTo("bob block.place")));
        extra.perform(get("/api/v1/world/world-zero/npc"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.box", equalTo("0,0,0-6,1,6")))
                .andExpect(jsonPath("$.maze", equalTo(cached.metadata().id().toString())))
                .andExpect(jsonPath("$.lease", equalTo("")));
        extra.perform(post("/api/v1/world/world-zero/npc/talk"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("SPOKE")))
                .andExpect(jsonPath("$.maze", equalTo(cached.metadata().id().toString())))
                .andExpect(jsonPath("$.lease", equalTo("")))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("0,0")));
        extra.perform(post("/api/v1/world/world-zero/parcels/lease"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("LEASED")))
                .andExpect(jsonPath("$.leaseId", equalTo("tenant-zero")))
                .andExpect(jsonPath("$.maze", equalTo(cached.metadata().id().toString())))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("0,0")))
                .andExpect(jsonPath("$.box", equalTo("0,0,0-6,1,6")));
        extra.perform(post("/api/v1/world/world-zero/parcels/grant")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"actorId\":\"bob\",\"x\":0,\"y\":0,\"z\":0}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("ALREADY_GRANTED")))
                .andExpect(jsonPath("$.maze", equalTo(cached.metadata().id().toString())))
                .andExpect(jsonPath("$.lease", equalTo("tenant-zero")))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("0,0")))
                .andExpect(jsonPath("$.box", equalTo("0,0,0-6,1,6")));
        extra.perform(get("/api/v1/world/world-zero/npc"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.lease", equalTo("tenant-zero")));
        extra.perform(post("/api/v1/world/world-zero/npc/hush"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("HUSHED")))
                .andExpect(jsonPath("$.maze", equalTo(cached.metadata().id().toString())))
                .andExpect(jsonPath("$.lease", equalTo("tenant-zero")))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("0,0")));
        extra.perform(get("/api/v1/world/world-zero/chunk")
                        .param("x", "0").param("y", "0").param("z", "0"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.lease", equalTo("tenant-zero")));
        extra.perform(get("/api/v1/world/world-zero/door"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.maze", equalTo(cached.metadata().id().toString())));
        extra.perform(post("/api/v1/world/world-zero/door/open"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("OPENED")))
                .andExpect(jsonPath("$.maze", equalTo(cached.metadata().id().toString())))
                .andExpect(jsonPath("$.lease", equalTo("tenant-zero")))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("0,0")))
                .andExpect(jsonPath("$.box", equalTo("0,0,0-6,1,6")));
        extra.perform(get("/api/v1/world/world-zero/trap"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.maze", equalTo(cached.metadata().id().toString())));
        extra.perform(post("/api/v1/world/world-zero/trap/arm"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("ARMED")))
                .andExpect(jsonPath("$.maze", equalTo(cached.metadata().id().toString())))
                .andExpect(jsonPath("$.lease", equalTo("tenant-zero")))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("0,0")))
                .andExpect(jsonPath("$.box", equalTo("0,0,0-6,1,6")));
        extra.perform(get("/api/v1/world/world-zero/portal"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.maze", equalTo(cached.metadata().id().toString())));
        extra.perform(post("/api/v1/world/world-zero/portal/open"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("OPENED")))
                .andExpect(jsonPath("$.maze", equalTo(cached.metadata().id().toString())))
                .andExpect(jsonPath("$.lease", equalTo("tenant-zero")))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("0,0")));
        MazeGenerationService.Cached again = gen.generate("recursive-backtracker", 3, 3, 8L);
        extra.perform(post("/api/v1/world/world-zero/stamp")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"x\":0,\"y\":0,\"z\":0,\"mazeId\":\""
                                + again.metadata().id() + "\",\"next\":true}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.ok", equalTo(true)))
                .andExpect(jsonPath("$.result", equalTo("APPLIED")))
                .andExpect(jsonPath("$.minX", equalTo(8)))
                .andExpect(jsonPath("$.maze", equalTo(again.metadata().id().toString())))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("8,0")));
        extra.perform(get("/api/v1/world/world-zero/parcels"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.parcels.length()", equalTo(2)))
                .andExpect(jsonPath("$.parcels[1].mazeRef", equalTo(again.metadata().id().toString())))
                .andExpect(jsonPath("$.parcels[1].minX", equalTo(8)))
                .andExpect(jsonPath("$.parcels[1].minZ", equalTo(0)))
                .andExpect(jsonPath("$.parcels[0].acl", equalTo("bob block.place")))
                .andExpect(jsonPath("$.parcels[1].acl", equalTo("")));
        extra.perform(get("/api/v1/world/world-zero"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.plots", equalTo(2)))
                .andExpect(jsonPath("$.lot", equalTo("0,0 · 8,0")))
                .andExpect(jsonPath("$.maze", equalTo(
                        cached.metadata().id() + " · " + again.metadata().id())));
        extra.perform(get("/api/v1/world/world-zero/block")
                        .param("x", "0").param("y", "0").param("z", "0"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.lot", equalTo("0,0")))
                .andExpect(jsonPath("$.box", equalTo("0,0,0-6,1,6")))
                .andExpect(jsonPath("$.maze", equalTo(cached.metadata().id().toString())))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))));
        extra.perform(get("/api/v1/world/world-zero/observe")
                        .param("x", "8").param("y", "0").param("z", "0"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.lot", equalTo("8,0")))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lease", equalTo("")))
                .andExpect(jsonPath("$.maze", equalTo(again.metadata().id().toString())));
        extra.perform(get("/api/v1/world/world-zero/chunk")
                        .param("x", "0").param("y", "0").param("z", "0"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.maze", equalTo(
                        cached.metadata().id() + " · " + again.metadata().id())))
                .andExpect(jsonPath("$.lease", equalTo("tenant-zero")));
        extra.perform(get("/api/v1/world/world-zero/chunk")
                        .param("x", "4").param("y", "0").param("z", "0"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.lease", equalTo("")));
        extra.perform(post("/api/v1/world/world-zero/parcels/lease"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("LEASED")))
                .andExpect(jsonPath("$.maze", equalTo(again.metadata().id().toString())))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("8,0")))
                .andExpect(jsonPath("$.box", equalTo("8,0,0-14,1,6")));
        extra.perform(post("/api/v1/world/world-zero/parcels/release"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("RELEASED")))
                .andExpect(jsonPath("$.maze", equalTo(again.metadata().id().toString())))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("8,0")))
                .andExpect(jsonPath("$.box", equalTo("8,0,0-14,1,6")));
        extra.perform(post("/api/v1/world/world-zero/parcels/release"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("RELEASED")))
                .andExpect(jsonPath("$.maze", equalTo("")))
                .andExpect(jsonPath("$.place", equalTo("")))
                .andExpect(jsonPath("$.lot", equalTo("")))
                .andExpect(jsonPath("$.box", equalTo("")));
        extra.perform(post("/api/v1/world/world-zero/parcels/deny")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"actorId\":\"carol\",\"x\":0,\"y\":0,\"z\":0}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("DENIED")))
                .andExpect(jsonPath("$.maze", equalTo(cached.metadata().id().toString())))
                .andExpect(jsonPath("$.lease", equalTo("")))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("0,0")))
                .andExpect(jsonPath("$.box", equalTo("0,0,0-6,1,6")));
        extra.perform(post("/api/v1/world/world-zero/parcels/revoke")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"actorId\":\"bob\",\"x\":0,\"y\":0,\"z\":0}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("REVOKED")))
                .andExpect(jsonPath("$.maze", equalTo(cached.metadata().id().toString())))
                .andExpect(jsonPath("$.lease", equalTo("")))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("0,0")))
                .andExpect(jsonPath("$.box", equalTo("0,0,0-6,1,6")));
        extra.perform(post("/api/v1/world/world-zero/parcels/forgive")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"actorId\":\"carol\",\"x\":0,\"y\":0,\"z\":0}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("FORGIVEN")))
                .andExpect(jsonPath("$.maze", equalTo(cached.metadata().id().toString())))
                .andExpect(jsonPath("$.lease", equalTo("")))
                .andExpect(jsonPath("$.place", org.hamcrest.Matchers.not(equalTo(""))))
                .andExpect(jsonPath("$.lot", equalTo("0,0")))
                .andExpect(jsonPath("$.box", equalTo("0,0,0-6,1,6")));
    }
}
