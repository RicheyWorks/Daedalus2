// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.applebaskets;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.applebaskets.AppleBaskets.Outcome;
import org.junit.jupiter.api.Test;

class AppleBasketsTest {
    /** Brute force: choose a count for each basket in turn; the last takes the rest. */
    static int brute(AppleBaskets a) {
        return share(a.apples(), a.baskets());
    }

    static int share(int left, int baskets) {
        if (baskets == 1) {
            return 1;
        }
        int n = 0;
        for (int k = 0; k <= left; k++) {
            n += share(left - k, baskets - 1);
        }
        return n;
    }

    /** 2 apples, 2 baskets: shares 2-0, 1-1, 0-2 (3), but 4 labelled picks. */
    static AppleBaskets fixture() {
        return new AppleBaskets(2, 2);
    }

    @Test
    void seededIsDeterministic() {
        assertEquals(AppleBaskets.seeded(1).apples(), AppleBaskets.seeded(1).apples());
        assertEquals(AppleBaskets.seeded(1).ways(), AppleBaskets.seeded(1).ways());
        assertThrows(IllegalArgumentException.class, () -> new AppleBaskets(-1, 2));
        assertThrows(IllegalArgumentException.class, () -> new AppleBaskets(2, 0));
    }

    @Test
    void answerMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            AppleBaskets r = AppleBaskets.seeded(seed);
            assertEquals(brute(r), r.ways(), "fast == brute force, seed " + seed);
            assertTrue(r.labelled() >= r.ways(), "labelled never fewer, seed " + seed);
        }
    }

    @Test
    void trap() {
        AppleBaskets r = fixture();
        assertEquals(3, r.ways());
        assertEquals(4, r.labelled());
        assertEquals(Outcome.WRONG, r.count("c0", 4), "alike apples: only the counts matter");
        assertEquals(String.format(KeeperAppleBaskets.WRONG, 4), r.talk("t0"));
    }

    @Test
    void wrongAndSpecialEarnNoCredit() {
        AppleBaskets r = fixture();
        r.read("r");
        assertEquals(Outcome.WRONG, r.count("c1", 3 + 1));
        assertEquals(Outcome.MALFORMED, r.count("c2", -1));
        assertEquals("count", r.quest().currentStep().type(), "no credit for a wrong answer");
        AppleBaskets sp = new AppleBaskets(0, 3);
        assertTrue(sp.noApples());
        assertEquals(Outcome.NO_APPLES, sp.count("x", 0));
        assertEquals(KeeperAppleBaskets.NO_APPLES, sp.talk("tx"));
    }

    @Test
    void guards() {
        AppleBaskets r = fixture();
        assertEquals(Outcome.IGNORED, r.count("", 3));
        assertEquals(Outcome.IGNORED, r.count(null, 3));
        assertEquals(Outcome.RIGHT, r.count("e1", 3));
        assertEquals(Outcome.DUPLICATE, r.count("e1", 3));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        AppleBaskets r = fixture();
        assertEquals(String.format(KeeperAppleBaskets.GREETING, 2, 2), r.talk("t0"));
        r.read("r0");
        assertEquals(Outcome.WRONG, r.count("c1", 4));
        assertEquals(Outcome.RIGHT, r.count("c2", 3));
        assertEquals(KeeperAppleBaskets.THANKS, r.talk("t2"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperAppleBaskets.DONE, r.talk("t3"));
    }
}
