// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.week;

/**
 * Old Wick ran the ark ferry between fragments and has survived more first weeks than anyone. His line follows the
 * week's state; lines are also listed in STORY.md.
 */
public final class WickLines {
    public static final String GREETING = "First week's the hard one. Drink clean when you can, cook what the plot "
            + "gives you, and never drink the sea, whatever it looks like.";
    public static final String THIRSTY = "Your lips are cracking. Get to a clean spring before the sun goes down.";
    public static final String HUNGRY = "You're running on nothing. Cook something, even porridge.";
    public static final String SICK = "That cloudy water got you. Boil it, filter it, or brew a cadence over it next "
            + "time.";
    public static final String STEADY = "Day %d. You're holding up.";
    public static final String LOST = "Lie still. Someone will carry you home. The shelf will wait for you.";
    public static final String THANKS = "Seven days. You're not a survivor any more, you're a neighbour. The ferry's "
            + "yours when you want it.";
    public static final int LOW = 25;

    private WickLines() {
    }

    /** The line for this week state. */
    public static String line(FirstWeek w) {
        if (w.lost()) {
            return LOST;
        }
        if (w.lastDay() == null && w.thirst() == FirstWeek.START && w.hunger() == FirstWeek.START) {
            return GREETING;
        }
        if (w.sick()) {
            return SICK;
        }
        if (w.thirst() < LOW) {
            return THIRSTY;
        }
        if (w.hunger() < LOW) {
            return HUNGRY;
        }
        return String.format(STEADY, Math.min(w.day(), FirstWeek.DAYS));
    }
}
