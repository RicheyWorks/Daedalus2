// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.chores;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.chores.ChoreDays.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class ChoreDaysTest {
    /** Brute force: every plan giving each chore a day 1..n; fewest last day keeping every rule, or -1. */
    static int brute(ChoreDays c) {
        int n = c.chores();
        int best = -1;
        int plans = (int) Math.pow(n, n);
        for (int p = 0; p < plans; p++) {
            int[] day = new int[n];
            int x = p;
            int last = 0;
            for (int i = 0; i < n; i++) {
                day[i] = 1 + x % n;
                x /= n;
                last = Math.max(last, day[i]);
            }
            boolean ok = true;
            for (List<Integer> r : c.rules()) {
                ok &= day[r.get(0)] < day[r.get(1)];
            }
            if (ok && (best < 0 || last < best)) {
                best = last;
            }
        }
        return best;
    }

    /** 4 chores, 0 before 1 and 2, both before 3: three days, not four. */
    static ChoreDays fixture() {
        return new ChoreDays(4, List.of(List.of(0, 1), List.of(0, 2), List.of(1, 3), List.of(2, 3)));
    }

    @Test
    void seededIsDeterministic() {
        assertEquals(ChoreDays.seeded(1).rules(), ChoreDays.seeded(1).rules());
        assertEquals(ChoreDays.seeded(1).days(), ChoreDays.seeded(1).days());
        assertThrows(IllegalArgumentException.class, () -> new ChoreDays(0, List.of()));
        assertThrows(IllegalArgumentException.class, () -> new ChoreDays(2, List.of(List.of(1, 1))));
    }

    @Test
    void answerMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            ChoreDays r = ChoreDays.seeded(seed);
            assertEquals(brute(r), r.days(), "fast == brute force, seed " + seed);
            assertEquals(brute(r) < 0, r.tangled(), "loops agree, seed " + seed);
        }
    }

    @Test
    void trap() {
        ChoreDays r = fixture();
        assertEquals(3, r.days());
        assertEquals(4, r.oneADay());
        assertEquals(Outcome.WRONG, r.count("c0", 4), "chores with nothing between them share a day");
        assertEquals(String.format(KeeperChoreDays.WRONG, 4), r.talk("t0"));
    }

    @Test
    void wrongAndSpecialEarnNoCredit() {
        ChoreDays r = fixture();
        r.read("r");
        assertEquals(Outcome.WRONG, r.count("c1", 3 + 1));
        assertEquals(Outcome.MALFORMED, r.count("c2", -1));
        assertEquals("count", r.quest().currentStep().type(), "no credit for a wrong answer");
        ChoreDays sp = new ChoreDays(2, List.of(List.of(0, 1), List.of(1, 0)));
        assertTrue(sp.tangled());
        assertEquals(Outcome.TANGLED, sp.count("x", 0));
        assertEquals(KeeperChoreDays.TANGLED, sp.talk("tx"));
    }

    @Test
    void guards() {
        ChoreDays r = fixture();
        assertEquals(Outcome.IGNORED, r.count("", 3));
        assertEquals(Outcome.IGNORED, r.count(null, 3));
        assertEquals(Outcome.RIGHT, r.count("e1", 3));
        assertEquals(Outcome.DUPLICATE, r.count("e1", 3));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        ChoreDays r = fixture();
        assertEquals(String.format(KeeperChoreDays.GREETING, 4, List.of(List.of(0, 1), List.of(0, 2), List.of(1, 3), List.of(2, 3))), r.talk("t0"));
        r.read("r0");
        assertEquals(Outcome.WRONG, r.count("c1", 4));
        assertEquals(Outcome.RIGHT, r.count("c2", 3));
        assertEquals(KeeperChoreDays.THANKS, r.talk("t2"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperChoreDays.DONE, r.talk("t3"));
    }
}
