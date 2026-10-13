// SPDX-License-Identifier: MIT
package com.daedalus.world.tactics;

import java.nio.charset.StandardCharsets;

/** Small portable checkpoint. Persistence owner supplies atomic storage; never modifies world-package bytes. */
public final class TacticalMemory {
    public static final int MAX_BYTES = 512;
    private TacticalMemory() { }

    public static byte[] encode(AdaptiveDirector.Memory memory) {
        String body = "DTM 1\n" + memory.faction() + " " + memory.session() + " " + memory.lastTick()
                + " " + memory.elevatedSamples() + " " + memory.casualtyPressure() + " " + memory.frameHash() + "\n";
        return (body + AdaptiveDirector.digest(body) + "\n").getBytes(StandardCharsets.US_ASCII);
    }

    public static AdaptiveDirector.Memory decode(byte[] bytes) {
        if (bytes == null || bytes.length > MAX_BYTES) throw new IllegalArgumentException("Checkpoint size");
        String text = new String(bytes, StandardCharsets.US_ASCII);
        String[] lines = text.split("\n", -1);
        if (lines.length != 4 || !lines[0].equals("DTM 1") || !lines[3].isEmpty()
                || !AdaptiveDirector.digest(lines[0] + "\n" + lines[1] + "\n").equals(lines[2])) {
            throw new IllegalArgumentException("Checkpoint version/integrity");
        }
        String[] v = lines[1].split(" ", -1);
        if (v.length != 6) throw new IllegalArgumentException("Checkpoint fields");
        return new AdaptiveDirector.Memory(v[0], v[1], Long.parseLong(v[2]), Integer.parseInt(v[3]),
                Integer.parseInt(v[4]), v[5]);
    }
}
