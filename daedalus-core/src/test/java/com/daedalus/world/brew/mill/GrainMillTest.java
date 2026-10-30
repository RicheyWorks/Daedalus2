// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.mill;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.mill.GrainMill.Outcome;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class GrainMillTest {
    /** Brute force over every order of grinding pairs. */
    static int brute(List<Integer> s) {
        if (s.size() == 1) {
            return 0;
        }
        int best = Integer.MAX_VALUE;
        for (int i = 0; i < s.size(); i++) {
            for (int j = i + 1; j < s.size(); j++) {
                List<Integer> n = new ArrayList<>(s);
                int m = n.get(i) + n.get(j);
                n.remove(j);
                n.remove(i);
                n.add(m);
                best = Math.min(best, m + brute(n));
            }
        }
        return best;
    }

    @Test
    void seededStoreIsDeterministic() {
        GrainMill m = GrainMill.seeded(3);
        assertTrue(m.sacks().size() >= 2 && m.sacks().size() <= 7);
        assertEquals(m.sacks(), GrainMill.seeded(3).sacks());
        assertThrows(IllegalArgumentException.class, () -> new GrainMill(4));
    }

    @Test
    void leastMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            GrainMill m = GrainMill.seeded(seed);
            assertEquals(brute(m.sacks()), m.least(), "Huffman == brute force, seed " + seed);
        }
    }

    @Test
    void grindingTheHeavySackEarlyCostsMore() {
        GrainMill m = new GrainMill(1, 2, 3, 10);
        assertEquals(25, m.least(), "1+2=3, 3+3=6, 6+10=16");
        m.grind("a", 2, 3);
        m.grind("b", 1, 2);
        m.grind("c", 0, 1);
        assertEquals(44, m.work(), "3+10=13, 2+13=15, 1+15=16: 44 work");
    }

    @Test
    void heavyEarnsNoCredit() {
        GrainMill m = new GrainMill(1, 2, 3, 10);
        assertEquals(Outcome.UNFINISHED, m.sack("s0"));
        m.grind("a", 2, 3);
        m.grind("b", 1, 2);
        m.grind("c", 0, 1);
        assertEquals(Outcome.HEAVY, m.sack("s1"));
        assertEquals(String.format(KeeperMillLines.HEAVY, 44, 25), m.talk("t1"));
        assertEquals("sack", m.quest().currentStep().type(), "no credit for heavy work");
    }

    @Test
    void guards() {
        GrainMill m = new GrainMill(1, 2, 3);
        assertEquals(Outcome.IGNORED, m.grind("", 0, 1));
        assertEquals(Outcome.NOT_THERE, m.grind("e0", 0, 0));
        assertEquals(Outcome.NOT_THERE, m.grind("e0", 0, 3));
        assertEquals(Outcome.GROUND, m.grind("e1", 0, 1));
        assertEquals(Outcome.DUPLICATE, m.grind("e1", 0, 1));
    }

    @Test
    void questHeavyThenWellThenKeeper() {
        GrainMill m = new GrainMill(1, 2, 3, 10);
        assertEquals(String.format(KeeperMillLines.GREETING, 4), m.talk("t0"));
        m.grind("a", 2, 3);
        m.grind("b", 1, 2);
        m.grind("c", 0, 1);
        assertEquals(Outcome.HEAVY, m.sack("s1"));
        m.restart();
        m.grind("d", 0, 1);
        assertEquals("3 sacks left, 3 work so far.", KeeperMillLines.line(m));
        m.grind("e", 0, 2);
        m.grind("f", 0, 1);
        assertEquals(25, m.work());
        assertEquals(Outcome.WELL, m.sack("s2"));
        assertEquals(KeeperMillLines.THANKS, m.talk("t2"));
        assertNull(m.quest().currentStep());
        assertEquals(KeeperMillLines.DONE, m.talk("t3"));
    }
}
