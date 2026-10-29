// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.shells2;

/** Keeper Oriel with the message shell. */
public final class KeeperShellLines {
    public static final String GREETING = "%d islanders, and each always passes the message shell to the same "
            + "neighbour. Start it with yourself: how many passes before it starts going round in a loop, and how "
            + "long is the loop?";
    public static final String WRONG = "%d passes in and a loop of %d? Watch the shell again.";
    public static final String THANKS = "Right. Now we know who will never hear the message.";
    public static final String DONE = "The shell is still going round.";

    private KeeperShellLines() {
    }

    /** The line for this island. */
    public static String line(MessageShells m) {
        if (m.quest().currentStep() == null) {
            return DONE;
        }
        if (m.last() == MessageShells.Outcome.WRONG) {
            return String.format(WRONG, m.namedTail(), m.namedLoop());
        }
        return String.format(GREETING, m.islanders());
    }
}
