// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.catches;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.catches.MiddleCatch.Outcome;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import org.junit.jupiter.api.Test;

class MiddleCatchTest {
    /** Brute force: sort the whole catch. */
    static int brute(List<Integer> l, int k) {
        List<Integer> s = new ArrayList<>(l);
        Collections.sort(s);
        return s.get(k - 1);
    }

    /** Lengths 7, 2, 9, 4, 4, 1 and the 3rd smallest: the 3rd fish on the table is 9, the 3rd smallest is 4. */
    static MiddleCatch table() {
        return new MiddleCatch(List.of(7, 2, 9, 4, 4, 1), 3);
    }

    @Test
    void seededCatchIsDeterministic() {
        assertEquals(MiddleCatch.seeded(2).lengths(), MiddleCatch.seeded(2).lengths());
        assertEquals(MiddleCatch.seeded(2).rank(), MiddleCatch.seeded(2).rank());
        assertThrows(IllegalArgumentException.class, () -> new MiddleCatch(List.of(3), 2));
        assertThrows(IllegalArgumentException.class, () -> new MiddleCatch(List.of(0), 1));
    }

    @Test
    void kthMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            MiddleCatch c = MiddleCatch.seeded(seed);
            for (int k = 1; k <= c.lengths().size(); k++) {
                assertEquals(brute(c.lengths(), k), new MiddleCatch(c.lengths(), k).kth(),
                        "quickselect == sort, seed " + seed + " k " + k);
            }
        }
    }

    @Test
    void tablePlaceIsATrap() {
        MiddleCatch c = table();
        assertEquals(4, c.kth());
        assertEquals(Outcome.WRONG, c.name("n0", 9));
        assertEquals(String.format(KeeperCatchLines.WRONG, 9, 3, "rd", 4), c.talk("t0"));
        assertEquals("th", KeeperCatchLines.nth(12));
    }

    @Test
    void wrongEarnsNoCredit() {
        MiddleCatch c = table();
        c.land("l");
        assertEquals(Outcome.WRONG, c.name("n1", 2));
        assertEquals("name", c.quest().currentStep().type(), "no credit for a wrong fish");
    }

    @Test
    void guards() {
        MiddleCatch c = table();
        assertEquals(Outcome.IGNORED, c.name("", 4));
        assertEquals(Outcome.RIGHT, c.name("e1", 4));
        assertEquals(Outcome.DUPLICATE, c.name("e1", 4));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        MiddleCatch c = table();
        assertEquals(String.format(KeeperCatchLines.GREETING, 6, 3, "rd"), c.talk("t0"));
        c.land("l0");
        assertEquals(Outcome.WRONG, c.name("n1", 9));
        assertEquals(Outcome.RIGHT, c.name("n2", 4));
        assertEquals(KeeperCatchLines.THANKS, c.talk("t2"));
        assertNull(c.quest().currentStep());
        assertEquals(KeeperCatchLines.DONE, c.talk("t3"));
    }
}
