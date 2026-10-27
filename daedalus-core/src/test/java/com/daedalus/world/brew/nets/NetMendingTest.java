// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.nets;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.nets.NetMending.Outcome;
import org.junit.jupiter.api.Test;

class NetMendingTest {
    /** Brute force: every mender tries every net or none, nets used once. */
    static int brute(NetMending n) {
        return go(n, 0, new boolean[n.nets()]);
    }

    private static int go(NetMending n, int m, boolean[] used) {
        if (m == n.menders()) {
            return 0;
        }
        int best = go(n, m + 1, used);
        for (int j = 0; j < n.nets(); j++) {
            if (n.knows(m, j) && !used[j]) {
                used[j] = true;
                best = Math.max(best, 1 + go(n, m + 1, used));
                used[j] = false;
            }
        }
        return best;
    }

    static NetMending trap() {
        return new NetMending(new boolean[][] {{true, true}, {true, false}});
    }

    @Test
    void seededLoftIsDeterministic() {
        NetMending n = NetMending.seeded(2);
        assertTrue(n.menders() >= 2 && n.menders() <= 5 && n.nets() >= 2 && n.nets() <= 5);
        assertEquals(n.most(), NetMending.seeded(2).most());
        assertThrows(IllegalArgumentException.class, () -> new NetMending(new boolean[][] {{true}, {}}));
    }

    @Test
    void mostMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            NetMending n = NetMending.seeded(seed);
            assertEquals(brute(n), n.most(), "Kuhn == brute force, seed " + seed);
        }
    }

    @Test
    void firstChoiceIsNotAlwaysBest() {
        assertEquals(2, trap().most());
    }

    @Test
    void fewEarnsNoCredit() {
        NetMending n = trap();
        assertEquals(Outcome.CANT_KNOT, n.assign("a0", 1, 1));
        n.assign("a1", 0, 0);
        assertEquals(Outcome.FEW, n.mend("m1"));
        assertEquals(String.format(KeeperNetLines.FEW, 1, 2), n.talk("t1"));
        assertEquals("mend", n.quest().currentStep().type(), "no credit for too few");
    }

    @Test
    void guards() {
        NetMending n = trap();
        assertEquals(Outcome.IGNORED, n.assign("", 0, 0));
        assertEquals(Outcome.NOT_THERE, n.assign("e0", 2, 0));
        assertEquals(Outcome.NOT_THERE, n.assign("e0", 0, 2));
        assertEquals(Outcome.ASSIGNED, n.assign("e1", 0, 0));
        assertEquals(Outcome.TAKEN, n.assign("e2", 1, 0));
        assertEquals(Outcome.DUPLICATE, n.assign("e1", 0, 1));
    }

    @Test
    void questFewThenWellThenKeeper() {
        NetMending n = trap();
        assertEquals(String.format(KeeperNetLines.GREETING, 2, 2), n.talk("t0"));
        n.assign("a1", 0, 0);
        assertEquals(Outcome.FEW, n.mend("m1"));
        n.assign("a2", 0, 1);
        n.assign("a3", 1, 0);
        assertEquals(Outcome.WELL, n.mend("m2"));
        assertEquals(KeeperNetLines.THANKS, n.talk("t2"));
        assertNull(n.quest().currentStep());
        assertEquals(KeeperNetLines.DONE, n.talk("t3"));
    }
}
