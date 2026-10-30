// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.rites;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.rites.FestivalRites.Outcome;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class FestivalRitesTest {
    /** Brute force: every permutation in lexicographic order; the first that keeps all needs. */
    static List<Integer> brute(FestivalRites f, List<Integer> prefix, boolean[] used) {
        if (prefix.size() == f.rites()) {
            for (int[] n : f.needs()) {
                if (prefix.indexOf(n[0]) > prefix.indexOf(n[1])) {
                    return null;
                }
            }
            return new ArrayList<>(prefix);
        }
        for (int r = 0; r < f.rites(); r++) {
            if (!used[r]) {
                used[r] = true;
                prefix.add(r);
                List<Integer> got = brute(f, prefix, used);
                prefix.remove(prefix.size() - 1);
                used[r] = false;
                if (got != null) {
                    return got;
                }
            }
        }
        return null;
    }

    /** 3 before 0 and 2 before 1: the first order is 2, 1, 3, 0; 3, 0, 2, 1 also works. */
    static FestivalRites festival() {
        return new FestivalRites(4, List.of(new int[] {3, 0}, new int[] {2, 1}));
    }

    @Test
    void seededFestivalIsDeterministic() {
        assertEquals(FestivalRites.seeded(9).order(), FestivalRites.seeded(9).order());
        assertThrows(IllegalArgumentException.class, () -> new FestivalRites(0, List.of()));
        assertThrows(IllegalArgumentException.class, () -> new FestivalRites(2, List.of(new int[] {1, 1})));
    }

    @Test
    void orderMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            FestivalRites f = FestivalRites.seeded(seed);
            assertFalse(f.tangled(), "seed " + seed);
            assertEquals(brute(f, new ArrayList<>(), new boolean[f.rites()]), f.order(),
                    "Kahn + min-heap == brute force, seed " + seed);
        }
    }

    @Test
    void greedyByNeedsIsNotFirst() {
        FestivalRites f = festival();
        assertEquals(List.of(2, 1, 3, 0), f.order());
        assertEquals(Outcome.NOT_FIRST, f.give("g0", List.of(3, 0, 2, 1)));
        assertEquals(String.format(KeeperRiteLines.NOT_FIRST, List.of(2, 1, 3, 0)), f.talk("t0"));
    }

    @Test
    void wrongOrdersEarnNoCredit() {
        FestivalRites f = festival();
        f.read("r");
        assertEquals(Outcome.OUT_OF_ORDER, f.give("g1", List.of(0, 1, 2, 3)));
        assertEquals(String.format(KeeperRiteLines.OUT_OF_ORDER, 0, 3), f.talk("t1"));
        assertEquals(Outcome.MALFORMED, f.give("g2", List.of(2, 1, 3)));
        assertEquals("order", f.quest().currentStep().type(), "no credit for a wrong order");
        FestivalRites t = new FestivalRites(3, List.of(new int[] {0, 1}, new int[] {1, 2}, new int[] {2, 0}));
        assertTrue(t.tangled());
        assertEquals(Outcome.TANGLED, t.give("x", List.of(0, 1, 2)));
        assertEquals(KeeperRiteLines.TANGLED, t.talk("tx"));
    }

    @Test
    void guards() {
        FestivalRites f = festival();
        assertEquals(Outcome.IGNORED, f.give("", List.of(2, 1, 3, 0)));
        assertEquals(Outcome.IGNORED, f.give("e", null));
        assertEquals(Outcome.MALFORMED, f.give("e0", List.of(2, 2, 3, 0)));
        assertEquals(Outcome.FIRST, f.give("e1", List.of(2, 1, 3, 0)));
        assertEquals(Outcome.DUPLICATE, f.give("e1", List.of(2, 1, 3, 0)));
    }

    @Test
    void questWrongThenFirstThenKeeper() {
        FestivalRites f = festival();
        assertEquals(String.format(KeeperRiteLines.GREETING, 4), f.talk("t0"));
        f.read("r0");
        assertEquals(Outcome.NOT_FIRST, f.give("g1", List.of(3, 0, 2, 1)));
        assertEquals(Outcome.FIRST, f.give("g2", List.of(2, 1, 3, 0)));
        assertEquals(KeeperRiteLines.THANKS, f.talk("t2"));
        assertNull(f.quest().currentStep());
        assertEquals(KeeperRiteLines.DONE, f.talk("t3"));
    }
}
