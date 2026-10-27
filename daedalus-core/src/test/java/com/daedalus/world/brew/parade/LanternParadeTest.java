// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.parade;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.parade.LanternParade.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class LanternParadeTest {
    static boolean strictlyRising(List<Walker> p) {
        for (int i = 1; i < p.size(); i++) {
            if (p.get(i).height() <= p.get(i - 1).height()) {
                return false;
            }
        }
        return true;
    }

    /** Brute force over every subset of the line, kept in line order. */
    static int brute(List<Walker> line) {
        int best = 0;
        for (int mask = 1; mask < (1 << line.size()); mask++) {
            int last = 0;
            int count = 0;
            boolean ok = true;
            for (int i = 0; i < line.size() && ok; i++) {
                if ((mask >> i & 1) == 1) {
                    ok = line.get(i).height() > last;
                    last = line.get(i).height();
                    count++;
                }
            }
            if (ok) {
                best = Math.max(best, count);
            }
        }
        return best;
    }

    static LanternParade small() {
        return new LanternParade(List.of(new Walker("ada", 9), new Walker("bram", 2), new Walker("coll", 5),
                new Walker("dilly", 3), new Walker("eno", 7), new Walker("fay", 8)));
    }

    @Test
    void seededLineIsDeterministic() {
        LanternParade p = LanternParade.seeded(2);
        assertTrue(p.line().size() >= 6 && p.line().size() <= 12);
        assertEquals(p.line(), LanternParade.seeded(2).line());
        assertThrows(IllegalArgumentException.class, () -> new Walker("x", 0));
    }

    @Test
    void longestMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            LanternParade p = LanternParade.seeded(seed);
            assertTrue(p.line().size() <= 12, "brute force stays small");
            assertEquals(brute(p.line()), p.longest(), "LIS == brute force, seed " + seed);
            assertTrue(strictlyRising(p.bestParade()), "walk-back parade rises, seed " + seed);
        }
    }

    @Test
    void theTallestFirstLanternIsNotAlwaysKept() {
        // ada's 9 at the front blocks everyone; the longest is bram 2, coll 5 (or dilly 3), eno 7, fay 8.
        LanternParade p = small();
        assertEquals(4, p.longest());
        assertTrue(p.bestParade().stream().noneMatch(w -> w.name().equals("ada")));
    }

    @Test
    void equalLanternsDoNotClimb() {
        LanternParade p = new LanternParade(List.of(new Walker("a", 4), new Walker("b", 4), new Walker("c", 4)));
        assertEquals(1, p.longest(), "strictly rising: equal heights don't count");
        p.keep("k1", "a");
        p.keep("k2", "b");
        assertEquals(Outcome.NOT_RISING, p.march("m1"));
        assertEquals("keep", p.quest().currentStep().type(), "no credit");
    }

    @Test
    void guards() {
        LanternParade p = small();
        assertEquals(Outcome.IGNORED, p.keep(null, "ada"));
        assertEquals(Outcome.UNKNOWN, p.keep("e0", "zed"));
        assertEquals(Outcome.EMPTY, p.march("m0"));
        assertEquals(Outcome.KEPT, p.keep("e1", "ada"));
        assertEquals(Outcome.DUPLICATE, p.keep("e1", "bram"));
        assertEquals(Outcome.ALREADY_KEPT, p.keep("e2", "ada"));
        assertEquals(Outcome.NOT_KEPT, p.seat("e3", "bram"));
        assertEquals(Outcome.SEATED, p.seat("e4", "ada"));
        assertThrows(IllegalArgumentException.class,
                () -> new LanternParade(List.of(new Walker("a", 1), new Walker("a", 2))));
    }

    @Test
    void questDimThenBrightThenKeeper() {
        LanternParade p = small();
        assertEquals(KeeperParadeLines.GREETING, p.talk("t0"));
        p.keep("k1", "ada");
        p.keep("k2", "bram");
        assertEquals("2 walking, but someone's lantern doesn't climb. Sit them out.", KeeperParadeLines.line(p));
        assertEquals(Outcome.NOT_RISING, p.march("m0"));
        p.seat("s1", "ada");
        p.keep("k3", "eno");
        assertEquals(Outcome.DIM, p.march("m1"));
        assertEquals(String.format(KeeperParadeLines.DIM, 2, 4), p.talk("t1"));
        p.keep("k4", "coll");
        p.keep("k5", "fay");
        assertEquals(Outcome.BRIGHT, p.march("m2"));
        assertEquals(KeeperParadeLines.THANKS, p.talk("t2"));
        assertNull(p.quest().currentStep());
        assertEquals(KeeperParadeLines.DONE, p.talk("t3"));
    }
}
