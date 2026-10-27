// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.driftwood;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.driftwood.DriftwoodCuts.Outcome;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class DriftwoodCutsTest {
    /** Brute force: every way to cut (each of the L-1 gaps cut or not); the most shells. */
    static int brute(DriftwoodCuts d) {
        int n = d.length();
        int best = 0;
        for (int mask = 0; mask < 1 << (n - 1); mask++) {
            List<Integer> pieces = new ArrayList<>();
            int run = 1;
            for (int g = 0; g < n - 1; g++) {
                if ((mask >> g & 1) == 1) {
                    pieces.add(run);
                    run = 1;
                } else {
                    run++;
                }
            }
            pieces.add(run);
            best = Math.max(best, d.worth(pieces));
        }
        return best;
    }

    /** Plank 4, prices 1, 5, 8, 9: two pieces of 2 fetch 10; the whole plank only 9, a 3 and a 1 fetch 9. */
    static DriftwoodCuts plank() {
        return new DriftwoodCuts(List.of(1, 5, 8, 9));
    }

    @Test
    void seededPlankIsDeterministic() {
        assertEquals(DriftwoodCuts.seeded(1).prices(), DriftwoodCuts.seeded(1).prices());
        assertEquals(DriftwoodCuts.seeded(1).best(), DriftwoodCuts.seeded(1).best());
        assertThrows(IllegalArgumentException.class, () -> new DriftwoodCuts(List.of()));
        assertThrows(IllegalArgumentException.class, () -> new DriftwoodCuts(List.of(1, -2)));
    }

    @Test
    void bestMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            DriftwoodCuts d = DriftwoodCuts.seeded(seed);
            assertEquals(brute(d), d.best(), "rod-cutting DP == brute force, seed " + seed);
        }
    }

    @Test
    void biggestPieceIsATrap() {
        DriftwoodCuts d = plank();
        assertEquals(10, d.best());
        assertEquals(Outcome.CHEAP, d.cut("c0", List.of(4)), "the whole plank fetches only 9");
        assertEquals(String.format(KeeperDriftwood.CHEAP, 9, 10), d.talk("t0"));
    }

    @Test
    void cheapWrongLengthAndNoBuyersEarnNoCredit() {
        DriftwoodCuts d = plank();
        d.measure("m");
        assertEquals(Outcome.CHEAP, d.cut("c1", List.of(3, 1)));
        assertEquals(Outcome.WRONG_LENGTH, d.cut("c2", List.of(2, 3)));
        assertEquals(KeeperDriftwood.WRONG_LENGTH, d.talk("t2"));
        assertEquals(Outcome.MALFORMED, d.cut("c3", List.of(5)));
        assertEquals("cut", d.quest().currentStep().type(), "no credit for a cheap or wrong cut");
        DriftwoodCuts none = new DriftwoodCuts(List.of(0, 0, 0));
        assertEquals(0, none.best());
        assertEquals(Outcome.NO_BUYERS, none.cut("x", List.of(3)));
        assertEquals(KeeperDriftwood.NO_BUYERS, none.talk("tx"));
    }

    @Test
    void guards() {
        DriftwoodCuts d = plank();
        assertEquals(Outcome.IGNORED, d.cut("", List.of(2, 2)));
        assertEquals(Outcome.IGNORED, d.cut("e", null));
        assertEquals(Outcome.MALFORMED, d.cut("e0", List.of(0, 4)));
        assertEquals(Outcome.BEST, d.cut("e1", List.of(2, 2)));
        assertEquals(Outcome.DUPLICATE, d.cut("e1", List.of(2, 2)));
    }

    @Test
    void questCheapThenBestThenKeeper() {
        DriftwoodCuts d = plank();
        assertEquals(String.format(KeeperDriftwood.GREETING, 4), d.talk("t0"));
        d.measure("m0");
        assertEquals(Outcome.CHEAP, d.cut("c1", List.of(4)));
        assertEquals(Outcome.BEST, d.cut("c2", List.of(2, 2)));
        assertEquals(KeeperDriftwood.THANKS, d.talk("t2"));
        assertNull(d.quest().currentStep());
        assertEquals(KeeperDriftwood.DONE, d.talk("t3"));
    }
}
