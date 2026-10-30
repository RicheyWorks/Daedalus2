// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.rope;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.rope.RopeMarket.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class RopeMarketTest {
    /** Brute force over every way to cut: each of the coil-1 gaps is cut or not. */
    static int brute(RopeMarket r) {
        int n = r.coil();
        int best = 0;
        for (int mask = 0; mask < (1 << (n - 1)); mask++) {
            int value = 0;
            int run = 1;
            for (int gap = 0; gap < n - 1; gap++) {
                if ((mask >> gap & 1) == 1) {
                    value += r.price(run);
                    run = 1;
                } else {
                    run++;
                }
            }
            best = Math.max(best, value + r.price(run));
        }
        return best;
    }

    /** Lengths 1-4 pay 1, 5, 8, 9: the whole 4 fetches 9, two 2s fetch 10. */
    static RopeMarket small() {
        return new RopeMarket(4, List.of(1, 5, 8, 9));
    }

    @Test
    void seededMarketIsDeterministic() {
        RopeMarket r = RopeMarket.seeded(6);
        assertTrue(r.coil() >= 6 && r.coil() <= 12);
        assertEquals(r.price(r.coil()), RopeMarket.seeded(6).price(r.coil()));
        assertThrows(IllegalArgumentException.class, () -> new RopeMarket(3, List.of(1, 2)));
    }

    @Test
    void bestPriceMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            RopeMarket r = RopeMarket.seeded(seed);
            assertTrue(r.coil() <= 12, "brute force stays small");
            assertEquals(brute(r), r.bestPrice(), "DP == brute force, seed " + seed);
            assertEquals(r.coil(), r.bestCuts().stream().mapToInt(Integer::intValue).sum(), "walk-back uses the coil");
            assertEquals(r.bestPrice(), r.bestCuts().stream().mapToInt(r::price).sum(), "walk-back fetches it");
        }
    }

    @Test
    void theWholeCoilIsNotAlwaysBest() {
        RopeMarket r = small();
        assertEquals(10, r.bestPrice());
        assertEquals(List.of(2, 2), r.bestCuts());
    }

    @Test
    void zeroPricedLengthsCanStillBeSold() {
        RopeMarket r = new RopeMarket(2, List.of(0, 0));
        assertEquals(0, r.bestPrice());
        r.cut("c1", 2);
        assertEquals(Outcome.RICH, r.sell("s1"), "nothing better was possible");
    }

    @Test
    void guards() {
        RopeMarket r = small();
        assertEquals(Outcome.IGNORED, r.cut(null, 2));
        assertEquals(Outcome.UNKNOWN, r.cut("e0", 9));
        assertEquals(Outcome.ROPE_LEFT, r.sell("s0"));
        assertEquals(Outcome.CUT, r.cut("e1", 3));
        assertEquals(Outcome.DUPLICATE, r.cut("e1", 1));
        assertEquals(Outcome.TOO_LONG, r.cut("e2", 2));
        assertEquals(Outcome.NOT_CUT, r.join("e3", 2));
        assertEquals(Outcome.JOINED, r.join("e4", 3));
        assertEquals(4, r.left());
    }

    @Test
    void questThinThenRichThenKeeper() {
        RopeMarket r = small();
        assertEquals(KeeperRopeLines.GREETING, r.talk("t0"));
        r.cut("c1", 1);
        assertEquals("1 pieces cut, 3 left on the coil.", KeeperRopeLines.line(r));
        r.cut("c2", 1);
        r.cut("c3", 2);
        assertEquals(KeeperRopeLines.READY, r.talk("t1"));
        assertEquals(Outcome.THIN, r.sell("s1"));
        assertEquals(String.format(KeeperRopeLines.THIN, 7, 10), r.talk("t2"));
        assertEquals("sell", r.quest().currentStep().type(), "no credit for a thin sale");
        r.join("j1", 1);
        r.join("j2", 1);
        r.cut("c4", 2);
        assertEquals(Outcome.RICH, r.sell("s2"));
        assertEquals(KeeperRopeLines.THANKS, r.talk("t3"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperRopeLines.DONE, r.talk("t4"));
    }
}
