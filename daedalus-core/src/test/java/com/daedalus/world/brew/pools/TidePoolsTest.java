// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.pools;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.pools.TidePools.Outcome;
import org.junit.jupiter.api.Test;

class TidePoolsTest {
    /** Brute force: fill each level unit by unit and keep it if a rock walls it on both sides. */
    static int brute(TidePools p) {
        int top = 0;
        for (int i = 0; i < p.rocks(); i++) {
            top = Math.max(top, p.rock(i));
        }
        int water = 0;
        for (int level = 1; level <= top; level++) {
            for (int i = 0; i < p.rocks(); i++) {
                if (p.rock(i) >= level) {
                    continue;
                }
                boolean left = false;
                boolean right = false;
                for (int j = 0; j < i; j++) {
                    left |= p.rock(j) >= level;
                }
                for (int j = i + 1; j < p.rocks(); j++) {
                    right |= p.rock(j) >= level;
                }
                if (left && right) {
                    water++;
                }
            }
        }
        return water;
    }

    static TidePools shelf() {
        return new TidePools(0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1);
    }

    @Test
    void seededShelfIsDeterministic() {
        TidePools a = TidePools.seeded(9);
        TidePools b = TidePools.seeded(9);
        assertEquals(a.rocks(), b.rocks());
        for (int i = 0; i < a.rocks(); i++) {
            assertEquals(a.rock(i), b.rock(i));
        }
        assertThrows(IllegalArgumentException.class, () -> new TidePools());
        assertThrows(IllegalArgumentException.class, () -> new TidePools(2, -1));
    }

    @Test
    void heldMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            TidePools p = TidePools.seeded(seed);
            assertEquals(brute(p), p.held(), "two pointers == brute force, seed " + seed);
        }
    }

    @Test
    void knownShelfAndFlatShelf() {
        assertEquals(6, shelf().held());
        assertEquals(0, new TidePools(1, 2, 3, 4).held(), "a rising shelf holds nothing");
    }

    @Test
    void wrongReadingEarnsNoCredit() {
        TidePools p = shelf();
        p.walk("w");
        assertEquals(Outcome.WRONG, p.read("r1", 5));
        assertEquals(String.format(KeeperPoolLines.WRONG, 5), p.talk("t1"));
        assertEquals("read", p.quest().currentStep().type(), "no credit for a wrong reading");
    }

    @Test
    void guards() {
        TidePools p = shelf();
        assertEquals(Outcome.IGNORED, p.read(" ", 6));
        assertEquals(Outcome.WRONG, p.read("e1", 0));
        assertEquals(Outcome.DUPLICATE, p.read("e1", 6));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        TidePools p = shelf();
        assertEquals(String.format(KeeperPoolLines.GREETING, 12), p.talk("t0"));
        p.walk("w0");
        assertEquals(Outcome.WRONG, p.read("r1", 7));
        assertEquals(Outcome.RIGHT, p.read("r2", 6));
        assertEquals(KeeperPoolLines.THANKS, p.talk("t2"));
        assertNull(p.quest().currentStep());
        assertEquals(KeeperPoolLines.DONE, p.talk("t3"));
    }
}
