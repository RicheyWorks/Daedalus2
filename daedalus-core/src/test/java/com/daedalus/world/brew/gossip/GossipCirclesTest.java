// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.gossip;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.gossip.GossipCircles.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class GossipCirclesTest {
    /** Brute force: group islanders who reach each other both ways; count groups of two or more. */
    static int brute(GossipCircles g) {
        int n = g.islanders();
        boolean[] done = new boolean[n];
        int c = 0;
        for (int a = 0; a < n; a++) {
            if (done[a]) {
                continue;
            }
            int size = 0;
            for (int b = 0; b < n; b++) {
                if (g.reaches(a, b) && g.reaches(b, a)) {
                    done[b] = true;
                    size++;
                    assertEquals(true, g.sameCircle(a, b));
                }
            }
            c += size >= 2 ? 1 : 0;
        }
        return c;
    }

    /** 0->1->2->0 (a circle), 2->3, 3->4->3 (a circle), 4->5. Two circles, though five tellings point onward. */
    static GossipCircles village() {
        return new GossipCircles(6, List.of(new int[] {0, 1}, new int[] {1, 2}, new int[] {2, 0}, new int[] {2, 3},
                new int[] {3, 4}, new int[] {4, 3}, new int[] {4, 5}));
    }

    @Test
    void seededVillageIsDeterministic() {
        assertEquals(GossipCircles.seeded(1).circles(), GossipCircles.seeded(1).circles());
        assertEquals(GossipCircles.seeded(1).islanders(), GossipCircles.seeded(1).islanders());
        assertThrows(IllegalArgumentException.class, () -> new GossipCircles(0, List.of()));
        assertThrows(IllegalArgumentException.class, () -> new GossipCircles(2, List.of(new int[] {1, 1})));
    }

    @Test
    void circlesMatchBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            GossipCircles g = GossipCircles.seeded(seed);
            assertEquals(brute(g), g.circles(), "Kosaraju == brute force, seed " + seed);
        }
    }

    @Test
    void oneBigChainIsATrap() {
        GossipCircles g = village();
        assertEquals(2, g.circles());
        assertEquals(Outcome.WRONG, g.count("c0", 1), "news from 0 reaches 5, but not back");
        assertEquals(String.format(KeeperGossip.WRONG, 1), g.talk("t0"));
    }

    @Test
    void wrongAndLoneEarnNoCredit() {
        GossipCircles g = village();
        g.listen("l");
        assertEquals(Outcome.WRONG, g.count("c1", 3));
        assertEquals(Outcome.MALFORMED, g.count("c2", -1));
        assertEquals("count", g.quest().currentStep().type(), "no credit for a wrong count");
        GossipCircles line = new GossipCircles(3, List.of(new int[] {0, 1}, new int[] {1, 2}));
        assertEquals(0, line.circles());
        assertEquals(Outcome.LONE, line.count("x", 0));
        assertEquals(KeeperGossip.LONE, line.talk("tx"));
    }

    @Test
    void guards() {
        GossipCircles g = village();
        assertEquals(Outcome.IGNORED, g.count("", 2));
        assertEquals(Outcome.IGNORED, g.count(null, 2));
        assertEquals(Outcome.RIGHT, g.count("e1", 2));
        assertEquals(Outcome.DUPLICATE, g.count("e1", 2));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        GossipCircles g = village();
        assertEquals(String.format(KeeperGossip.GREETING, 6), g.talk("t0"));
        g.listen("l0");
        assertEquals(Outcome.WRONG, g.count("c1", 1));
        assertEquals(Outcome.RIGHT, g.count("c2", 2));
        assertEquals(KeeperGossip.THANKS, g.talk("t2"));
        assertNull(g.quest().currentStep());
        assertEquals(KeeperGossip.DONE, g.talk("t3"));
    }
}
