// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.hunt;

/**
 * Archivist Tamsin kept the ark's record ledger. She cannot walk the bridges any more, but she can still hear a
 * record hum through the stone. Her line comes from the hunt state; lines are also listed in STORY.md.
 */
public final class ArchivistLines {
    public static final String UNDERFOOT = "It's right here. The needle-hum is under your feet. Search.";
    public static final String ONE_BRIDGE = "One bridge away. Cross to %s.";
    public static final String WARMER = "Warmer. %d bridges off; start across to %s.";
    public static final String FAINT = "Faint, far out on the shelf: %d bridges. Head for %s and listen again.";
    public static final String EMPTY = "The crates are empty. Every record is home.";
    public static final String THANKS = "Three records home already. Take them to Keeper Oriel's bench and mend them. "
            + "I'll keep listening for the rest.";
    public static final String TIRED = "You're spent. Sleep, and the bridges will still be there tomorrow.";

    private ArchivistLines() {
    }

    /** The line for this hunt state. */
    public static String line(RecordHunt h) {
        RecordHunt.Hint hint = h.hint();
        if (hint == null) {
            return EMPTY;
        }
        if (h.stamina() == 0) {
            return TIRED;
        }
        return switch (hint.distance()) {
            case 0 -> UNDERFOOT;
            case 1 -> String.format(ONE_BRIDGE, FragmentMap.name(hint.toward()));
            case 2, 3 -> String.format(WARMER, hint.distance(), FragmentMap.name(hint.toward()));
            default -> String.format(FAINT, hint.distance(), FragmentMap.name(hint.toward()));
        };
    }
}
