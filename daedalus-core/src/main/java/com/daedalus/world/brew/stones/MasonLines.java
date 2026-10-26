// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.stones;

/**
 * Mason Hale cut the ark's keel blocks before the fall; now she cuts choir stones. Her line follows the chapter
 * state so a host can show it without a dialogue tree. Lines are also listed in STORY.md.
 */
public final class MasonLines {
    public static final String GREETING = "Feel that? The shelf shakes every night, and the ropes can't take it "
            + "forever. Bring me a song you've mended and a blank stone, and I'll make it hum.";
    public static final String ONE_STONE = "One stone humming. One more and the ropes near it might just hold.";
    public static final String CUT_OFF = "Last night's shake cut off %d fragment%s. Re-string the snapped ropes, and "
            + "put a stone where the shaking keeps winning.";
    public static final String HOLDING = "The ropes held %d night%s. Keep the stones singing.";
    public static final String THANKS = "Three nights and not one fragment lost. The stones remember what the arks "
            + "sang. Take this chisel; it's yours now.";

    private MasonLines() {
    }

    /** The line for this chapter state. */
    public static String line(ChoirStones c) {
        if (c.stones().isEmpty()) {
            return GREETING;
        }
        ChoirStones.Night n = c.lastNight();
        if (n != null && !n.held()) {
            int k = n.cutOff().size();
            return String.format(CUT_OFF, k, k == 1 ? "" : "s");
        }
        if (n == null) {
            return c.stones().size() == 1 ? ONE_STONE : String.format(HOLDING, 0, "s");
        }
        int h = c.heldNights();
        return String.format(HOLDING, h, h == 1 ? "" : "s");
    }
}
