// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.giftswap;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.giftswap.GiftSwap.Outcome;
import org.junit.jupiter.api.Test;

class GiftSwapTest {
    /** Brute force: every draw (permutation), counting those with no friend drawing their own gift. */
    static int brute(GiftSwap g) {
        return draws(g.friends(), 0, new boolean[g.friends()]);
    }

    static int draws(int n, int who, boolean[] taken) {
        if (who == n) {
            return 1;
        }
        int ways = 0;
        for (int gift = 0; gift < n; gift++) {
            if (gift != who && !taken[gift]) {
                taken[gift] = true;
                ways += draws(n, who + 1, taken);
                taken[gift] = false;
            }
        }
        return ways;
    }

    /** 3 friends: draws 231 and 312 work (2), not every draw but 123 (5). */
    static GiftSwap fixture() {
        return new GiftSwap(3);
    }

    @Test
    void seededIsDeterministic() {
        assertEquals(GiftSwap.seeded(1).friends(), GiftSwap.seeded(1).friends());
        assertEquals(GiftSwap.seeded(1).ways(), GiftSwap.seeded(1).ways());
        assertThrows(IllegalArgumentException.class, () -> new GiftSwap(0));
        assertThrows(IllegalArgumentException.class, () -> new GiftSwap(13));
    }

    @Test
    void answerMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            GiftSwap r = GiftSwap.seeded(seed);
            assertEquals(brute(r), r.ways(), "fast == brute force, seed " + seed);
            assertTrue(r.allButOne() >= r.ways(), "never more good draws than all but one, seed " + seed);
        }
    }

    @Test
    void trap() {
        GiftSwap r = fixture();
        assertEquals(2, r.ways());
        assertEquals(5, r.allButOne());
        assertEquals(Outcome.WRONG, r.count("c0", 5), "one friend keeping their gift fails too");
        assertEquals(String.format(KeeperGiftSwap.WRONG, 5), r.talk("t0"));
    }

    @Test
    void wrongAndSpecialEarnNoCredit() {
        GiftSwap r = fixture();
        r.read("r");
        assertEquals(Outcome.WRONG, r.count("c1", 2 + 1));
        assertEquals(Outcome.MALFORMED, r.count("c2", -1));
        assertEquals("count", r.quest().currentStep().type(), "no credit for a wrong answer");
        GiftSwap sp = new GiftSwap(1);
        assertTrue(sp.alone());
        assertEquals(Outcome.ALONE, sp.count("x", 0));
        assertEquals(KeeperGiftSwap.ALONE, sp.talk("tx"));
    }

    @Test
    void guards() {
        GiftSwap r = fixture();
        assertEquals(Outcome.IGNORED, r.count("", 2));
        assertEquals(Outcome.IGNORED, r.count(null, 2));
        assertEquals(Outcome.RIGHT, r.count("e1", 2));
        assertEquals(Outcome.DUPLICATE, r.count("e1", 2));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        GiftSwap r = fixture();
        assertEquals(String.format(KeeperGiftSwap.GREETING, 3), r.talk("t0"));
        r.read("r0");
        assertEquals(Outcome.WRONG, r.count("c1", 5));
        assertEquals(Outcome.RIGHT, r.count("c2", 2));
        assertEquals(KeeperGiftSwap.THANKS, r.talk("t2"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperGiftSwap.DONE, r.talk("t3"));
    }
}
