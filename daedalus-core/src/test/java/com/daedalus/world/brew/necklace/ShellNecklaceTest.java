// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.necklace;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.necklace.ShellNecklace.Outcome;
import java.util.HashSet;
import java.util.Set;
import org.junit.jupiter.api.Test;

class ShellNecklaceTest {
    /** Brute force: a set of every substring. */
    static int brute(ShellNecklace s) {
        Set<String> seen = new HashSet<>();
        for (int i = 0; i < s.shells().length(); i++) {
            for (int j = i + 1; j <= s.shells().length(); j++) {
                seen.add(s.shells().substring(i, j));
            }
        }
        return seen.size();
    }

    /** Necklace aaa: bracelets a, aa, aaa (3), from 6 cuts. */
    static ShellNecklace fixture() {
        return new ShellNecklace("aaa");
    }

    @Test
    void seededIsDeterministic() {
        assertEquals(ShellNecklace.seeded(1).shells(), ShellNecklace.seeded(1).shells());
        assertEquals(ShellNecklace.seeded(1).distinct(), ShellNecklace.seeded(1).distinct());
        assertThrows(IllegalArgumentException.class, () -> new ShellNecklace(null));
        assertThrows(IllegalArgumentException.class, () -> new ShellNecklace("A"));
    }

    @Test
    void answerMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            ShellNecklace r = ShellNecklace.seeded(seed);
            assertEquals(brute(r), r.distinct(), "fast == brute force, seed " + seed);
            assertTrue(r.cuts() >= r.distinct(), "never more bracelets than cuts, seed " + seed);
        }
    }

    @Test
    void trap() {
        ShellNecklace r = fixture();
        assertEquals(3, r.distinct());
        assertEquals(6, r.cuts());
        assertEquals(Outcome.WRONG, r.count("c0", 6), "same shells in the same order are one bracelet");
        assertEquals(String.format(KeeperShellNecklace.WRONG, 6), r.talk("t0"));
    }

    @Test
    void wrongAndSpecialEarnNoCredit() {
        ShellNecklace r = fixture();
        r.read("r");
        assertEquals(Outcome.WRONG, r.count("c1", 3 + 1));
        assertEquals(Outcome.MALFORMED, r.count("c2", -1));
        assertEquals("count", r.quest().currentStep().type(), "no credit for a wrong answer");
        ShellNecklace sp = new ShellNecklace("");
        assertTrue(sp.bare());
        assertEquals(Outcome.BARE, sp.count("x", 0));
        assertEquals(KeeperShellNecklace.BARE, sp.talk("tx"));
    }

    @Test
    void guards() {
        ShellNecklace r = fixture();
        assertEquals(Outcome.IGNORED, r.count("", 3));
        assertEquals(Outcome.IGNORED, r.count(null, 3));
        assertEquals(Outcome.RIGHT, r.count("e1", 3));
        assertEquals(Outcome.DUPLICATE, r.count("e1", 3));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        ShellNecklace r = fixture();
        assertEquals(String.format(KeeperShellNecklace.GREETING, "aaa"), r.talk("t0"));
        r.read("r0");
        assertEquals(Outcome.WRONG, r.count("c1", 6));
        assertEquals(Outcome.RIGHT, r.count("c2", 3));
        assertEquals(KeeperShellNecklace.THANKS, r.talk("t2"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperShellNecklace.DONE, r.talk("t3"));
    }
}
