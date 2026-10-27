// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.echo;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.echo.EchoCave.Outcome;
import org.junit.jupiter.api.Test;

class EchoCaveTest {
    static boolean palindrome(String s) {
        return new StringBuilder(s).reverse().toString().equals(s);
    }

    /** Brute force over every subsequence of the marks. */
    static int brute(String s) {
        int best = 0;
        for (int mask = 1; mask < (1 << s.length()); mask++) {
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < s.length(); i++) {
                if ((mask >> i & 1) == 1) {
                    sb.append(s.charAt(i));
                }
            }
            if (sb.length() > best && palindrome(sb.toString())) {
                best = sb.length();
            }
        }
        return best;
    }

    @Test
    void seededWallIsDeterministic() {
        EchoCave c = EchoCave.seeded(5);
        assertTrue(c.marks().length() >= 4 && c.marks().length() <= 12);
        assertEquals(c.marks(), EchoCave.seeded(5).marks());
        assertThrows(IllegalArgumentException.class, () -> new EchoCave("dx"));
    }

    @Test
    void longestMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            EchoCave c = EchoCave.seeded(seed);
            assertEquals(brute(c.marks()), c.longest(), "LPS == brute force, seed " + seed);
            String b = c.bestChant();
            assertEquals(c.longest(), b.length());
            assertTrue(palindrome(b) && EchoCave.inOrder(b, c.marks()), "walk-back echoes, seed " + seed);
        }
    }

    @Test
    void skippingAMarkCanPay() {
        EchoCave c = new EchoCave("drmrsd");
        assertEquals(5, c.longest());
        assertEquals(Outcome.WELL, c.sing("s", "drmrd"));
    }

    @Test
    void noEchoEarnsNoCredit() {
        EchoCave c = new EchoCave("drmrsd");
        c.read("r");
        assertEquals(Outcome.NO_ECHO, c.sing("s1", "drm"));
        assertEquals(String.format(KeeperEchoLines.NO_ECHO, "drm"), c.talk("t1"));
        assertEquals("sing", c.quest().currentStep().type(), "no credit without an echo");
    }

    @Test
    void guards() {
        EchoCave c = new EchoCave("drmrsd");
        assertEquals(Outcome.IGNORED, c.sing("", "d"));
        assertEquals(Outcome.NOT_ON_WALL, c.sing("e0", "ff"));
        assertEquals(Outcome.NOT_ON_WALL, c.sing("e0", "sm"));
        assertEquals(Outcome.SHORT, c.sing("e1", "d"));
        assertEquals(Outcome.DUPLICATE, c.sing("e1", "drmrd"));
    }

    @Test
    void questShortThenWellThenKeeper() {
        EchoCave c = new EchoCave("drmrsd");
        assertEquals(String.format(KeeperEchoLines.GREETING, "drmrsd"), c.talk("t0"));
        c.read("r0");
        assertEquals(Outcome.SHORT, c.sing("s1", "rmr"));
        assertEquals(String.format(KeeperEchoLines.SHORT, 3, 5), c.talk("t1"));
        assertEquals("sing", c.quest().currentStep().type(), "no credit for a short echo");
        assertEquals(Outcome.WELL, c.sing("s2", "drmrd"));
        assertEquals(KeeperEchoLines.THANKS, c.talk("t2"));
        assertNull(c.quest().currentStep());
        assertEquals(KeeperEchoLines.DONE, c.talk("t3"));
    }
}
