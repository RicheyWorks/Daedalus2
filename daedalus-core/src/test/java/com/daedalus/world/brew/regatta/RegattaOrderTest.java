// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.regatta;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.regatta.RegattaOrder.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class RegattaOrderTest {
    /** Brute force: every pair i < j with the earlier finisher numbered higher. */
    static int brute(RegattaOrder r) {
        List<Integer> f = r.finish();
        int n = 0;
        for (int i = 0; i < f.size(); i++) {
            for (int j = i + 1; j < f.size(); j++) {
                n += f.get(i) > f.get(j) ? 1 : 0;
            }
        }
        return n;
    }

    /** Finish 3 1 2: pairs (3,1) and (3,2) swapped, but only one neighbour pair is out of order. */
    static RegattaOrder fixture() {
        return new RegattaOrder(List.of(3, 1, 2));
    }

    @Test
    void seededIsDeterministic() {
        assertEquals(RegattaOrder.seeded(1).finish(), RegattaOrder.seeded(1).finish());
        assertEquals(RegattaOrder.seeded(1).swapped(), RegattaOrder.seeded(1).swapped());
        assertThrows(IllegalArgumentException.class, () -> new RegattaOrder(List.of()));
        assertThrows(IllegalArgumentException.class, () -> new RegattaOrder(List.of(1, 1)));
    }

    @Test
    void answerMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            RegattaOrder r = RegattaOrder.seeded(seed);
            assertEquals(brute(r), r.swapped(), "fast == brute force, seed " + seed);
            assertTrue(r.swapped() >= r.neighbours(), "never fewer swaps than neighbour swaps, seed " + seed);
        }
    }

    @Test
    void trap() {
        RegattaOrder r = fixture();
        assertEquals(2, r.swapped());
        assertEquals(1, r.neighbours());
        assertEquals(Outcome.WRONG, r.count("c0", 1), "far-apart boats can have swapped too");
        assertEquals(String.format(KeeperRegattaOrder.WRONG, 1), r.talk("t0"));
    }

    @Test
    void wrongAndSpecialEarnNoCredit() {
        RegattaOrder r = fixture();
        r.read("r");
        assertEquals(Outcome.WRONG, r.count("c1", 2 + 1));
        assertEquals(Outcome.MALFORMED, r.count("c2", -1));
        assertEquals("count", r.quest().currentStep().type(), "no credit for a wrong answer");
        RegattaOrder sp = new RegattaOrder(List.of(0, 1, 2));
        assertTrue(sp.inOrder());
        assertEquals(Outcome.IN_ORDER, sp.count("x", 0));
        assertEquals(KeeperRegattaOrder.IN_ORDER, sp.talk("tx"));
    }

    @Test
    void guards() {
        RegattaOrder r = fixture();
        assertEquals(Outcome.IGNORED, r.count("", 2));
        assertEquals(Outcome.IGNORED, r.count(null, 2));
        assertEquals(Outcome.RIGHT, r.count("e1", 2));
        assertEquals(Outcome.DUPLICATE, r.count("e1", 2));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        RegattaOrder r = fixture();
        assertEquals(String.format(KeeperRegattaOrder.GREETING, List.of(3, 1, 2)), r.talk("t0"));
        r.read("r0");
        assertEquals(Outcome.WRONG, r.count("c1", 1));
        assertEquals(Outcome.RIGHT, r.count("c2", 2));
        assertEquals(KeeperRegattaOrder.THANKS, r.talk("t2"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperRegattaOrder.DONE, r.talk("t3"));
    }
}
