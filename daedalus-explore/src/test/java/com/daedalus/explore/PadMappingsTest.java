// SPDX-License-Identifier: MIT
package com.daedalus.explore;

import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class PadMappingsTest {
    @Test
    void databaseShipsWithEveryPlatform() {
        String db = PadMappings.load();
        assertTrue(PadMappings.count(db, "Windows") > 500, "Windows mappings");
        assertTrue(PadMappings.count(db, "Mac OS X") > 300, "Mac mappings");
        assertTrue(PadMappings.count(db, "Linux") > 300, "Linux mappings");
    }

    @Test
    void retroArcadeAndAtariPadsAreListed() {
        String db = PadMappings.load();
        for (String name : new String[] {"Mayflash N64 Adapter", "Sega Mega Drive Mini 6B Controller", "Atari VCS Classic Controller",
                "Astro City Mini", "NSO N64 Controller", "Razer Raiju", "GameSir", "8BitDo M30", "Qanba", "Raphnet Saturn"}) {
            assertTrue(db.contains(name), name);
        }
    }

    @Test
    void platformNameIsOneGlfwKnows() {
        String p = PadMappings.platform();
        assertTrue(p.equals("Windows") || p.equals("Mac OS X") || p.equals("Linux"));
    }
}
