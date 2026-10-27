// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.splice;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.splice.RopeSplicing.Outcome;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class RopeSplicingTest {
    /** Brute force: the work of every full bracketing of ropes a..b, as a list. */
    static List<Long> all(List<Integer> e, int a, int b) {
        List<Long> out = new ArrayList<>();
        if (b - a == 1) {
            out.add(0L);
            return out;
        }
        for (int k = a + 1; k < b; k++) {
            for (long l : all(e, a, k)) {
                for (long r : all(e, k, b)) {
                    out.add(l + r + (long) e.get(a) * e.get(k) * e.get(b));
                }
            }
        }
        return out;
    }

    /** Ends 10, 30, 5, 60: (r0 r1) r2 is 1500 + 3000 = 4500; r0 (r1 r2) is 9000 + 18000 = 27000. */
    static RopeSplicing walk() {
        return new RopeSplicing(List.of(10, 30, 5, 60));
    }

    @Test
    void seededWalkIsDeterministic() {
        assertEquals(RopeSplicing.seeded(8).ends(), RopeSplicing.seeded(8).ends());
        assertThrows(IllegalArgumentException.class, () -> new RopeSplicing(List.of(3)));
        assertThrows(IllegalArgumentException.class, () -> new RopeSplicing(List.of(3, 0)));
    }

    @Test
    void leastMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            RopeSplicing r = RopeSplicing.seeded(seed);
            List<Long> every = all(r.ends(), 0, r.ropes());
            assertEquals(every.stream().mapToLong(Long::longValue).min().getAsLong(), r.least(),
                    "interval DP == brute force over every bracketing, seed " + seed);
        }
        assertEquals(0, new RopeSplicing(List.of(4, 7)).least(), "one rope needs no splice");
    }

    @Test
    void orderMatters() {
        RopeSplicing r = walk();
        assertEquals(4500, r.least());
        assertEquals(4500, r.leftToRight());
        RopeSplicing other = new RopeSplicing(List.of(40, 20, 30, 10, 30));
        assertEquals(26000, other.least());
        assertEquals(48000, other.leftToRight(), "left to right is not always least");
    }

    @Test
    void heavyEarnsNoCredit() {
        RopeSplicing r = walk();
        r.lay("l");
        assertEquals(Outcome.HEAVY, r.name("n0", 27000));
        assertEquals(String.format(KeeperSpliceLines.HEAVY, 27000, 4500), r.talk("t0"));
        assertEquals("name", r.quest().currentStep().type(), "no credit for a heavy answer");
    }

    @Test
    void guards() {
        RopeSplicing r = walk();
        assertEquals(Outcome.IGNORED, r.name("", 4500));
        assertEquals(Outcome.IGNORED, r.name("e0", -1));
        assertEquals(Outcome.LEAST, r.name("e1", 4500));
        assertEquals(Outcome.DUPLICATE, r.name("e1", 4500));
    }

    @Test
    void questHeavyThenLeastThenKeeper() {
        RopeSplicing r = walk();
        assertEquals(String.format(KeeperSpliceLines.GREETING, 3), r.talk("t0"));
        r.lay("l0");
        assertEquals(Outcome.HEAVY, r.name("n1", 27000));
        assertEquals(Outcome.LEAST, r.name("n2", 4500));
        assertEquals(KeeperSpliceLines.THANKS, r.talk("t2"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperSpliceLines.DONE, r.talk("t3"));
    }
}
