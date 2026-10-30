// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.story;

/**
 * Keeper Oriel, who tends the Homestead Well and still remembers the ark choir. Her line depends on the chapter state
 * so a host can show it without any dialogue tree of its own. Lines are also listed in STORY.md.
 */
public final class KeeperLines {
    public static final String GREETING = "The arks sang these records into the seed vaults. The shattering scratched "
            + "every one. Bring me a record and brew what it can't sing.";
    public static final String PROGRESS = "The water at %s runs clear again. %d of %d records sing whole.";
    public static final String DRINK = "Three songs mended. Go and drink from a clean spring, then come tell me.";
    public static final String THANKS = "You hear that? The springs are humming the old tunes back. The arks would "
            + "be proud. Keep the choir: every record you mend wakes another spring.";
    public static final String ALL_CLEAN = "Every spring on the island runs clean. The choir is whole.";

    private KeeperLines() {
    }

    /** The line for this chapter state. */
    public static String line(SeedSongSpring s) {
        SeedSongSpring.Tally t = s.tally();
        if (t.restored() == 0) {
            return GREETING;
        }
        if (s.chain().nextCloudy() == null) {
            return ALL_CLEAN;
        }
        var step = s.quest().currentStep();
        if (step != null && step.type().equals("draw_clean")) {
            return DRINK;
        }
        String last = null;
        for (SpringChain.Spring sp : s.chain().springs()) {
            if (s.chain().clean(sp.id())) {
                last = sp.name();
            }
        }
        return String.format(PROGRESS, last, t.restored(), s.records().size());
    }

    /** What she hears on a scratched record: how many herbs play, how many notes the scratch ate, and whether it comes home. */
    public static String hint(ScratchedRecord r) {
        String home = r.comesHome() ? " It wants to come home: it ends on the note it began with."
                : " It does not come home; it ends somewhere new.";
        return String.format("This is %s. I hear %s, then the scratch eats %d note%s.%s", r.tune().seedSong(),
                String.join(", ", r.heard()), r.missing(), r.missing() == 1 ? "" : "s", home);
    }
}
