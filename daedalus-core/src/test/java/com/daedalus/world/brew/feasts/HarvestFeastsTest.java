// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.feasts;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.feasts.HarvestFeasts.Outcome;
import org.junit.jupiter.api.Test;

class HarvestFeastsTest {
    /** Brute force over every subset of feasts. */
    static int brute(HarvestFeasts h) {
        int n = h.feasts();
        int best = 0;
        for (int mask = 0; mask < (1 << n); mask++) {
            boolean ok = true;
            int sum = 0;
            for (int i = 0; i < n && ok; i++) {
                if ((mask >> i & 1) == 1) {
                    sum += h.cheer(i);
                    for (int j = i + 1; j < n && ok; j++) {
                        if ((mask >> j & 1) == 1
                                && HarvestFeasts.clash(h.start(i), h.end(i), h.start(j), h.end(j))) {
                            ok = false;
                        }
                    }
                }
            }
            if (ok) {
                best = Math.max(best, sum);
            }
        }
        return best;
    }

    /** Feast 0 [0,6) cheer 5; feast 1 [0,3) cheer 3; feast 2 [3,6) cheer 3. */
    static HarvestFeasts trap() {
        return new HarvestFeasts(new int[] {0, 0, 3}, new int[] {6, 3, 6}, new int[] {5, 3, 3});
    }

    @Test
    void seededBookIsDeterministic() {
        HarvestFeasts h = HarvestFeasts.seeded(8);
        assertTrue(h.feasts() >= 3 && h.feasts() <= 12);
        assertEquals(h.most(), HarvestFeasts.seeded(8).most());
        assertThrows(IllegalArgumentException.class, () -> new HarvestFeasts(new int[] {2}, new int[] {2},
                new int[] {1}));
    }

    @Test
    void mostMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            HarvestFeasts h = HarvestFeasts.seeded(seed);
            assertEquals(brute(h), h.most(), "weighted interval DP == brute force, seed " + seed);
        }
    }

    @Test
    void twoSmallFeastsCanBeatOneBig() {
        assertEquals(6, trap().most(), "touching feasts [0,3) and [3,6) do not overlap");
    }

    @Test
    void overlapEarnsNoCredit() {
        HarvestFeasts h = trap();
        h.toggle("b0", 0);
        h.toggle("b1", 1);
        assertEquals(Outcome.OVERLAP, h.open("o1"));
        assertArrayEquals(new int[] {0, 1}, h.overlap());
        assertEquals(String.format(KeeperFeastLines.OVERLAP, 0, 1), h.talk("t1"));
        assertEquals("open", h.quest().currentStep().type(), "no credit for an overlap");
    }

    @Test
    void guards() {
        HarvestFeasts h = trap();
        assertEquals(Outcome.IGNORED, h.toggle("", 0));
        assertEquals(Outcome.NOT_THERE, h.toggle("e0", 3));
        assertEquals(Outcome.BOOKED, h.toggle("e1", 0));
        assertEquals(Outcome.DUPLICATE, h.toggle("e1", 1));
        assertEquals(Outcome.STRUCK, h.toggle("e2", 0));
    }

    @Test
    void questDimThenWellThenKeeper() {
        HarvestFeasts h = trap();
        assertEquals(String.format(KeeperFeastLines.GREETING, 3), h.talk("t0"));
        h.toggle("b0", 0);
        assertEquals(Outcome.DIM, h.open("o1"));
        assertEquals(String.format(KeeperFeastLines.DIM, 5, 6), h.talk("t1"));
        assertEquals("open", h.quest().currentStep().type(), "no credit for a dim book");
        h.toggle("b1", 0);
        h.toggle("b2", 1);
        h.toggle("b3", 2);
        assertEquals(Outcome.WELL, h.open("o2"));
        assertEquals(KeeperFeastLines.THANKS, h.talk("t2"));
        assertNull(h.quest().currentStep());
        assertEquals(KeeperFeastLines.DONE, h.talk("t3"));
    }
}
