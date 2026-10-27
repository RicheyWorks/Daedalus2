// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.beacons;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.beacons.BeaconFence.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class BeaconFenceTest {
    /** Brute force: a post is a corner unless it lies in a triangle or on a segment of other posts. */
    static int brute(BeaconFence f) {
        List<List<Integer>> ps = f.posts();
        int n = ps.size();
        int corners = 0;
        for (int i = 0; i < n; i++) {
            boolean inside = false;
            for (int a = 0; a < n && !inside; a++) {
                for (int b = 0; b < n && !inside; b++) {
                    for (int c = 0; c < n && !inside; c++) {
                        if (a != i && b != i && c != i) {
                            inside = inTriangle(ps.get(i), ps.get(a), ps.get(b), ps.get(c));
                        }
                    }
                }
            }
            corners += inside ? 0 : 1;
        }
        return corners < 3 ? 0 : corners;
    }

    /** Closed triangle test (a repeated vertex makes it a segment). */
    static boolean inTriangle(List<Integer> p, List<Integer> a, List<Integer> b, List<Integer> c) {
        long d1 = BeaconFence.cross(a, b, p);
        long d2 = BeaconFence.cross(b, c, p);
        long d3 = BeaconFence.cross(c, a, p);
        boolean neg = d1 < 0 || d2 < 0 || d3 < 0;
        boolean pos = d1 > 0 || d2 > 0 || d3 > 0;
        if (neg && pos) {
            return false;
        }
        int minX = Math.min(a.get(0), Math.min(b.get(0), c.get(0)));
        int maxX = Math.max(a.get(0), Math.max(b.get(0), c.get(0)));
        int minY = Math.min(a.get(1), Math.min(b.get(1), c.get(1)));
        int maxY = Math.max(a.get(1), Math.max(b.get(1), c.get(1)));
        return p.get(0) >= minX && p.get(0) <= maxX && p.get(1) >= minY && p.get(1) <= maxY;
    }

    /** Square corners plus a centre post and an edge post: 4 corners, 6 posts. */
    static BeaconFence fixture() {
        return new BeaconFence(List.of(List.of(0, 0), List.of(4, 0), List.of(4, 4), List.of(0, 4), List.of(2, 2), List.of(2, 0)));
    }

    @Test
    void seededIsDeterministic() {
        assertEquals(BeaconFence.seeded(1).posts(), BeaconFence.seeded(1).posts());
        assertEquals(BeaconFence.seeded(1).corners(), BeaconFence.seeded(1).corners());
        assertThrows(IllegalArgumentException.class, () -> new BeaconFence(List.of()));
        assertThrows(IllegalArgumentException.class, () -> new BeaconFence(List.of(List.of(1, 1), List.of(1, 1))));
    }

    @Test
    void answerMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            BeaconFence r = BeaconFence.seeded(seed);
            assertEquals(brute(r), r.corners(), "fast == brute force, seed " + seed);
            assertTrue(r.all() >= r.corners(), "never more corners than posts, seed " + seed);
        }
    }

    @Test
    void trap() {
        BeaconFence r = fixture();
        assertEquals(4, r.corners());
        assertEquals(6, r.all());
        assertEquals(Outcome.WRONG, r.count("c0", 6), "inside and edge posts don't bend the rope");
        assertEquals(String.format(KeeperBeaconFence.WRONG, 6), r.talk("t0"));
    }

    @Test
    void wrongAndSpecialEarnNoCredit() {
        BeaconFence r = fixture();
        r.read("r");
        assertEquals(Outcome.WRONG, r.count("c1", 4 + 1));
        assertEquals(Outcome.MALFORMED, r.count("c2", -1));
        assertEquals("count", r.quest().currentStep().type(), "no credit for a wrong answer");
        BeaconFence sp = new BeaconFence(List.of(List.of(0, 0), List.of(1, 1), List.of(2, 2)));
        assertTrue(sp.flat());
        assertEquals(Outcome.FLAT, sp.count("x", 0));
        assertEquals(KeeperBeaconFence.FLAT, sp.talk("tx"));
    }

    @Test
    void guards() {
        BeaconFence r = fixture();
        assertEquals(Outcome.IGNORED, r.count("", 4));
        assertEquals(Outcome.IGNORED, r.count(null, 4));
        assertEquals(Outcome.RIGHT, r.count("e1", 4));
        assertEquals(Outcome.DUPLICATE, r.count("e1", 4));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        BeaconFence r = fixture();
        assertEquals(String.format(KeeperBeaconFence.GREETING, fixture().posts()), r.talk("t0"));
        r.read("r0");
        assertEquals(Outcome.WRONG, r.count("c1", 6));
        assertEquals(Outcome.RIGHT, r.count("c2", 4));
        assertEquals(KeeperBeaconFence.THANKS, r.talk("t2"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperBeaconFence.DONE, r.talk("t3"));
    }
}
