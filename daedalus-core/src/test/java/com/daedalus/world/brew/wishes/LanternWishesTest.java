// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.wishes;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.wishes.LanternWishes.Outcome;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class LanternWishesTest {
    /** Brute force: try every lit/dark pattern. */
    static boolean brute(LanternWishes w) {
        for (int mask = 0; mask < 1 << w.lanterns(); mask++) {
            List<Boolean> lit = new ArrayList<>();
            for (int i = 0; i < w.lanterns(); i++) {
                lit.add((mask >> i & 1) == 1);
            }
            if (w.unhappyUnder(lit) == 0) {
                return true;
            }
        }
        return false;
    }

    /** Wishes 1 or 2, not 1 or 3, not 2 or not 3, 1 or not 3: (dark, lit, dark) and (lit, dark, lit) work. */
    static LanternWishes festival() {
        return new LanternWishes(3, List.of(new int[] {1, 2}, new int[] {-1, 3}, new int[] {-2, -3},
                new int[] {1, -3}));
    }

    @Test
    void seededFestivalIsDeterministic() {
        assertEquals(LanternWishes.seeded(1).possible(), LanternWishes.seeded(1).possible());
        assertEquals(LanternWishes.seeded(1).wishCount(), LanternWishes.seeded(1).wishCount());
        assertThrows(IllegalArgumentException.class, () -> new LanternWishes(0, List.of()));
        assertThrows(IllegalArgumentException.class, () -> new LanternWishes(2, List.of(new int[] {0, 1})));
        assertThrows(IllegalArgumentException.class, () -> new LanternWishes(2, List.of(new int[] {3, 1})));
    }

    @Test
    void possibleMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            LanternWishes w = LanternWishes.seeded(seed);
            assertEquals(brute(w), w.possible(), "2-SAT == brute force, seed " + seed);
        }
    }

    @Test
    void lightingEverythingIsATrap() {
        LanternWishes w = festival();
        assertEquals(Outcome.UNHAPPY, w.light("l0", List.of(true, true, true)), "not 2 or not 3 fails");
        assertEquals(String.format(KeeperLanternWishes.UNHAPPY, 1), w.talk("t0"));
    }

    @Test
    void unhappyAndImpossibleEarnNoCredit() {
        LanternWishes w = festival();
        w.hear("h");
        assertEquals(Outcome.UNHAPPY, w.light("l1", List.of(false, false, true)));
        assertEquals(String.format(KeeperLanternWishes.UNHAPPY, 2), w.talk("t1"));
        assertEquals(Outcome.MALFORMED, w.light("l2", List.of(true, false)));
        assertEquals("light", w.quest().currentStep().type(), "no credit for an unhappy lighting");
        LanternWishes clash = new LanternWishes(1, List.of(new int[] {1, 1}, new int[] {-1, -1}));
        assertFalse(clash.possible());
        assertEquals(Outcome.IMPOSSIBLE, clash.light("x", List.of(true)));
        assertEquals(KeeperLanternWishes.IMPOSSIBLE, clash.talk("tx"));
    }

    @Test
    void guards() {
        LanternWishes w = festival();
        assertEquals(Outcome.IGNORED, w.light("", List.of(false, true, false)));
        assertEquals(Outcome.IGNORED, w.light("e", null));
        assertEquals(Outcome.GRANTED, w.light("e1", List.of(false, true, false)));
        assertEquals(Outcome.DUPLICATE, w.light("e1", List.of(false, true, false)));
    }

    @Test
    void questUnhappyThenGrantedThenKeeper() {
        LanternWishes w = festival();
        assertEquals(String.format(KeeperLanternWishes.GREETING, 3, 4), w.talk("t0"));
        w.hear("h0");
        assertEquals(Outcome.UNHAPPY, w.light("l1", List.of(true, true, true)));
        assertEquals(Outcome.GRANTED, w.light("l2", List.of(true, false, true)));
        assertEquals(KeeperLanternWishes.THANKS, w.talk("t2"));
        assertNull(w.quest().currentStep());
        assertEquals(KeeperLanternWishes.DONE, w.talk("t3"));
    }
}
