// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.hives;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.hives.LuckyHives.Outcome;
import org.junit.jupiter.api.Test;

class LuckyHivesTest {
    /** Brute force: trial division by every smaller number. */
    static boolean brute(int n) {
        if (n < 2) {
            return false;
        }
        for (int d = 2; d < n; d++) {
            if (n % d == 0) {
                return false;
            }
        }
        return true;
    }

    @Test
    void seededHillIsDeterministic() {
        assertEquals(LuckyHives.seeded(3).hives(), LuckyHives.seeded(3).hives());
        assertThrows(IllegalArgumentException.class, () -> new LuckyHives(0));
        assertThrows(IllegalArgumentException.class, () -> new LuckyHives(100_001));
    }

    @Test
    void sieveMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            LuckyHives h = LuckyHives.seeded(seed);
            int count = 0;
            for (int n = 1; n <= h.hives(); n++) {
                assertEquals(brute(n), h.isLucky(n), "sieve == trial division, seed " + seed + " hive " + n);
                count += brute(n) ? 1 : 0;
            }
            assertEquals(count, h.lucky(), "seed " + seed);
        }
    }

    @Test
    void oddsAndOneAreTraps() {
        LuckyHives h = new LuckyHives(30);
        assertEquals(10, h.lucky());
        assertFalse(h.isLucky(1));
        assertFalse(h.isLucky(9), "odd is not lucky");
        assertEquals(Outcome.MISCOUNT, h.count("c0", 11));
        assertEquals(String.format(KeeperHiveLines.MISCOUNT, 11, 10), h.talk("t0"));
    }

    @Test
    void miscountEarnsNoCredit() {
        LuckyHives h = new LuckyHives(30);
        h.visit("v");
        assertEquals(Outcome.MISCOUNT, h.count("c1", 15));
        assertEquals("count", h.quest().currentStep().type(), "no credit for a miscount");
    }

    @Test
    void guards() {
        LuckyHives h = new LuckyHives(30);
        assertEquals(Outcome.IGNORED, h.count("", 10));
        assertEquals(Outcome.IGNORED, h.count("e0", -1));
        assertEquals(Outcome.COUNTED, h.count("e1", 10));
        assertEquals(Outcome.DUPLICATE, h.count("e1", 10));
        assertEquals(0, new LuckyHives(1).lucky());
    }

    @Test
    void questMiscountThenCountedThenKeeper() {
        LuckyHives h = new LuckyHives(30);
        assertEquals(String.format(KeeperHiveLines.GREETING, 30), h.talk("t0"));
        h.visit("v0");
        assertEquals(Outcome.MISCOUNT, h.count("c1", 11));
        assertEquals(Outcome.COUNTED, h.count("c2", 10));
        assertEquals(KeeperHiveLines.THANKS, h.talk("t2"));
        assertNull(h.quest().currentStep());
        assertEquals(KeeperHiveLines.DONE, h.talk("t3"));
    }
}
