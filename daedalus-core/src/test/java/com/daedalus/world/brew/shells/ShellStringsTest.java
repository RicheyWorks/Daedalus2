// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.shells;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.shells.ShellStrings.Outcome;
import com.daedalus.world.brew.shells.ShellStrings.Side;
import org.junit.jupiter.api.Test;

class ShellStringsTest {
    static boolean isSubsequence(String sub, String s) {
        int i = 0;
        for (int j = 0; j < s.length() && i < sub.length(); j++) {
            if (s.charAt(j) == sub.charAt(i)) {
                i++;
            }
        }
        return i == sub.length();
    }

    /** Brute force over every subsequence of the left string. */
    static int brute(String a, String b) {
        int best = 0;
        for (int mask = 0; mask < (1 << a.length()); mask++) {
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < a.length(); i++) {
                if ((mask >> i & 1) == 1) {
                    sb.append(a.charAt(i));
                }
            }
            if (sb.length() > best && isSubsequence(sb.toString(), b)) {
                best = sb.length();
            }
        }
        return best;
    }

    @Test
    void seededStringsAreDeterministic() {
        ShellStrings s = ShellStrings.seeded(9);
        assertTrue(s.left().length() >= 4 && s.left().length() <= 10);
        assertEquals(s.right(), ShellStrings.seeded(9).right());
        assertThrows(IllegalArgumentException.class, () -> new ShellStrings("cx", "c"));
    }

    @Test
    void longestMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            ShellStrings s = ShellStrings.seeded(seed);
            assertEquals(brute(s.left(), s.right()), s.longest(), "LCS == brute force, seed " + seed);
            String m = s.bestMatch();
            assertEquals(s.longest(), m.length());
            assertTrue(isSubsequence(m, s.left()) && isSubsequence(m, s.right()), "walk-back fits both, seed " + seed);
        }
    }

    @Test
    void matchingTheFirstShellIsNotAlwaysBest() {
        // left starts with p; matching it to right's last p keeps 1, skipping it keeps "cws".
        ShellStrings s = new ShellStrings("pcws", "cwsp");
        assertEquals(3, s.longest());
        assertEquals("cws", s.bestMatch());
    }

    @Test
    void noSharedShellsMatchEmpty() {
        ShellStrings s = new ShellStrings("cc", "ww");
        assertEquals(0, s.longest());
        s.take("a", Side.LEFT, 0);
        s.take("b", Side.LEFT, 1);
        s.take("c", Side.RIGHT, 0);
        s.take("d", Side.RIGHT, 1);
        assertEquals(Outcome.WELL, s.compare("x"), "empty is the best these can do");
    }

    @Test
    void guards() {
        ShellStrings s = new ShellStrings("cw", "wc");
        assertEquals(Outcome.IGNORED, s.take("", Side.LEFT, 0));
        assertEquals(Outcome.NOT_THERE, s.take("e0", Side.LEFT, 5));
        assertEquals(Outcome.DIFFERENT, s.compare("m0"));
        assertEquals(Outcome.TAKEN, s.take("e1", Side.LEFT, 0));
        assertEquals(Outcome.DUPLICATE, s.take("e1", Side.LEFT, 1));
        assertEquals(Outcome.ALREADY_OFF, s.take("e2", Side.LEFT, 0));
        assertEquals(Outcome.NOT_THERE, s.putBack("e3", Side.RIGHT, 0));
        assertEquals(Outcome.PUT_BACK, s.putBack("e4", Side.LEFT, 0));
    }

    @Test
    void questShortThenWellThenKeeper() {
        ShellStrings s = new ShellStrings("pcws", "cwsp");
        assertEquals(String.format(KeeperShellLines.GREETING, "pcws", "cwsp"), s.talk("t0"));
        s.take("a1", Side.LEFT, 1);
        assertEquals("\"pws\" and \"cwsp\" so far.", KeeperShellLines.line(s));
        s.take("a2", Side.LEFT, 2);
        s.take("a3", Side.LEFT, 3);
        s.take("b1", Side.RIGHT, 0);
        s.take("b2", Side.RIGHT, 1);
        s.take("b3", Side.RIGHT, 2);
        assertEquals(KeeperShellLines.READY, s.talk("t1"));
        assertEquals(Outcome.SHORT, s.compare("m1"));
        assertEquals(String.format(KeeperShellLines.SHORT, 1, 3), s.talk("t2"));
        assertEquals("compare", s.quest().currentStep().type(), "no credit for short strings");
        s.putBack("p1", Side.LEFT, 1);
        s.putBack("p2", Side.LEFT, 2);
        s.putBack("p3", Side.LEFT, 3);
        s.take("p4", Side.LEFT, 0);
        s.putBack("p5", Side.RIGHT, 0);
        s.putBack("p6", Side.RIGHT, 1);
        s.putBack("p7", Side.RIGHT, 2);
        s.take("p8", Side.RIGHT, 3);
        assertEquals(Outcome.WELL, s.compare("m2"));
        assertEquals(KeeperShellLines.THANKS, s.talk("t3"));
        assertNull(s.quest().currentStep());
        assertEquals(KeeperShellLines.DONE, s.talk("t4"));
    }
}
