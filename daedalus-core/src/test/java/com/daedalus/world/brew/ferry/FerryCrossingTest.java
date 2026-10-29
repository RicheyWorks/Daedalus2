// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.ferry;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.ferry.FerryCrossing.Outcome;
import org.junit.jupiter.api.Test;

class FerryCrossingTest {
    /** Brute force over every simple path from isle 0 to the last isle. */
    static int brute(FerryCrossing f) {
        int[] best = {-1};
        walk(f, 0, 1, 0, best);
        return best[0];
    }

    private static void walk(FerryCrossing f, int at, int seen, int paid, int[] best) {
        if (at == f.isles() - 1) {
            if (best[0] < 0 || paid < best[0]) {
                best[0] = paid;
            }
            return;
        }
        for (int v = 0; v < f.isles(); v++) {
            if ((seen >> v & 1) == 0 && f.fare(at, v) != FerryCrossing.NONE) {
                walk(f, v, seen | 1 << v, paid + f.fare(at, v), best);
            }
        }
    }

    static int[][] line4() {
        int[][] f = new int[4][4];
        set(f, 0, 1, 1);
        set(f, 1, 2, 1);
        set(f, 2, 3, 1);
        set(f, 0, 3, 9);
        return f;
    }

    static void set(int[][] f, int a, int b, int v) {
        f[a][b] = v;
        f[b][a] = v;
    }

    @Test
    void seededHarbourIsDeterministic() {
        FerryCrossing f = FerryCrossing.seeded(4);
        assertTrue(f.isles() >= 4 && f.isles() <= 7);
        assertEquals(f.cheapest(), FerryCrossing.seeded(4).cheapest());
        assertThrows(IllegalArgumentException.class, () -> new FerryCrossing(new int[][] {{0, 1}, {2, 0}}));
    }

    @Test
    void cheapestMatchesBruteForce() {
        int routed = 0;
        for (long seed = 0; seed < 30; seed++) {
            FerryCrossing f = FerryCrossing.seeded(seed);
            assertEquals(brute(f), f.cheapest(), "Dijkstra == brute force, seed " + seed);
            if (f.cheapest() >= 0) {
                routed++;
            }
        }
        assertTrue(routed > 20, "most seeded harbours have a route");
    }

    @Test
    void directFerryIsNotAlwaysCheapest() {
        assertEquals(3, new FerryCrossing(line4()).cheapest());
    }

    @Test
    void noRouteEarnsNoCredit() {
        int[][] f = new int[4][4];
        set(f, 0, 1, 2);
        set(f, 1, 2, 2);
        FerryCrossing c = new FerryCrossing(f);
        assertEquals(-1, c.cheapest());
        c.sail("s1", 1);
        assertEquals(Outcome.NO_ROUTE, c.dock("d1"));
        assertEquals(KeeperFerryLines.NO_ROUTE, c.talk("t1"));
        assertEquals("dock", c.quest().currentStep().type(), "no credit without a route");
    }

    @Test
    void guards() {
        FerryCrossing c = new FerryCrossing(line4());
        assertEquals(Outcome.IGNORED, c.sail(" ", 1));
        assertEquals(Outcome.NO_FERRY, c.sail("e0", 2));
        assertEquals(Outcome.NO_FERRY, c.sail("e0", 9));
        assertEquals(Outcome.NOT_HOME, c.dock("d0"));
        assertEquals(Outcome.SAILED, c.sail("e1", 1));
        assertEquals(Outcome.DUPLICATE, c.sail("e1", 2));
    }

    @Test
    void questDearThenWellThenKeeper() {
        FerryCrossing c = new FerryCrossing(line4());
        assertEquals(String.format(KeeperFerryLines.GREETING, 0, 3), c.talk("t0"));
        c.sail("a1", 3);
        assertEquals(Outcome.DEAR, c.dock("d1"));
        assertEquals(String.format(KeeperFerryLines.DEAR, 9, 3), c.talk("t1"));
        assertEquals("dock", c.quest().currentStep().type(), "no credit for a dear crossing");
        c.restart();
        c.sail("b1", 1);
        assertEquals("Isle 1 now, 1 shells paid.", KeeperFerryLines.line(c));
        c.sail("b2", 2);
        c.sail("b3", 3);
        assertEquals(Outcome.WELL, c.dock("d2"));
        assertEquals(KeeperFerryLines.THANKS, c.talk("t2"));
        assertNull(c.quest().currentStep());
        assertEquals(KeeperFerryLines.DONE, c.talk("t3"));
    }
}
