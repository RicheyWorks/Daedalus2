// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.lamps;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.lamps.LampPosts.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class LampPostsTest {
    /** Brute force: add up every lamp over each post. */
    static int brute(LampPosts l, int post) {
        int sum = 0;
        for (int[] x : l.lamps()) {
            if (x[0] <= post && post <= x[1]) {
                sum += x[2];
            }
        }
        return sum;
    }

    /** Post 1 sits under three faint lamps (3); posts 3-4 under two, one strong (6). */
    static LampPosts fence() {
        return new LampPosts(6, List.of(new int[] {0, 2, 1}, new int[] {1, 2, 1}, new int[] {1, 4, 1},
                new int[] {3, 5, 5}));
    }

    @Test
    void seededFenceIsDeterministic() {
        LampPosts a = LampPosts.seeded(4);
        LampPosts b = LampPosts.seeded(4);
        assertEquals(a.posts(), b.posts());
        assertEquals(a.brightest(), b.brightest());
        assertThrows(IllegalArgumentException.class, () -> new LampPosts(3, List.of(new int[] {2, 3, 1})));
        assertThrows(IllegalArgumentException.class, () -> new LampPosts(0, List.of()));
    }

    @Test
    void lightMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            LampPosts l = LampPosts.seeded(seed);
            int best = 0;
            for (int p = 0; p < l.posts(); p++) {
                assertEquals(brute(l, p), l.light(p), "difference array == brute force, seed " + seed);
                best = Math.max(best, brute(l, p));
            }
            assertEquals(best, l.brightest(), "seed " + seed);
        }
    }

    @Test
    void mostLampsIsNotBrightest() {
        LampPosts l = fence();
        assertEquals(3, l.light(1));
        assertEquals(6, l.brightest());
    }

    @Test
    void dimPostEarnsNoCredit() {
        LampPosts l = fence();
        l.hang("h");
        assertEquals(Outcome.DIM, l.point("p1", 1));
        assertEquals(String.format(KeeperLampLines.DIM, 1, 3, 6), l.talk("t1"));
        assertEquals("point", l.quest().currentStep().type(), "no credit for a dim post");
    }

    @Test
    void guards() {
        LampPosts l = fence();
        assertEquals(Outcome.IGNORED, l.point("", 3));
        assertEquals(Outcome.NOT_THERE, l.point("e0", 6));
        assertEquals(Outcome.BRIGHT, l.point("e1", 4), "either of the tied posts is bright");
        assertEquals(Outcome.DUPLICATE, l.point("e1", 3));
    }

    @Test
    void questDimThenBrightThenKeeper() {
        LampPosts l = fence();
        assertEquals(String.format(KeeperLampLines.GREETING, 6), l.talk("t0"));
        l.hang("h0");
        assertEquals(Outcome.DIM, l.point("p1", 1));
        assertEquals(Outcome.BRIGHT, l.point("p2", 3));
        assertEquals(KeeperLampLines.THANKS, l.talk("t2"));
        assertNull(l.quest().currentStep());
        assertEquals(KeeperLampLines.DONE, l.talk("t3"));
    }
}
