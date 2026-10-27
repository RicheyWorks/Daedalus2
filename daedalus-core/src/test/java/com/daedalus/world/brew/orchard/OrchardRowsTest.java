// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.orchard;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.orchard.OrchardRows.Outcome;
import org.junit.jupiter.api.Test;

class OrchardRowsTest {
    /** Brute force over every subset of trees with no two neighbours. */
    static int brute(OrchardRows o) {
        int best = 0;
        for (int mask = 0; mask < (1 << o.trees()); mask++) {
            if ((mask & (mask >> 1)) != 0) {
                continue;
            }
            int s = 0;
            for (int i = 0; i < o.trees(); i++) {
                if ((mask >> i & 1) == 1) {
                    s += o.apples(i);
                }
            }
            best = Math.max(best, s);
        }
        return best;
    }

    static OrchardRows trap() {
        return new OrchardRows(2, 9, 1, 1, 9);
    }

    @Test
    void seededRowIsDeterministic() {
        OrchardRows o = OrchardRows.seeded(4);
        assertTrue(o.trees() >= 3 && o.trees() <= 14);
        assertEquals(o.most(), OrchardRows.seeded(4).most());
        assertThrows(IllegalArgumentException.class, () -> new OrchardRows(1, -1));
    }

    @Test
    void mostMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            OrchardRows o = OrchardRows.seeded(seed);
            assertEquals(brute(o), o.most(), "take/skip DP == brute force, seed " + seed);
        }
    }

    @Test
    void everyOtherTreeIsNotAlwaysBest() {
        assertEquals(18, trap().most());
    }

    @Test
    void neighboursEarnNoCredit() {
        OrchardRows o = trap();
        o.toggle("a", 0);
        o.toggle("b", 1);
        assertEquals(Outcome.NEIGHBOURS, o.carry("c1"));
        assertArrayEquals(new int[] {0, 1}, o.neighbours());
        assertEquals(String.format(KeeperOrchardLines.NEIGHBOURS, 0, 1), o.talk("t1"));
        assertEquals("carry", o.quest().currentStep().type(), "no credit for bare neighbours");
    }

    @Test
    void guards() {
        OrchardRows o = trap();
        assertEquals(Outcome.IGNORED, o.toggle("", 0));
        assertEquals(Outcome.NOT_THERE, o.toggle("e0", 5));
        assertEquals(Outcome.STRIPPED, o.toggle("e1", 0));
        assertEquals(Outcome.DUPLICATE, o.toggle("e1", 1));
        assertEquals(Outcome.LEFT, o.toggle("e2", 0));
    }

    @Test
    void questLightThenWellThenKeeper() {
        OrchardRows o = trap();
        assertEquals(String.format(KeeperOrchardLines.GREETING, 5), o.talk("t0"));
        o.toggle("a0", 0);
        assertEquals("2 apples in the basket so far.", KeeperOrchardLines.line(o));
        o.toggle("a2", 2);
        o.toggle("a4", 4);
        assertEquals(Outcome.LIGHT, o.carry("c1"));
        assertEquals(String.format(KeeperOrchardLines.LIGHT, 12, 18), o.talk("t1"));
        o.toggle("b0", 0);
        o.toggle("b2", 2);
        o.toggle("b1", 1);
        assertEquals(Outcome.WELL, o.carry("c2"));
        assertEquals(KeeperOrchardLines.THANKS, o.talk("t2"));
        assertNull(o.quest().currentStep());
        assertEquals(KeeperOrchardLines.DONE, o.talk("t3"));
    }
}
