// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.casks;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.casks.WaterCasks.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class WaterCasksTest {
    /** Brute force: try every count of every size (each count bounded by measure / size). */
    static int brute(int measure, List<Integer> sizes, int i) {
        if (measure == 0) {
            return 0;
        }
        if (i == sizes.size()) {
            return -1;
        }
        int best = -1;
        int s = sizes.get(i);
        for (int k = 0; k * s <= measure; k++) {
            int rest = brute(measure - k * s, sizes, i + 1);
            if (rest >= 0 && (best < 0 || rest + k < best)) {
                best = rest + k;
            }
        }
        return best;
    }

    @Test
    void seededSpringIsDeterministic() {
        WaterCasks w = WaterCasks.seeded(3);
        assertTrue(w.measure() >= 10 && w.measure() <= 40);
        assertTrue(w.sizes().size() >= 2 && w.sizes().size() <= 4);
        assertEquals(w.sizes(), WaterCasks.seeded(3).sizes());
        assertEquals(w.measure(), WaterCasks.seeded(3).measure());
    }

    @Test
    void fewestMatchesBruteForce() {
        for (long seed = 0; seed < 40; seed++) {
            WaterCasks w = WaterCasks.seeded(seed);
            assertEquals(brute(w.measure(), w.sizes(), 0), w.fewest(), "DP == brute force, seed " + seed);
            if (w.fillable()) {
                assertEquals(w.fewest(), w.bestPour().size(), "walk-back size, seed " + seed);
                assertEquals(w.measure(), w.bestPour().stream().mapToInt(Integer::intValue).sum(), "walk-back sum");
            }
        }
    }

    @Test
    void biggestCaskFirstIsNotAlwaysFewest() {
        // biggest first: 5 + 1 + 1 + 1 = 4 casks; the fewest is 4 + 4 = 2 casks.
        WaterCasks w = new WaterCasks(8, List.of(1, 4, 5));
        assertEquals(2, w.fewest());
        assertEquals(List.of(4, 4), w.bestPour());
    }

    @Test
    void anUnreachableMeasureIsNoFillWithNoCredit() {
        WaterCasks w = new WaterCasks(9, List.of(4, 6));
        assertFalse(w.fillable());
        assertEquals(-1, brute(9, w.sizes(), 0));
        assertEquals(List.of(), w.bestPour());
        w.pour("p1", 4);
        assertEquals(Outcome.NO_FILL, w.seal("s1"));
        assertEquals(String.format(KeeperCaskLines.NO_FILL, 9), KeeperCaskLines.line(w));
        assertEquals("pour", w.quest().currentStep().type(), "no neat-seal credit");
    }

    @Test
    void guards() {
        WaterCasks w = new WaterCasks(6, List.of(2, 3));
        assertEquals(Outcome.IGNORED, w.pour(null, 2));
        assertEquals(Outcome.UNKNOWN, w.pour("e0", 5));
        assertEquals(Outcome.POURED, w.pour("e1", 2));
        assertEquals(Outcome.DUPLICATE, w.pour("e1", 3));
        assertEquals(Outcome.SHORT, w.seal("s0"));
        assertEquals(Outcome.NOT_POURED, w.empty("e2", 3));
        w.pour("e3", 3);
        w.pour("e4", 3);
        assertEquals(Outcome.OVER, w.seal("s1"));
        assertEquals(Outcome.EMPTIED, w.empty("e5", 2));
        assertThrows(IllegalArgumentException.class, () -> new WaterCasks(5, List.of(2, 2)));
        assertThrows(IllegalArgumentException.class, () -> new WaterCasks(0, List.of(2)));
    }

    @Test
    void questWastefulThenNeatThenKeeper() {
        WaterCasks w = new WaterCasks(8, List.of(1, 4, 5));
        assertEquals(String.format(KeeperCaskLines.GREETING, 8), w.talk("t0"));
        w.pour("p1", 5);
        assertEquals("5 of 8 in the tank.", KeeperCaskLines.line(w));
        w.pour("p2", 1);
        w.pour("p3", 1);
        w.pour("p4", 1);
        assertEquals(KeeperCaskLines.READY, w.talk("t1"));
        assertEquals(Outcome.WASTEFUL, w.seal("s1"));
        assertEquals(String.format(KeeperCaskLines.WASTEFUL, 4, 2), w.talk("t2"));
        w.empty("b1", 5);
        w.empty("b2", 1);
        w.empty("b3", 1);
        w.empty("b4", 1);
        w.pour("q1", 4);
        w.pour("q2", 4);
        assertEquals(Outcome.NEAT, w.seal("s2"));
        assertEquals(KeeperCaskLines.THANKS, w.talk("t3"));
        assertNull(w.quest().currentStep());
        assertEquals(KeeperCaskLines.DONE, w.talk("t4"));
    }
}
