// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.chant;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.chant.MirrorChant.Outcome;
import org.junit.jupiter.api.Test;

class MirrorChantTest {
    /** Brute force: check every stretch. */
    static int brute(String s) {
        int best = 0;
        for (int i = 0; i < s.length(); i++) {
            for (int j = i + 1; j <= s.length(); j++) {
                String t = s.substring(i, j);
                if (new StringBuilder(t).reverse().toString().equals(t)) {
                    best = Math.max(best, t.length());
                }
            }
        }
        return best;
    }

    /** "abacddca": the odd mirror "aba" is 3, the even mirror "acddca" is 6. */
    static MirrorChant chant() {
        return new MirrorChant("abacddca");
    }

    @Test
    void seededChantIsDeterministic() {
        assertEquals(MirrorChant.seeded(4).chant(), MirrorChant.seeded(4).chant());
        assertThrows(IllegalArgumentException.class, () -> new MirrorChant(""));
        assertThrows(IllegalArgumentException.class, () -> new MirrorChant("ab1"));
    }

    @Test
    void longestMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            MirrorChant c = MirrorChant.seeded(seed);
            assertEquals(brute(c.chant()), c.longest(), "Manacher == brute force, seed " + seed);
            String v = c.verse();
            assertEquals(new StringBuilder(v).reverse().toString(), v, "seed " + seed);
            assertEquals(c.longest(), v.length());
        }
    }

    @Test
    void evenMirrorsCount() {
        MirrorChant c = chant();
        assertEquals(6, c.longest());
        assertEquals("acddca", c.verse());
        assertEquals(Outcome.SHORT, c.mark("m0", 0, 3));
        assertEquals(String.format(KeeperChantLines.SHORT, 3, 6), c.talk("t0"));
    }

    @Test
    void brokenEarnsNoCredit() {
        MirrorChant c = chant();
        c.hear("h");
        assertEquals(Outcome.BROKEN, c.mark("m1", 2, 6));
        assertEquals(String.format(KeeperChantLines.BROKEN, "acdd"), c.talk("t1"));
        assertEquals("mark", c.quest().currentStep().type(), "no credit for a broken mirror");
    }

    @Test
    void guards() {
        MirrorChant c = chant();
        assertEquals(Outcome.IGNORED, c.mark("", 1, 7));
        assertEquals(Outcome.NOT_THERE, c.mark("e0", 3, 3));
        assertEquals(Outcome.NOT_THERE, c.mark("e0", 1, 9));
        assertEquals(Outcome.MIRROR, c.mark("e1", 2, 8));
        assertEquals(Outcome.DUPLICATE, c.mark("e1", 2, 8));
    }

    @Test
    void questShortThenMirrorThenKeeper() {
        MirrorChant c = chant();
        assertEquals(String.format(KeeperChantLines.GREETING, "abacddca"), c.talk("t0"));
        c.hear("h0");
        assertEquals(Outcome.SHORT, c.mark("m1", 0, 3));
        assertEquals(Outcome.MIRROR, c.mark("m2", 2, 8));
        assertEquals(KeeperChantLines.THANKS, c.talk("t2"));
        assertNull(c.quest().currentStep());
        assertEquals(KeeperChantLines.DONE, c.talk("t3"));
    }
}
