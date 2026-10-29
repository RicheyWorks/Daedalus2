// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.cargo;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.cargo.CargoWeights.Outcome;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

class CargoWeightsTest {
    /** Brute force: every non-empty selection, with a set of totals. */
    static int brute(CargoWeights c) {
        Set<Integer> totals = new HashSet<>();
        for (int m = 1; m < 1 << c.crates().size(); m++) {
            int t = 0;
            for (int i = 0; i < c.crates().size(); i++) {
                if ((m >> i & 1) == 1) {
                    t += c.crates().get(i);
                }
            }
            totals.add(t);
        }
        return totals.size();
    }

    /** Crates 1 2 3: loads 1 to 6 (six), from 7 selections. */
    static CargoWeights fixture() {
        return new CargoWeights(List.of(1, 2, 3));
    }

    @Test
    void seededIsDeterministic() {
        assertEquals(CargoWeights.seeded(1).crates(), CargoWeights.seeded(1).crates());
        assertEquals(CargoWeights.seeded(1).loads(), CargoWeights.seeded(1).loads());
        assertThrows(IllegalArgumentException.class, () -> new CargoWeights(null));
        assertThrows(IllegalArgumentException.class, () -> new CargoWeights(List.of(0)));
    }

    @Test
    void answerMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            CargoWeights r = CargoWeights.seeded(seed);
            assertEquals(brute(r), r.loads(), "fast == brute force, seed " + seed);
            assertTrue(r.selections() >= r.loads(), "never more loads than selections, seed " + seed);
        }
    }

    @Test
    void trap() {
        CargoWeights r = fixture();
        assertEquals(6, r.loads());
        assertEquals(7, r.selections());
        assertEquals(Outcome.WRONG, r.count("c0", 7), "different selections can weigh the same");
        assertEquals(String.format(KeeperCargoWeights.WRONG, 7), r.talk("t0"));
    }

    @Test
    void wrongAndSpecialEarnNoCredit() {
        CargoWeights r = fixture();
        r.read("r");
        assertEquals(Outcome.WRONG, r.count("c1", 6 + 1));
        assertEquals(Outcome.MALFORMED, r.count("c2", -1));
        assertEquals("count", r.quest().currentStep().type(), "no credit for a wrong answer");
        CargoWeights sp = new CargoWeights(List.of());
        assertTrue(sp.empty());
        assertEquals(Outcome.EMPTY, sp.count("x", 0));
        assertEquals(KeeperCargoWeights.EMPTY, sp.talk("tx"));
    }

    @Test
    void guards() {
        CargoWeights r = fixture();
        assertEquals(Outcome.IGNORED, r.count("", 6));
        assertEquals(Outcome.IGNORED, r.count(null, 6));
        assertEquals(Outcome.RIGHT, r.count("e1", 6));
        assertEquals(Outcome.DUPLICATE, r.count("e1", 6));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        CargoWeights r = fixture();
        assertEquals(String.format(KeeperCargoWeights.GREETING, List.of(1, 2, 3)), r.talk("t0"));
        r.read("r0");
        assertEquals(Outcome.WRONG, r.count("c1", 7));
        assertEquals(Outcome.RIGHT, r.count("c2", 6));
        assertEquals(KeeperCargoWeights.THANKS, r.talk("t2"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperCargoWeights.DONE, r.talk("t3"));
    }
}
