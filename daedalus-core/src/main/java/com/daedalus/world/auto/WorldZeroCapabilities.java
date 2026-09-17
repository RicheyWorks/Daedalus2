// SPDX-License-Identifier: MIT

package com.daedalus.world.auto;

import java.util.List;

/**
 * Registers World Zero capabilities one by one. This is not
 * {@link WorldZeroDrive#DRIVEN} — the harness compares the two sets.
 */
public final class WorldZeroCapabilities {

    private WorldZeroCapabilities() {
    }

    public static CapabilityRegistry registry() {
        return registry(List.of());
    }

    /**
     * Same eight World Zero ids, plus extras a plugin advertised via
     * {@code MazePlugin.worldCapabilities()}. Extra ids stay UNACCOUNTED
     * until the drive script names them.
     */
    public static CapabilityRegistry registry(Iterable<String> extras) {
        CapabilityRegistry registry = new CapabilityRegistry();
        registry.register("world.inspect");
        registry.register("chunk.inspect");
        registry.register("block.inspect");
        registry.register("block.place");
        registry.register("block.remove");
        registry.register("door.inspect");
        registry.register("door.open");
        registry.register("door.close");
        if (extras != null) {
            for (String extra : extras) {
                registry.register(extra);
            }
        }
        return registry;
    }
}
