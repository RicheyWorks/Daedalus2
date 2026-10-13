package com.daedalus.server.controller;

import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

class RealmShardDirectoryControllerTest {
    @Test void routesSeparateDistrictsAndRealms() throws Exception {
        var controller=new RealmShardDirectoryController(
                "world-zero,0,49,https://realm-a.example/;world-zero,50,99,https://realm-b.example;labyrinth,0,99,https://lab.example",7);
        var mvc=MockMvcBuilders.standaloneSetup(controller).build();
        mvc.perform(get("/api/v1/realms/world-zero/districts/49/route"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.serverUrl").value("https://realm-a.example"))
                .andExpect(jsonPath("$.directoryRevision").value(7));
        assertEquals("https://realm-b.example",controller.route("world-zero",50).serverUrl());
        assertEquals("https://lab.example",controller.route("labyrinth",50).serverUrl());
        mvc.perform(get("/api/v1/realms/missing/districts/0/route")).andExpect(status().isNotFound());
        mvc.perform(get("/api/v1/realms/world-zero/districts/100/route")).andExpect(status().isBadRequest());
        mvc.perform(get("/api/v1/realms/world-zero/districts/-1/route")).andExpect(status().isBadRequest());
    }
    @Test void rejectsAmbiguousOrUnsafeConfiguration() {
        for(String value:new String[]{"","world-zero,0,100,https://a.example","world-zero,9,8,https://a.example",
                "World,0,1,https://a.example","world-zero,0,1,http://a.example","world-zero,0,1,https://user@a.example",
                "world-zero,0,1,https://a.example/path","world-zero,0,1,https://a.example?key=secret",
                "world-zero,0,1,https://a.example;world-zero,1,2,https://b.example"})
            assertThrows(IllegalArgumentException.class,()->new RealmShardDirectoryController(value,1),value);
        assertThrows(IllegalArgumentException.class,()->new RealmShardDirectoryController("x,0,99,https://a.example",0));
    }
}
