// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.baskets;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.baskets.TwinBaskets.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class TwinBasketsTest {
    /** Brute force: every pair i < j. */
    static int brute(TwinBaskets t) {
        List<Integer> b = t.baskets();
        int n = 0;
        for (int i = 0; i < b.size(); i++) {
            for (int j = i + 1; j < b.size(); j++) {
                if (b.get(i) + b.get(j) == t.load()) {
                    n++;
                }
            }
        }
        return n;
    }

    /** Brute force for ordered pairs: every i != j. */
    static int both(TwinBaskets t) {
        List<Integer> b = t.baskets();
        int n = 0;
        for (int i = 0; i < b.size(); i++) {
            for (int j = 0; j < b.size(); j++) {
                if (i != j && b.get(i) + b.get(j) == t.load()) {
                    n++;
                }
            }
        }
        return n;
    }

    /** Baskets 1 2 3 4 3, load 6: pairs 2+4 and 3+3, four if counted both ways. */
    static TwinBaskets fixture() {
        return new TwinBaskets(List.of(1, 2, 3, 4, 3), 6);
    }

    @Test
    void seededIsDeterministic() {
        assertEquals(TwinBaskets.seeded(1).baskets(), TwinBaskets.seeded(1).baskets());
        assertEquals(TwinBaskets.seeded(1).pairs(), TwinBaskets.seeded(1).pairs());
        assertThrows(IllegalArgumentException.class, () -> new TwinBaskets(List.of(1), 0));
        assertThrows(IllegalArgumentException.class, () -> new TwinBaskets(List.of(0), 2));
    }

    @Test
    void answerMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            TwinBaskets r = TwinBaskets.seeded(seed);
            assertEquals(brute(r), r.pairs(), "fast == brute force, seed " + seed);
            assertEquals(both(r), r.ordered(), "ordered, seed " + seed);
        }
    }

    @Test
    void trap() {
        TwinBaskets r = fixture();
        assertEquals(2, r.pairs());
        assertEquals(4, r.ordered());
        assertEquals(Outcome.WRONG, r.count("c0", 4), "counting both ways counts each pair twice");
        assertEquals(String.format(KeeperTwinBaskets.WRONG, 4), r.talk("t0"));
    }

    @Test
    void wrongAndSpecialEarnNoCredit() {
        TwinBaskets r = fixture();
        r.read("r");
        assertEquals(Outcome.WRONG, r.count("c1", 2 + 1));
        assertEquals(Outcome.MALFORMED, r.count("c2", -1));
        assertEquals("count", r.quest().currentStep().type(), "no credit for a wrong answer");
        TwinBaskets sp = new TwinBaskets(List.of(5), 10);
        assertTrue(sp.few());
        assertEquals(Outcome.FEW, sp.count("x", 0));
        assertEquals(KeeperTwinBaskets.FEW, sp.talk("tx"));
    }

    @Test
    void guards() {
        TwinBaskets r = fixture();
        assertEquals(Outcome.IGNORED, r.count("", 2));
        assertEquals(Outcome.IGNORED, r.count(null, 2));
        assertEquals(Outcome.RIGHT, r.count("e1", 2));
        assertEquals(Outcome.DUPLICATE, r.count("e1", 2));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        TwinBaskets r = fixture();
        assertEquals(String.format(KeeperTwinBaskets.GREETING, List.of(1, 2, 3, 4, 3), 6), r.talk("t0"));
        r.read("r0");
        assertEquals(Outcome.WRONG, r.count("c1", 4));
        assertEquals(Outcome.RIGHT, r.count("c2", 2));
        assertEquals(KeeperTwinBaskets.THANKS, r.talk("t2"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperTwinBaskets.DONE, r.talk("t3"));
    }
}
