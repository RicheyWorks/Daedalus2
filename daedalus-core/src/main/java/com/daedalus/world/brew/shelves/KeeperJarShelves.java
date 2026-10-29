// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.shelves;

/** Keeper Oriel in the pantry. */
public final class KeeperJarShelves {
    public static final String GREETING = "The jars sit in the order %s, and jar k belongs in place k. "
            + "Swapping two jars at a time, what is the fewest swaps?";
    public static final String WRONG = "Not %d. Follow each ring of jars: it needs one swap fewer than its size.";
    public static final String SORTED = "Every jar is already home. No swaps needed.";
    public static final String THANKS = "Fewest swaps! The pantry is tidy again.";
    public static final String DONE = "Jar by jar, the shelf remembers its order.";

    private KeeperJarShelves() {
    }

    /** The line for this shelf. */
    public static String line(JarShelves r) {
        if (r.sorted()) {
            return SORTED;
        }
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.last() == JarShelves.Outcome.WRONG) {
            return String.format(WRONG, r.named());
        }
        return String.format(GREETING, r.order());
    }
}
