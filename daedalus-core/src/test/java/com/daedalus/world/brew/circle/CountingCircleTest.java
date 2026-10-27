// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.circle;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.circle.CountingCircle.Outcome;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class CountingCircleTest {
    /** Brute force: play the game out. */
    static int brute(int n, int k) {
        List<Integer> ring = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            ring.add(i);
        }
        int at = 0;
        while (ring.size() > 1) {
            at = (at + k - 1) % ring.size();
            ring.remove(at);
        }
        return ring.get(0);
    }

    /** 5 children, every 2nd out: 1, 3, 0, 4 step out and child 2 is left. */
    static CountingCircle fire() {
        return new CountingCircle(5, 2);
    }

    @Test
    void seededCircleIsDeterministic() {
        assertEquals(CountingCircle.seeded(6).children(), CountingCircle.seeded(6).children());
        assertEquals(CountingCircle.seeded(6).step(), CountingCircle.seeded(6).step());
        assertThrows(IllegalArgumentException.class, () -> new CountingCircle(0, 2));
        assertThrows(IllegalArgumentException.class, () -> new CountingCircle(3, 0));
    }

    @Test
    void survivorMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            CountingCircle c = CountingCircle.seeded(seed);
            assertEquals(brute(c.children(), c.step()), c.survivor(), "Josephus == simulation, seed " + seed);
        }
    }

    @Test
    void firstOutIsNotLast() {
        CountingCircle c = fire();
        assertEquals(2, c.survivor());
        assertEquals(0, new CountingCircle(5, 1).survivor() - 4, "count of 1 leaves the last child");
        assertEquals(Outcome.OUT, c.name("n0", 4));
        assertEquals(String.format(KeeperCircleLines.OUT, 4, 2), c.talk("t0"));
    }

    @Test
    void outEarnsNoCredit() {
        CountingCircle c = fire();
        c.gather("g");
        assertEquals(Outcome.OUT, c.name("n1", 0));
        assertEquals("name", c.quest().currentStep().type(), "no credit for a child who steps out");
    }

    @Test
    void guards() {
        CountingCircle c = fire();
        assertEquals(Outcome.IGNORED, c.name("", 2));
        assertEquals(Outcome.NOT_THERE, c.name("e0", 5));
        assertEquals(Outcome.LAST, c.name("e1", 2));
        assertEquals(Outcome.DUPLICATE, c.name("e1", 2));
    }

    @Test
    void questOutThenLastThenKeeper() {
        CountingCircle c = fire();
        assertEquals(String.format(KeeperCircleLines.GREETING, 5, 2, "nd"), c.talk("t0"));
        c.gather("g0");
        assertEquals(Outcome.OUT, c.name("n1", 4));
        assertEquals(Outcome.LAST, c.name("n2", 2));
        assertEquals(String.format(KeeperCircleLines.THANKS, 2), c.talk("t2"));
        assertNull(c.quest().currentStep());
        assertEquals(KeeperCircleLines.DONE, c.talk("t3"));
    }
}
