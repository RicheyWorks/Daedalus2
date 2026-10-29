// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.crabs;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.crabs.CrabPens.Outcome;
import org.junit.jupiter.api.Test;

class CrabPensTest {
    /** Brute force: multiply the crabs moon by moon, keeping only the remainder. */
    static long brute(CrabPens c) {
        long crabs = 1;
        for (long m = 0; m < c.moons(); m++) {
            crabs = crabs * c.brood() % c.pen();
        }
        return crabs;
    }

    /** Brood 3, 13 moons, pens of 7: 3^13 = 1594323 leaves 3; brood times moons (39) would leave 4. */
    static CrabPens pens() {
        return new CrabPens(3, 13, 7);
    }

    @Test
    void seededPensAreDeterministic() {
        assertEquals(CrabPens.seeded(1).leftOver(), CrabPens.seeded(1).leftOver());
        assertEquals(CrabPens.seeded(1).moons(), CrabPens.seeded(1).moons());
        assertThrows(IllegalArgumentException.class, () -> new CrabPens(2, 0, 5));
        assertThrows(IllegalArgumentException.class, () -> new CrabPens(2, 3, 1));
    }

    @Test
    void leftOverMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            CrabPens c = CrabPens.seeded(seed);
            assertEquals(brute(c), c.leftOver(), "binary exponentiation == brute force, seed " + seed);
            assertTrue(c.multiplications() <= 12, "few multiplications, seed " + seed);
        }
        CrabPens big = new CrabPens(2, 1_000_000_000L, 1_000_000);
        assertTrue(big.multiplications() <= 60, "a billion moons in under 60 multiplications");
    }

    @Test
    void broodTimesMoonsIsATrap() {
        CrabPens c = pens();
        assertEquals(3, c.leftOver());
        assertEquals(Outcome.WRONG, c.count("c0", 4), "3 x 13 = 39 leaves 4, but crabs multiply");
        assertEquals(String.format(KeeperCrabPens.WRONG, 4), c.talk("t0"));
    }

    @Test
    void wrongAndWashedOutEarnNoCredit() {
        CrabPens c = pens();
        c.watch("w");
        assertEquals(Outcome.WRONG, c.count("c1", 1));
        assertEquals(Outcome.MALFORMED, c.count("c2", 7));
        assertEquals("count", c.quest().currentStep().type(), "no credit for a wrong count");
        CrabPens washed = new CrabPens(14, 5, 7);
        assertEquals(0, washed.leftOver());
        assertEquals(Outcome.WASHED_OUT, washed.count("x", 0));
        assertEquals(KeeperCrabPens.WASHED_OUT, washed.talk("tx"));
    }

    @Test
    void guards() {
        CrabPens c = pens();
        assertEquals(Outcome.IGNORED, c.count("", 3));
        assertEquals(Outcome.IGNORED, c.count(null, 3));
        assertEquals(Outcome.MALFORMED, c.count("e0", -1));
        assertEquals(Outcome.RIGHT, c.count("e1", 3));
        assertEquals(Outcome.DUPLICATE, c.count("e1", 3));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        CrabPens c = pens();
        assertEquals(String.format(KeeperCrabPens.GREETING, 3, 13, 7), c.talk("t0"));
        c.watch("w0");
        assertEquals(Outcome.WRONG, c.count("c1", 4));
        assertEquals(Outcome.RIGHT, c.count("c2", 3));
        assertEquals(KeeperCrabPens.THANKS, c.talk("t2"));
        assertNull(c.quest().currentStep());
        assertEquals(KeeperCrabPens.DONE, c.talk("t3"));
    }
}
