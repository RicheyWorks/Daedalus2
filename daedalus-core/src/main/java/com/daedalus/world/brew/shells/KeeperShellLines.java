// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.shells;

/** Keeper Oriel by the inn fire. */
public final class KeeperShellLines {
    public static final String GREETING = "\"%s\" and \"%s\". Take shells off till they match, but don't reorder a "
            + "single one, and keep them as long as you can.";
    public static final String THREADING = "\"%s\" and \"%s\" so far.";
    public static final String READY = "They match. Hold them up together.";
    public static final String SHORT = "They match, but %d shells long where %d could be. Put some back.";
    public static final String THANKS = "Two strings, the same shells in the same order, and nothing wasted. Keep "
            + "them safe.";
    public static final String DONE = "Off to bed, both of you, shells and all.";

    private KeeperShellLines() {
    }

    /** The line for these strings. */
    public static String line(ShellStrings s) {
        if (s.quest().currentStep() == null) {
            return DONE;
        }
        String a = s.kept(ShellStrings.Side.LEFT);
        String b = s.kept(ShellStrings.Side.RIGHT);
        if (s.last() == ShellStrings.Outcome.SHORT) {
            return String.format(SHORT, a.length(), s.longest());
        }
        if (a.equals(s.left()) && b.equals(s.right())) {
            return String.format(GREETING, a, b);
        }
        return a.equals(b) ? READY : String.format(THREADING, a, b);
    }
}
