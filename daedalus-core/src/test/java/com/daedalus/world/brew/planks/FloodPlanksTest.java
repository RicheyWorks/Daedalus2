// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.planks;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.planks.FloodPlanks.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class FloodPlanksTest {
    /** Brute force: add every flood plank by plank. */
    static int brute(FloodPlanks p) {
        int[] h = new int[p.planks()];
        for (List<Integer> f : p.floods()) {
            for (int i = f.get(0); i <= f.get(1); i++) {
                h[i] += f.get(2);
            }
        }
        int best = 0;
        for (int x : h) {
            best = Math.max(best, x);
        }
        return best;
    }

    /** 5 planks, floods [0-1 +2], [3-4 +3], [1-3 +1]: highest 4, all floods 6. */
    static FloodPlanks fixture() {
        return new FloodPlanks(5, List.of(List.of(0, 1, 2), List.of(3, 4, 3), List.of(1, 3, 1)));
    }

    @Test
    void seededIsDeterministic() {
        assertEquals(FloodPlanks.seeded(1).floods(), FloodPlanks.seeded(1).floods());
        assertEquals(FloodPlanks.seeded(1).highest(), FloodPlanks.seeded(1).highest());
        assertThrows(IllegalArgumentException.class, () -> new FloodPlanks(0, List.of()));
        assertThrows(IllegalArgumentException.class, () -> new FloodPlanks(2, List.of(List.of(1, 0, 1))));
    }

    @Test
    void answerMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            FloodPlanks r = FloodPlanks.seeded(seed);
            assertEquals(brute(r), r.highest(), "fast == brute force, seed " + seed);
            assertTrue(r.allFloods() >= r.highest(), "all floods never lower, seed " + seed);
        }
    }

    @Test
    void trap() {
        FloodPlanks r = fixture();
        assertEquals(4, r.highest());
        assertEquals(6, r.allFloods());
        assertEquals(Outcome.WRONG, r.count("c0", 6), "floods over different planks don't stack");
        assertEquals(String.format(KeeperFloodPlanks.WRONG, 6), r.talk("t0"));
    }

    @Test
    void wrongAndSpecialEarnNoCredit() {
        FloodPlanks r = fixture();
        r.read("r");
        assertEquals(Outcome.WRONG, r.count("c1", 4 + 1));
        assertEquals(Outcome.MALFORMED, r.count("c2", -1));
        assertEquals("count", r.quest().currentStep().type(), "no credit for a wrong answer");
        FloodPlanks sp = new FloodPlanks(3, List.of());
        assertTrue(sp.calm());
        assertEquals(Outcome.CALM, sp.count("x", 0));
        assertEquals(KeeperFloodPlanks.CALM, sp.talk("tx"));
    }

    @Test
    void guards() {
        FloodPlanks r = fixture();
        assertEquals(Outcome.IGNORED, r.count("", 4));
        assertEquals(Outcome.IGNORED, r.count(null, 4));
        assertEquals(Outcome.RIGHT, r.count("e1", 4));
        assertEquals(Outcome.DUPLICATE, r.count("e1", 4));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        FloodPlanks r = fixture();
        assertEquals(String.format(KeeperFloodPlanks.GREETING, 5, List.of(List.of(0, 1, 2), List.of(3, 4, 3), List.of(1, 3, 1))), r.talk("t0"));
        r.read("r0");
        assertEquals(Outcome.WRONG, r.count("c1", 6));
        assertEquals(Outcome.RIGHT, r.count("c2", 4));
        assertEquals(KeeperFloodPlanks.THANKS, r.talk("t2"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperFloodPlanks.DONE, r.talk("t3"));
    }
}
