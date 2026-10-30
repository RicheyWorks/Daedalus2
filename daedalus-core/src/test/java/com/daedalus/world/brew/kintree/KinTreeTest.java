// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.kintree;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.kintree.KinTree.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class KinTreeTest {
    /** Brute force: breadth-first search on the tree as an undirected graph. */
    static int brute(KinTree t) {
        int n = t.parents().size();
        int[] dist = new int[n];
        java.util.Arrays.fill(dist, -1);
        java.util.ArrayDeque<Integer> q = new java.util.ArrayDeque<>();
        dist[t.a()] = 0;
        q.add(t.a());
        while (!q.isEmpty()) {
            int u = q.poll();
            for (int v = 0; v < n; v++) {
                boolean edge = v > 0 && t.parents().get(v) == u || u > 0 && t.parents().get(u) == v;
                if (edge && dist[v] < 0) {
                    dist[v] = dist[u] + 1;
                    q.add(v);
                }
            }
        }
        return dist[t.b()];
    }

    /** Parents -1 0 0 1 1 2, islanders 3 and 4: siblings 2 steps apart, 4 via the founder. */
    static KinTree fixture() {
        return new KinTree(List.of(-1, 0, 0, 1, 1, 2), 3, 4);
    }

    @Test
    void seededIsDeterministic() {
        assertEquals(KinTree.seeded(1).parents(), KinTree.seeded(1).parents());
        assertEquals(KinTree.seeded(1).steps(), KinTree.seeded(1).steps());
        assertThrows(IllegalArgumentException.class, () -> new KinTree(List.of(0), 0, 0));
        assertThrows(IllegalArgumentException.class, () -> new KinTree(List.of(-1, 1), 0, 1));
    }

    @Test
    void answerMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            KinTree r = KinTree.seeded(seed);
            assertEquals(brute(r), r.steps(), "fast == brute force, seed " + seed);
            assertTrue(r.viaFounder() >= r.steps(), "via the founder is never shorter, seed " + seed);
        }
    }

    @Test
    void trap() {
        KinTree r = fixture();
        assertEquals(2, r.steps());
        assertEquals(4, r.viaFounder());
        assertEquals(Outcome.WRONG, r.count("c0", 4), "climb only to the nearest shared ancestor");
        assertEquals(String.format(KeeperKinTree.WRONG, 4), r.talk("t0"));
    }

    @Test
    void wrongAndSpecialEarnNoCredit() {
        KinTree r = fixture();
        r.read("r");
        assertEquals(Outcome.WRONG, r.count("c1", 2 + 1));
        assertEquals(Outcome.MALFORMED, r.count("c2", -1));
        assertEquals("count", r.quest().currentStep().type(), "no credit for a wrong answer");
        KinTree sp = new KinTree(List.of(-1, 0, 0), 2, 2);
        assertTrue(sp.same());
        assertEquals(Outcome.SAME, sp.count("x", 0));
        assertEquals(KeeperKinTree.SAME, sp.talk("tx"));
    }

    @Test
    void guards() {
        KinTree r = fixture();
        assertEquals(Outcome.IGNORED, r.count("", 2));
        assertEquals(Outcome.IGNORED, r.count(null, 2));
        assertEquals(Outcome.RIGHT, r.count("e1", 2));
        assertEquals(Outcome.DUPLICATE, r.count("e1", 2));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        KinTree r = fixture();
        assertEquals(String.format(KeeperKinTree.GREETING, List.of(-1, 0, 0, 1, 1, 2), 3, 4), r.talk("t0"));
        r.read("r0");
        assertEquals(Outcome.WRONG, r.count("c1", 4));
        assertEquals(Outcome.RIGHT, r.count("c2", 2));
        assertEquals(KeeperKinTree.THANKS, r.talk("t2"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperKinTree.DONE, r.talk("t3"));
    }
}
