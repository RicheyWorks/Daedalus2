// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.crews;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.crews.FishingCrews.Outcome;
import org.junit.jupiter.api.Test;

class FishingCrewsTest {
    /** Brute force over every permutation of crews. */
    static int brute(FishingCrews f) {
        return perm(f, 0, new boolean[f.boats()]);
    }

    static int perm(FishingCrews f, int boat, boolean[] used) {
        if (boat == f.boats()) {
            return 0;
        }
        int best = Integer.MAX_VALUE;
        for (int c = 0; c < f.boats(); c++) {
            if (!used[c]) {
                used[c] = true;
                best = Math.min(best, f.hours(boat, c) + perm(f, boat + 1, used));
                used[c] = false;
            }
        }
        return best;
    }

    /** Greedy picks crew 0 for boat 0 (1 hour) and pays 9 later; the best is 3 + 3 + 2 = 8. */
    static FishingCrews harbour() {
        return new FishingCrews(new int[][] {{1, 3, 9}, {9, 9, 3}, {2, 9, 9}});
    }

    @Test
    void seededHarbourIsDeterministic() {
        FishingCrews a = FishingCrews.seeded(4);
        FishingCrews b = FishingCrews.seeded(4);
        assertEquals(a.boats(), b.boats());
        assertEquals(a.hours(1, 0), b.hours(1, 0));
        assertThrows(IllegalArgumentException.class, () -> new FishingCrews(new int[][] {{1, 2}}));
        assertThrows(IllegalArgumentException.class, () -> new FishingCrews(new int[][] {{-1}}));
    }

    @Test
    void fewestMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            FishingCrews f = FishingCrews.seeded(seed);
            assertEquals(brute(f), f.fewest(), "subset DP == every permutation, seed " + seed);
        }
    }

    @Test
    void greedyIsNotBest() {
        FishingCrews f = harbour();
        assertEquals(8, f.fewest());
        assertEquals(Outcome.COSTLY, f.rota("g", 0, 2, 1), "greedy 1 + 3 + 9 = 13");
        assertEquals(13, f.cost());
    }

    @Test
    void clashEarnsNoCredit() {
        FishingCrews f = harbour();
        f.ask("a");
        assertEquals(Outcome.CLASH, f.rota("r1", 1, 2, 1));
        assertEquals(KeeperCrewLines.CLASH, f.talk("t1"));
        assertEquals("rota", f.quest().currentStep().type(), "no credit for a clash");
    }

    @Test
    void guards() {
        FishingCrews f = harbour();
        assertEquals(Outcome.IGNORED, f.rota("", 1, 2, 0));
        assertEquals(Outcome.NOT_THERE, f.rota("e0", 1, 2));
        assertEquals(Outcome.NOT_THERE, f.rota("e0", 1, 2, 3));
        assertEquals(Outcome.WELL, f.rota("e1", 1, 2, 0));
        assertEquals(Outcome.DUPLICATE, f.rota("e1", 0, 1, 2));
    }

    @Test
    void questCostlyThenWellThenKeeper() {
        FishingCrews f = harbour();
        assertEquals(String.format(KeeperCrewLines.GREETING, 3, 3), f.talk("t0"));
        f.ask("a0");
        assertEquals(Outcome.COSTLY, f.rota("r1", 0, 2, 1));
        assertEquals(String.format(KeeperCrewLines.COSTLY, 13, 8), f.talk("t1"));
        assertEquals(Outcome.WELL, f.rota("r2", 1, 2, 0));
        assertEquals(KeeperCrewLines.THANKS, f.talk("t2"));
        assertNull(f.quest().currentStep());
        assertEquals(KeeperCrewLines.DONE, f.talk("t3"));
    }
}
