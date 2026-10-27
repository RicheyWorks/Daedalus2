// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.circle;

/** Keeper Oriel by the fire. */
public final class KeeperCircleLines {
    public static final String GREETING = "%d children round the fire, counting from child 0. Every %d%s count steps "
            + "out, and the count goes on. Who is left last to light the lantern?";
    public static final String OUT = "Child %d steps out. Child %d is left last.";
    public static final String THANKS = "Child %d it is. Light the lantern!";
    public static final String DONE = "The lantern is lit. Off to bed.";

    private KeeperCircleLines() {
    }

    static String nth(int k) {
        return k == 1 ? "st" : k == 2 ? "nd" : k == 3 ? "rd" : "th";
    }

    /** The line for this circle. */
    public static String line(CountingCircle c) {
        if (c.quest().currentStep() == null) {
            return DONE;
        }
        if (c.last() == CountingCircle.Outcome.OUT) {
            return String.format(OUT, c.named(), c.survivor());
        }
        return String.format(GREETING, c.children(), c.step(), nth(c.step()));
    }
}
