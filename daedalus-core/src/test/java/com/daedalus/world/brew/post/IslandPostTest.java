// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.post;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.post.IslandPost.Outcome;
import org.junit.jupiter.api.Test;

class IslandPostTest {
    /** Brute force over every order of the other isles. */
    static int brute(IslandPost p) {
        int[] best = {Integer.MAX_VALUE};
        perm(p, 0, 1, 0, best);
        return best[0];
    }

    private static void perm(IslandPost p, int at, int seen, int rowed, int[] best) {
        if (seen == (1 << p.isles()) - 1) {
            best[0] = Math.min(best[0], rowed + p.dist(at, 0));
            return;
        }
        for (int v = 1; v < p.isles(); v++) {
            if ((seen >> v & 1) == 0) {
                perm(p, v, seen | 1 << v, rowed + p.dist(at, v), best);
            }
        }
    }

    /** Square 0-1-2-3 with sides 1; diagonals 0-2 = 1 is near but 1-3 = 9. */
    static IslandPost square() {
        return new IslandPost(new int[][] {
            {0, 1, 1, 1},
            {1, 0, 1, 9},
            {1, 1, 0, 1},
            {1, 9, 1, 0}});
    }

    @Test
    void seededSeaIsDeterministic() {
        IslandPost p = IslandPost.seeded(7);
        assertTrue(p.isles() >= 4 && p.isles() <= 7);
        assertEquals(p.shortest(), IslandPost.seeded(7).shortest());
        assertThrows(IllegalArgumentException.class, () -> new IslandPost(new int[][] {{0, 1}, {2, 0}}));
    }

    @Test
    void shortestMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            IslandPost p = IslandPost.seeded(seed);
            assertEquals(brute(p), p.shortest(), "Held-Karp == brute force, seed " + seed);
        }
    }

    @Test
    void nearestFirstIsNotAlwaysShortest() {
        IslandPost p = square();
        assertEquals(4, p.shortest());
        // going to the near diagonal isle 2 first forces the 1-3 crossing: 1+1+9+1 = 12.
        p.call("a", 2);
        p.call("b", 1);
        p.call("c", 3);
        assertEquals(Outcome.LONG, p.home("h"));
        assertEquals(12, p.rowed());
    }

    @Test
    void missedIslesEarnNoCredit() {
        IslandPost p = square();
        p.call("a", 1);
        p.call("a2", 2);
        assertEquals(Outcome.MISSED, p.home("h1"));
        p.restart();
        p.call("b", 1);
        assertEquals(Outcome.MISSED, p.home("h2"));
        assertEquals(String.format(KeeperPostLines.MISSED, 2), p.talk("t1"));
        assertEquals("home", p.quest().currentStep().type(), "no credit for missed isles");
    }

    @Test
    void guards() {
        IslandPost p = square();
        assertEquals(Outcome.IGNORED, p.call("", 1));
        assertEquals(Outcome.NOT_THERE, p.call("e0", 4));
        assertEquals(Outcome.ALREADY, p.call("e0", 0));
        assertEquals(Outcome.CALLED, p.call("e1", 1));
        assertEquals(Outcome.DUPLICATE, p.call("e1", 2));
        assertEquals(Outcome.ALREADY, p.call("e2", 1));
    }

    @Test
    void questLongThenWellThenKeeper() {
        IslandPost p = square();
        assertEquals(String.format(KeeperPostLines.GREETING, 4), p.talk("t0"));
        p.call("a1", 2);
        assertEquals("2 isles called at, 1 leagues rowed.", KeeperPostLines.line(p));
        p.call("a2", 1);
        p.call("a3", 3);
        assertEquals(Outcome.LONG, p.home("h1"));
        assertEquals(String.format(KeeperPostLines.LONG, 12, 4), p.talk("t1"));
        assertEquals("home", p.quest().currentStep().type(), "no credit for a long round");
        p.restart();
        p.call("b1", 1);
        p.call("b2", 2);
        p.call("b3", 3);
        assertEquals(Outcome.WELL, p.home("h2"));
        assertEquals(KeeperPostLines.THANKS, p.talk("t2"));
        assertNull(p.quest().currentStep());
        assertEquals(KeeperPostLines.DONE, p.talk("t3"));
    }
}
