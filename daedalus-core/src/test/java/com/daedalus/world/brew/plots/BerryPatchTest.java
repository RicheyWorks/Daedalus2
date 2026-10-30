// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.plots;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.plots.BerryPatch.Outcome;
import org.junit.jupiter.api.Test;

class BerryPatchTest {
    /** Brute force: add every bush in the rectangle. */
    static long brute(BerryPatch b, int r0, int c0, int r1, int c1) {
        long s = 0;
        for (int i = r0; i < r1; i++) {
            for (int j = c0; j < c1; j++) {
                s += b.berries(i, j);
            }
        }
        return s;
    }

    /** The single richest bush (9) sits in a poor corner; the 2x2 square at (1,1) has 4+4+4+4 = 16. */
    static BerryPatch patch() {
        return new BerryPatch(new int[][] {{9, 0, 0}, {0, 4, 4}, {0, 4, 4}}, 2);
    }

    @Test
    void seededPatchIsDeterministic() {
        assertEquals(BerryPatch.seeded(1).richest(), BerryPatch.seeded(1).richest());
        assertEquals(BerryPatch.seeded(1).side(), BerryPatch.seeded(1).side());
        assertThrows(IllegalArgumentException.class, () -> new BerryPatch(new int[][] {{1, 2}}, 2));
        assertThrows(IllegalArgumentException.class, () -> new BerryPatch(new int[][] {{1}, {1, 2}}, 1));
    }

    @Test
    void sumsAndRichestMatchBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            BerryPatch b = BerryPatch.seeded(seed);
            long best = 0;
            for (int r0 = 0; r0 < b.rows(); r0++) {
                for (int c0 = 0; c0 < b.cols(); c0++) {
                    for (int r1 = r0 + 1; r1 <= b.rows(); r1++) {
                        for (int c1 = c0 + 1; c1 <= b.cols(); c1++) {
                            assertEquals(brute(b, r0, c0, r1, c1), b.sum(r0, c0, r1, c1), "seed " + seed);
                            if (r1 - r0 == b.side() && c1 - c0 == b.side()) {
                                best = Math.max(best, brute(b, r0, c0, r1, c1));
                            }
                        }
                    }
                }
            }
            assertEquals(best, b.richest(), "prefix sums == brute force, seed " + seed);
        }
    }

    @Test
    void richestBushIsATrap() {
        BerryPatch b = patch();
        assertEquals(13, b.sum(0, 0, 2, 2));
        assertEquals(16, b.richest());
    }

    @Test
    void poorEarnsNoCredit() {
        BerryPatch b = patch();
        b.count("c");
        assertEquals(Outcome.POOR, b.pick("p0", 0, 0));
        assertEquals(String.format(KeeperBerryLines.POOR, 13, 16), b.talk("t0"));
        assertEquals("pick", b.quest().currentStep().type(), "no credit for a poor square");
    }

    @Test
    void guards() {
        BerryPatch b = patch();
        assertEquals(Outcome.IGNORED, b.pick("", 1, 1));
        assertEquals(Outcome.NOT_THERE, b.pick("e0", 2, 2));
        assertEquals(Outcome.RICHEST, b.pick("e1", 1, 1));
        assertEquals(Outcome.DUPLICATE, b.pick("e1", 1, 1));
    }

    @Test
    void questPoorThenRichestThenKeeper() {
        BerryPatch b = patch();
        assertEquals(String.format(KeeperBerryLines.GREETING, 3, 3, 2, 2), b.talk("t0"));
        b.count("c0");
        assertEquals(Outcome.POOR, b.pick("p1", 0, 0));
        assertEquals(Outcome.RICHEST, b.pick("p2", 1, 1));
        assertEquals(KeeperBerryLines.THANKS, b.talk("t2"));
        assertNull(b.quest().currentStep());
        assertEquals(KeeperBerryLines.DONE, b.talk("t3"));
    }
}
