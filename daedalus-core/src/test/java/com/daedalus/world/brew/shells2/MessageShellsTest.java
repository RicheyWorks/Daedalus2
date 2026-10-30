// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.shells2;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.shells2.MessageShells.Outcome;
import java.util.Arrays;
import org.junit.jupiter.api.Test;

class MessageShellsTest {
    /** Brute force: pass the shell, noting when each islander first held it, until someone holds it twice. */
    static int[] brute(MessageShells m) {
        int[] first = new int[m.islanders()];
        Arrays.fill(first, -1);
        int at = 0;
        int step = 0;
        while (first[at] < 0) {
            first[at] = step++;
            at = m.next(at);
        }
        return new int[] {first[at], step - first[at]};
    }

    /** 0 to 1 to 2 to 3 to 4, then back to 2: 2 passes in, a loop of 3 among 5 islanders. */
    static MessageShells island() {
        return new MessageShells(1, 2, 3, 4, 2);
    }

    @Test
    void seededIslandIsDeterministic() {
        MessageShells a = MessageShells.seeded(8);
        MessageShells b = MessageShells.seeded(8);
        assertEquals(a.islanders(), b.islanders());
        assertEquals(a.loop(), b.loop());
        assertThrows(IllegalArgumentException.class, () -> new MessageShells(1));
        assertEquals(1, new MessageShells(0).loop(), "one islander keeps the shell");
    }

    @Test
    void tailAndLoopMatchBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            MessageShells m = MessageShells.seeded(seed);
            int[] b = brute(m);
            assertEquals(b[0], m.tail(), "Floyd tail == simulation, seed " + seed);
            assertEquals(b[1], m.loop(), "Floyd loop == simulation, seed " + seed);
        }
    }

    @Test
    void loopIsNotEveryone() {
        MessageShells m = island();
        assertEquals(2, m.tail());
        assertEquals(3, m.loop(), "3 in the loop, not all 5 islanders");
    }

    @Test
    void wrongReadingEarnsNoCredit() {
        MessageShells m = island();
        m.pass("p");
        assertEquals(Outcome.WRONG, m.read("r1", 0, 5));
        assertEquals(String.format(KeeperShellLines.WRONG, 0, 5), m.talk("t1"));
        assertEquals("read", m.quest().currentStep().type(), "no credit for a wrong reading");
    }

    @Test
    void guards() {
        MessageShells m = island();
        assertEquals(Outcome.IGNORED, m.read("", 2, 3));
        assertEquals(Outcome.WRONG, m.read("e1", 2, 4), "half right is still wrong");
        assertEquals(Outcome.DUPLICATE, m.read("e1", 2, 3));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        MessageShells m = island();
        assertEquals(String.format(KeeperShellLines.GREETING, 5), m.talk("t0"));
        m.pass("p0");
        assertEquals(Outcome.WRONG, m.read("r1", 0, 5));
        assertEquals(Outcome.RIGHT, m.read("r2", 2, 3));
        assertEquals(KeeperShellLines.THANKS, m.talk("t2"));
        assertNull(m.quest().currentStep());
        assertEquals(KeeperShellLines.DONE, m.talk("t3"));
    }
}
