// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.plugin.MazePlugin;
import com.daedalus.plugin.PluginManifest;
import com.daedalus.plugin.runtime.PluginRegistry;
import com.daedalus.server.service.WorldService;
import com.daedalus.server.web.ApiExceptionHandler;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.nio.file.Path;

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
        mvc = MockMvcBuilders.standaloneSetup(new WorldController(worlds, new PluginRegistry()))
                .setControllerAdvice(new ApiExceptionHandler())
                .build();
    }

    @Test
    void inspectPlaceRemoveAndUnknownWorld() throws Exception {
        mvc.perform(get("/api/v1/world/world-zero"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id", equalTo("world-zero")))
                .andExpect(jsonPath("$.revision", equalTo(0)))
                .andExpect(jsonPath("$.chunkCount", equalTo(0)));

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
                        "npc.talk", "npc.hush")));

        mvc.perform(get("/api/v1/world/world-zero/observe")
                        .param("x", "1").param("y", "2").param("z", "3"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.blockType", equalTo("AIR")))
                .andExpect(jsonPath("$.doorState", equalTo("CLOSED")))
                .andExpect(jsonPath("$.revision", equalTo(0)));

        mvc.perform(get("/api/v1/world/world-zero/trace"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.steps.length()", equalTo(0)));

        mvc.perform(put("/api/v1/world/world-zero/block")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"x\":1,\"y\":2,\"z\":3,\"type\":\"STONE\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.previous", equalTo("AIR")))
                .andExpect(jsonPath("$.type", equalTo("STONE")))
                .andExpect(jsonPath("$.revision", equalTo(1)));

        mvc.perform(get("/api/v1/world/world-zero/block").param("x", "1").param("y", "2").param("z", "3"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.type", equalTo("STONE")))
                .andExpect(jsonPath("$.present", equalTo(true)));

        mvc.perform(get("/api/v1/world/world-zero/chunk").param("x", "0").param("y", "0").param("z", "0"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.present", equalTo(true)))
                .andExpect(jsonPath("$.occupied", equalTo(1)));

        mvc.perform(get("/api/v1/world/world-zero/chunk").param("x", "4").param("y", "0").param("z", "0"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.present", equalTo(false)))
                .andExpect(jsonPath("$.revision", nullValue()));

        mvc.perform(delete("/api/v1/world/world-zero/block")
                        .param("x", "1").param("y", "2").param("z", "3"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.previous", equalTo("STONE")))
                .andExpect(jsonPath("$.type", equalTo("AIR")));

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
                .andExpect(jsonPath("$.state", equalTo("CLOSED")));

        mvc.perform(post("/api/v1/world/world-zero/door/open"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("OPENED")))
                .andExpect(jsonPath("$.state", equalTo("OPEN")));

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
                .andExpect(jsonPath("$.steps[1].capability", equalTo("block.remove")))
                .andExpect(jsonPath("$.steps[2].capability", equalTo("door.open")))
                .andExpect(jsonPath("$.steps[3].capability", equalTo("door.open")));

        mvc.perform(get("/api/v1/world/world-zero/trap"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id", equalTo("trap-zero")))
                .andExpect(jsonPath("$.state", equalTo("DISARMED")));

        mvc.perform(post("/api/v1/world/world-zero/trap/arm"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("ARMED")))
                .andExpect(jsonPath("$.state", equalTo("ARMED")));

        mvc.perform(post("/api/v1/world/world-zero/trap/arm"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("ALREADY_ARMED")));

        mvc.perform(get("/api/v1/world/world-zero/portal"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id", equalTo("portal-zero")))
                .andExpect(jsonPath("$.state", equalTo("SEALED")));

        mvc.perform(post("/api/v1/world/world-zero/portal/open"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("OPENED")))
                .andExpect(jsonPath("$.state", equalTo("OPEN")));

        mvc.perform(post("/api/v1/world/world-zero/portal/open"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("ALREADY_OPEN")));

        mvc.perform(get("/api/v1/world/world-zero/npc"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id", equalTo("npc-zero")))
                .andExpect(jsonPath("$.state", equalTo("IDLE")));

        mvc.perform(post("/api/v1/world/world-zero/npc/talk"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("SPOKE")))
                .andExpect(jsonPath("$.state", equalTo("SPEAKING")));

        mvc.perform(post("/api/v1/world/world-zero/npc/talk"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result", equalTo("ALREADY_SPEAKING")));
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
        MockMvc extra = MockMvcBuilders.standaloneSetup(new WorldController(worlds, plugins))
                .setControllerAdvice(new ApiExceptionHandler())
                .build();
        extra.perform(get("/api/v1/world/world-zero/capabilities"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.capabilities", org.hamcrest.Matchers.hasItems(
                        "door.open", "trap.arm")));
    }
}
